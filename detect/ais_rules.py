"""Reguli AIS: gaură de semnal, inconsistență de viteză la reapariție, loitering, salt de poziție.

Intrare: DataFrame cu mesaje PositionMessage cu timestamp <= now (garantat de core), `now`, config și, pe date
reale, zonele învățate din înregistrare (acoperire de recepție, ancoraje). Ieșire: listă de SensorEvent.
Fără stare, fără I/O: nu știe cum sunt livrate rezultatele.

# STUB: reguli naive, dar reale: prinde scenariul demo. Vezi detect/README.md pentru îmbunătățiri.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from contracts.geo import haversine_km, haversine_km_np, kmh_to_kn, kn_to_kmh
from contracts.models import SensorEvent
from contracts.runtime import stable_id
from detect.zones import LearnedZones, coverage_bbox, is_covered, is_excluded


def _event(event_type: str, mmsi: str, start, end, lat: float, lon: float, confidence: float,
           metrics: dict, simulated: bool) -> SensorEvent:
    return SensorEvent(
        event_id=stable_id("ais", event_type, mmsi, pd.Timestamp(start).to_pydatetime(), prefix="evt-"),
        event_type=event_type,
        source="ais",
        mmsi=mmsi,
        start=pd.Timestamp(start).to_pydatetime(),
        end=None if end is None else pd.Timestamp(end).to_pydatetime(),
        lat=round(float(lat), 5),
        lon=round(float(lon), 5),
        confidence=round(float(min(1.0, max(0.0, confidence))), 3),
        metrics=metrics,
        simulated=bool(simulated),
    )


def _edge_km(lat: float, lon: float, bbox: dict) -> float:
    return min(
        haversine_km(lat, lon, bbox["lat_min"], lon), haversine_km(lat, lon, bbox["lat_max"], lon),
        haversine_km(lat, lon, lat, bbox["lon_min"]), haversine_km(lat, lon, lat, bbox["lon_max"]),
    )


def detect_gaps(df: pd.DataFrame, now: datetime, cfg: dict, learned: LearnedZones | None = None) -> list[SensorEvent]:
    """Gaură AIS = now - ultimul_mesaj > prag. NU diferența dintre două mesaje consecutive.

    Nava trebuie să fi transmis regulat înainte, iar ultima poziție să fie unde AIS chiar se recepționează.
    """
    c = cfg["detect"]["gap"]
    bbox = coverage_bbox(cfg, learned)
    now_ts = pd.Timestamp(now)
    out = []
    last = df.loc[df.groupby("mmsi")["timestamp"].idxmax()]
    for r in last.itertuples(index=False):
        gap_min = (now_ts - r.timestamp).total_seconds() / 60.0
        if gap_min <= c["threshold_min"]:
            continue
        if _edge_km(r.lat, r.lon, bbox) < c["edge_margin_km"]:
            continue  # a ieșit din acoperire, nu e "dark"
        if is_excluded("ais_gap", r.lat, r.lon, cfg, learned):
            continue
        if not is_covered(r.lat, r.lon, learned):
            continue  # acolo nu o aude niciun receptor: tăcerea nu dovedește nimic
        recent = df[(df["mmsi"] == r.mmsi) & (df["timestamp"] > r.timestamp - pd.Timedelta(hours=1))]
        if len(recent) < c["min_messages_last_hour"]:
            continue  # nu transmitea regulat nici înainte
        sog = 0.0 if pd.isna(r.sog_kn) else float(r.sog_kn)
        rate_kmh = kn_to_kmh(max(sog, c["min_uncertainty_speed_kn"]))
        out.append(_event(
            "ais_gap", r.mmsi, r.timestamp, None, r.lat, r.lon,
            confidence=min(1.0, gap_min / (3 * c["threshold_min"])),
            metrics={
                "gap_min": round(gap_min, 1),
                "threshold_min": c["threshold_min"],
                "last_sog_kn": round(sog, 1),
                "uncertainty_km_per_h": round(rate_kmh, 2),
                "uncertainty_radius_km": round(rate_kmh * gap_min / 60.0, 2),
            },
            simulated=r.simulated,
        ))
    return out


def detect_speed_inconsistency(df: pd.DataFrame, cfg: dict) -> list[SensorEvent]:
    """La reapariție (pauză > min_gap_min): distanța parcursă nu se potrivește cu viteza raportată.

    Se verifică în ambele direcții: prea rapid și prea lent.
    """
    c = cfg["detect"]["speed_consistency"]
    history = np.timedelta64(int(c["history_min"] * 60), "s")
    out = []
    for mmsi, g in df.groupby("mmsi", sort=True):
        if len(g) < 2:
            continue
        t = g["timestamp"].to_numpy()
        dt_min = np.diff(t).astype("timedelta64[s]").astype(float) / 60.0
        idx = np.nonzero(dt_min > c["min_gap_min"])[0]
        for i in idx:
            a, b = g.iloc[i], g.iloc[i + 1]
            dist = haversine_km(a.lat, a.lon, b.lat, b.lon)
            implied_kn = kmh_to_kn(dist / (dt_min[i] / 60.0))
            # Viteza așteptată = mediana SOG din istoricul dinainte de pauză; SOG-ul de după reapariție nu contează.
            hist = g["sog_kn"].to_numpy(dtype=float)[(t >= t[i] - history) & (t <= t[i])]
            reported = float(np.nanmedian(hist)) if np.isfinite(hist).any() else 0.0
            direction = None
            if reported >= c["min_expected_kn"]:
                ratio = implied_kn / reported
                if ratio < c["ratio_too_slow"]:
                    direction = "too_slow"
                elif ratio > c["ratio_too_fast"]:
                    direction = "too_fast"
            else:
                ratio = None
                if implied_kn > c["stationary_max_implied_kn"]:
                    direction = "too_fast"
            if direction is None:
                continue
            out.append(_event(
                "speed_inconsistency", mmsi, a.timestamp, b.timestamp, b.lat, b.lon,
                confidence=0.9 if ratio is None else min(1.0, abs(np.log(max(ratio, 1e-3)))),
                metrics={
                    "direction": direction,
                    "gap_min": round(float(dt_min[i]), 1),
                    "distance_km": round(dist, 2),
                    "implied_kn": round(implied_kn, 1),
                    "reported_kn": round(reported, 1),
                    "ratio": None if ratio is None else round(ratio, 2),
                    "expected_km": round(kn_to_kmh(reported) * dt_min[i] / 60.0, 1),
                    "from_lat": round(float(a.lat), 5),
                    "from_lon": round(float(a.lon), 5),
                },
                simulated=bool(b.simulated),
            ))
    return out


def detect_position_jumps(df: pd.DataFrame, cfg: dict) -> list[SensorEvent]:
    c = cfg["detect"]["position_jump"]
    out = []
    for mmsi, g in df.groupby("mmsi", sort=True):
        if len(g) < 2:
            continue
        lat, lon = g["lat"].to_numpy(), g["lon"].to_numpy()
        dt_h = np.diff(g["timestamp"].to_numpy()).astype("timedelta64[s]").astype(float) / 3600.0
        dist = haversine_km_np(lat[:-1], lon[:-1], lat[1:], lon[1:])
        with np.errstate(divide="ignore"):
            implied = np.where(dt_h > 0, dist / np.maximum(dt_h, 1e-9), np.inf)
        implied_kn = implied / kn_to_kmh(1.0)
        bad = np.nonzero((dt_h * 60.0 <= c["max_dt_min"]) & (implied_kn > c["max_implied_kn"]))[0]
        for i in bad:
            b = g.iloc[i + 1]
            out.append(_event(
                "position_jump", mmsi, b.timestamp, b.timestamp, b.lat, b.lon,
                confidence=min(1.0, float(implied_kn[i]) / (4 * c["max_implied_kn"])),
                metrics={
                    "distance_km": round(float(dist[i]), 2),
                    "dt_min": round(float(dt_h[i] * 60.0), 2),
                    "implied_kn": round(float(min(implied_kn[i], 1e6)), 1),
                    "max_implied_kn": c["max_implied_kn"],
                },
                simulated=bool(b.simulated),
            ))
    return out


def detect_loitering(df: pd.DataFrame, cfg: dict, learned: LearnedZones | None = None) -> list[SensorEvent]:
    """Fereastră glisantă pe timp: viteză medie mică ȘI poziții strânse, în afara zonelor de excludere.

    O navă practic nemișcată (viteză medie <= max_moored_sog_kn) e ancorată/acostată, nu în loitering.

    Episodul pornește la începutul primei ferestre valide, deci id-ul rămâne stabil când `now` avansează.
    """
    c = cfg["detect"]["loitering"]
    win = f"{c['window_min']}min"
    out = []
    for mmsi, g in df.groupby("mmsi", sort=True):
        if len(g) < c["min_messages"]:
            continue
        s = g.set_index("timestamp")
        s = s.assign(t_min=(s.index - s.index[0]).total_seconds() / 60.0)
        roll = s[["lat", "lon", "sog_kn", "t_min"]].rolling(win)
        n = roll["lat"].count()
        span_min = s["t_min"] - roll["t_min"].min()
        sog = roll["sog_kn"].mean()
        lat_min, lat_max = roll["lat"].min(), roll["lat"].max()
        lon_min, lon_max = roll["lon"].min(), roll["lon"].max()
        # STUB: întinderea = diagonala bbox-ului din fereastră (haversine), nu raza față de centroid.
        extent = haversine_km_np(lat_min.to_numpy(), lon_min.to_numpy(), lat_max.to_numpy(), lon_max.to_numpy())
        ok = (
            (n.to_numpy() >= c["min_messages"])
            & (span_min.to_numpy() >= c["window_min"] * c["min_coverage_ratio"])
            & (sog.to_numpy() <= c["max_mean_sog_kn"])
            & (extent <= c["max_extent_km"])
        )
        if not ok.any():
            continue
        times = s.index
        # Episoade = rulări consecutive de ferestre valide.
        i = 0
        while i < len(ok):
            if not ok[i]:
                i += 1
                continue
            j = i
            while j + 1 < len(ok) and ok[j + 1]:
                j += 1
            # Episodul începe la primul mesaj lent din prima fereastră validă, nu la marginea ferestrei
            # (care poate cuprinde încă minute de mers normal).
            win_start = times[i] - pd.Timedelta(minutes=c["window_min"])
            first_win = s[(s.index >= win_start) & (s.index <= times[i])]
            slow = first_win.index[first_win["sog_kn"] <= c["max_mean_sog_kn"]]
            ep_start = slow[0] if len(slow) else win_start
            seg = s[(s.index >= ep_start) & (s.index <= times[j])]
            clat, clon = float(seg["lat"].mean()), float(seg["lon"].mean())
            moored = float(seg["sog_kn"].mean()) <= c["max_moored_sog_kn"]
            if not moored and not is_excluded("loitering", clat, clon, cfg, learned):
                ongoing = j == len(ok) - 1
                dur = (times[j] - ep_start).total_seconds() / 60.0
                out.append(_event(
                    "loitering", mmsi, ep_start, None if ongoing else times[j], clat, clon,
                    confidence=min(1.0, dur / (3 * c["window_min"])),
                    metrics={
                        "duration_min": round(dur, 1),
                        "mean_sog_kn": round(float(seg["sog_kn"].mean()), 2),
                        "extent_km": round(float(extent[j]), 2),
                        "window_min": c["window_min"],
                        "max_mean_sog_kn": c["max_mean_sog_kn"],
                    },
                    simulated=bool(seg["simulated"].any()),
                ))
            i = j + 1
    return out


def detect_rendezvous(df: pd.DataFrame, cfg: dict, learned: LearnedZones | None = None) -> list[SensorEvent]:
    """Detectează întâlniri suspecte între două nave (STS transfer / rendezvous).

    Identifică perechi de nave diferite care stau la distanță mică (<= max_distance_km),
    ambele având viteză mică (<= max_sog_kn), timp de cel puțin `min_duration_min`.
    Ignoră navele aflate în zonele de excludere (ancoraj, culoar portuar).
    """
    if "rendezvous" not in cfg.get("detect", {}):
        return []
    c = cfg["detect"]["rendezvous"]
    max_dist = float(c["max_distance_km"])
    max_sog = float(c["max_sog_kn"])
    min_dur = float(c["min_duration_min"])
    min_msgs = int(c["min_messages"])
    time_win_s = float(c["time_window_min"]) * 60.0

    slow = df[df["sog_kn"].fillna(0) <= max_sog].copy()
    if slow["mmsi"].nunique() < 2:
        return []

    slow = slow.sort_values("timestamp")
    mmsis = sorted(slow["mmsi"].unique())
    out: list[SensorEvent] = []

    for idx_a in range(len(mmsis)):
        for idx_b in range(idx_a + 1, len(mmsis)):
            ma, mb = mmsis[idx_a], mmsis[idx_b]
            ga = slow[slow["mmsi"] == ma]
            gb = slow[slow["mmsi"] == mb]
            if len(ga) < min_msgs or len(gb) < min_msgs:
                continue

            merged = pd.merge_asof(
                ga[["timestamp", "lat", "lon", "sog_kn", "simulated"]].sort_values("timestamp"),
                gb[["timestamp", "lat", "lon", "sog_kn", "simulated"]].sort_values("timestamp"),
                on="timestamp",
                direction="nearest",
                tolerance=pd.Timedelta(seconds=time_win_s),
                suffixes=("_a", "_b"),
            ).dropna(subset=["lat_b", "lon_b"])

            if len(merged) < min_msgs:
                continue

            dist_km = haversine_km_np(
                merged["lat_a"].to_numpy(), merged["lon_a"].to_numpy(),
                merged["lat_b"].to_numpy(), merged["lon_b"].to_numpy(),
            )
            close_mask = dist_km <= max_dist
            if not close_mask.any():
                continue

            close_pts = merged[close_mask]
            if len(close_pts) < min_msgs:
                continue

            start_t = close_pts["timestamp"].min()
            end_t = close_pts["timestamp"].max()
            dur_min = (end_t - start_t).total_seconds() / 60.0

            if dur_min >= min_dur:
                clat = float((close_pts["lat_a"].mean() + close_pts["lat_b"].mean()) / 2.0)
                clon = float((close_pts["lon_a"].mean() + close_pts["lon_b"].mean()) / 2.0)
                if is_excluded("rendezvous", clat, clon, cfg, learned):
                    continue

                mean_d = float(dist_km[close_mask].mean())
                mean_s = float((close_pts["sog_kn_a"].mean() + close_pts["sog_kn_b"].mean()) / 2.0)
                sim = bool(close_pts["simulated_a"].any() or close_pts["simulated_b"].any())

                out.append(_event(
                    "rendezvous", ma, start_t, end_t,
                    float(close_pts["lat_a"].iloc[-1]), float(close_pts["lon_a"].iloc[-1]),
                    confidence=min(1.0, dur_min / (2 * min_dur)),
                    metrics={
                        "other_mmsi": mb,
                        "distance_km": round(mean_d, 2),
                        "duration_min": round(dur_min, 1),
                        "mean_sog_kn": round(mean_s, 1),
                        "max_sog_kn": max_sog,
                    },
                    simulated=sim,
                ))
                out.append(_event(
                    "rendezvous", mb, start_t, end_t,
                    float(close_pts["lat_b"].iloc[-1]), float(close_pts["lon_b"].iloc[-1]),
                    confidence=min(1.0, dur_min / (2 * min_dur)),
                    metrics={
                        "other_mmsi": ma,
                        "distance_km": round(mean_d, 2),
                        "duration_min": round(dur_min, 1),
                        "mean_sog_kn": round(mean_s, 1),
                        "max_sog_kn": max_sog,
                    },
                    simulated=sim,
                ))
    return out


def detect_identity_spoofing(df: pd.DataFrame, cfg: dict) -> list[SensorEvent]:
    """Detectează falsificarea identității AIS (transponder clonat / emisie simultană la distanță).

    Semnalează când același MMSI transmite mesaje cu ecart temporal foarte mic (<= max_dt_min),
    dar la o distanță imposibilă (>= min_distance_km) implicând viteze de deplasare nerealiste (>= min_implied_kn).
    """
    if "identity_spoofing" not in cfg.get("detect", {}):
        return []
    c = cfg["detect"]["identity_spoofing"]
    min_dist = float(c["min_distance_km"])
    max_dt_min = float(c["max_dt_min"])
    min_speed = float(c["min_implied_kn"])

    out = []
    for mmsi, g in df.groupby("mmsi", sort=True):
        if len(g) < 2:
            continue
        g_sorted = g.sort_values("timestamp")
        lat, lon = g_sorted["lat"].to_numpy(), g_sorted["lon"].to_numpy()
        dt_h = np.diff(g_sorted["timestamp"].to_numpy()).astype("timedelta64[s]").astype(float) / 3600.0
        dist = haversine_km_np(lat[:-1], lon[:-1], lat[1:], lon[1:])
        with np.errstate(divide="ignore"):
            implied_kn = np.where(dt_h > 0, dist / np.maximum(dt_h, 1e-9) / kn_to_kmh(1.0), np.inf)

        bad = np.nonzero((dt_h * 60.0 <= max_dt_min) & (dist >= min_dist) & (implied_kn >= min_speed))[0]
        for i in bad:
            b = g_sorted.iloc[i + 1]
            out.append(_event(
                "identity_spoofing", mmsi, b.timestamp, b.timestamp, b.lat, b.lon,
                confidence=min(1.0, float(dist[i]) / (2 * min_dist)),
                metrics={
                    "distance_km": round(float(dist[i]), 1),
                    "dt_min": round(float(dt_h[i] * 60.0), 1),
                    "implied_kn": round(float(min(implied_kn[i], 9999)), 0),
                    "min_implied_kn": min_speed,
                },
                simulated=bool(b.simulated),
            ))
    return out


def run_all(df: pd.DataFrame, now: datetime, cfg: dict, learned: LearnedZones | None = None) -> list[SensorEvent]:
    """Toate regulile AIS. `df` trebuie să conțină doar mesaje cu timestamp <= now.

    `learned`: zonele învățate din AIS real (None pentru datele sintetice).
    """
    if len(df) and df["timestamp"].max() > pd.Timestamp(now):
        raise ValueError("detect: received messages from the future (timestamp > now)")
    if df.empty:
        return []
    return (
        detect_gaps(df, now, cfg, learned)
        + detect_speed_inconsistency(df, cfg)
        + detect_loitering(df, cfg, learned)
        + detect_position_jumps(df, cfg)
        + detect_rendezvous(df, cfg, learned)
        + detect_identity_spoofing(df, cfg)
    )
