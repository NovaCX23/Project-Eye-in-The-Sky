"""Reguli radar: țintele unei treceri Sentinel-1 față de imaginea AIS de la momentul achiziției.

1. Fiecare navă AIS primește o poziție la momentul imaginii: interpolată între două poziții care îl încadrează,
   sau extrapolată (dead reckoning) din cea mai apropiată poziție, pe o durată scurtă.
2. Țintele și navele se asociază unu-la-unu (algoritmul ungar) într-o rază care crește cu incertitudinea poziției,
   plus o toleranță în azimut pentru navele în mișcare (deplasarea Doppler din SAR).
3. Ce rămâne neasociat e partea interesantă:
   - o țintă pe mare deschisă, care nu e structură fixă: o navă fără AIS ("dark"); unde AIS se recepționează e
     dovadă puternică, altfel doar un indiciu slab;
   - o țintă dark în zona în care putea ajunge o navă care tocmai a tăcut (aceeași condiție ca regula ais_gap):
     radarul confirmă gaura și spune unde e nava;
   - o navă AIS mare, cu poziție aproape sigură pe mare deschisă, fără niciun ecou radar: posibilă poziție falsă.
Fără stare, fără I/O: trecerea (sar/store.py), AIS-ul de până la `now` și distanța până la coastă vin de la core.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from shapely.geometry import Point, Polygon

from contracts.geo import destination, haversine_km, kn_to_kmh
from contracts.models import SensorEvent
from contracts.runtime import parse_time, stable_id
from detect.ais_rules import detect_gaps
from detect.zones import LearnedZones, is_covered, is_excluded

UNMATCHED = 1e9
MOVING_KN = 0.5          # sub această viteză nu se extrapolează pe direcție (zgomotul COG al unei nave oprite)
MIN_CONFIDENCE = 0.3


@dataclass
class TargetStatus:
    """Ce a devenit fiecare țintă a trecerii (afișat pe hartă)."""

    target_id: str
    status: str                     # matched | dark | dark_uncovered | fixed | coastal | excluded | unchecked
    mmsi: str | None = None
    vessel_name: str | None = None
    match_km: float | None = None
    note: str | None = None


@dataclass
class _Fix:
    mmsi: str
    lat: float
    lon: float
    sog: float | None
    extrap_min: float              # 0 = interpolată
    name: str | None
    simulated: bool


def ais_at(df: pd.DataFrame, t: datetime, cfg: dict) -> list[_Fix]:
    """Poziția fiecărei nave la momentul t, doar când se poate estima sigur."""
    c = cfg["detect"]["sar"]
    T = pd.Timestamp(t)
    out = []
    for mmsi, g in df.groupby("mmsi", sort=True):
        before, after = g[g["timestamp"] <= T], g[g["timestamp"] > T]
        a = before.iloc[-1] if len(before) else None
        b = after.iloc[0] if len(after) else None
        name = g["vessel_name"].dropna().iloc[-1] if g["vessel_name"].notna().any() else None
        sim = bool(g["simulated"].any())
        if a is not None and b is not None and (b.timestamp - a.timestamp) <= pd.Timedelta(minutes=c["max_interp_gap_min"]):
            span = (b.timestamp - a.timestamp).total_seconds()
            f = 0.0 if span == 0 else (T - a.timestamp).total_seconds() / span
            sog = None if pd.isna(a.sog_kn) else float(a.sog_kn)
            out.append(_Fix(mmsi, float(a.lat + (b.lat - a.lat) * f), float(a.lon + (b.lon - a.lon) * f), sog, 0.0,
                            name, sim))
            continue
        cands = []
        if a is not None:
            cands.append((a, (T - a.timestamp).total_seconds() / 60.0, 1))
        if b is not None:
            cands.append((b, (b.timestamp - T).total_seconds() / 60.0, -1))
        if not cands:
            continue
        fix, dt, sign = min(cands, key=lambda x: x[1])
        if dt > c["max_extrapolate_min"]:
            continue
        sog = None if pd.isna(fix.sog_kn) else float(fix.sog_kn)
        lat, lon = float(fix.lat), float(fix.lon)
        if sog and sog > MOVING_KN and not pd.isna(fix.cog_deg):
            lat, lon = destination(lat, lon, (float(fix.cog_deg) + (0 if sign > 0 else 180)) % 360,
                                   kn_to_kmh(sog) * dt / 60.0)
        out.append(_Fix(mmsi, lat, lon, sog, dt, name, sim))
    return out


def satellite_name(platform: str) -> str:
    """sentinel-1c -> Sentinel-1C."""
    head, _, tail = platform.partition("-")
    return f"{head.capitalize()}-{tail.upper()}" if tail else platform


def _gate_km(fix: _Fix, cfg: dict) -> float:
    c = cfg["detect"]["sar"]
    g = c["gate_km"] + c["gate_km_per_min_extrap"] * fix.extrap_min
    if fix.sog is not None and fix.sog >= c["doppler_min_sog_kn"]:
        g += c["doppler_gate_km"]
    return g


def _event(event_type: str, key: tuple, rec: dict, lat: float, lon: float, confidence: float, metrics: dict,
           mmsi: str | None = None, target_id: str | None = None, simulated: bool = False) -> SensorEvent:
    acquired = parse_time(rec["acquired_at"])
    return SensorEvent(event_id=stable_id("sar", event_type, *key, prefix="evt-"), event_type=event_type, source="sar",
                       mmsi=mmsi, target_id=target_id, sensor_id=rec["pass_id"], start=acquired, end=acquired,
                       lat=round(lat, 5), lon=round(lon, 5), confidence=round(min(1.0, max(0.0, confidence)), 3),
                       metrics=metrics, simulated=simulated)


def cross_reference(rec: dict, df: pd.DataFrame, now: datetime, cfg: dict, coast_km: Callable[[float, float], float],
                    lengths: dict[str, float] | None = None,
                    learned: LearnedZones | None = None) -> tuple[list[TargetStatus], list[SensorEvent]]:
    """Statusul fiecărei ținte și evenimentele radar. `df` = AIS până la `now`; trecerea e publicată la `now`."""
    if parse_time(rec["available_at"]) > now:
        raise ValueError("sar_rules: radar pass not yet published at now (future data)")
    if len(df) and df["timestamp"].max() > pd.Timestamp(now):
        raise ValueError("sar_rules: AIS after now (future data)")
    c, s = cfg["detect"]["sar"], cfg["sar"]
    lengths = lengths or {}
    acquired = parse_time(rec["acquired_at"])
    foot = Polygon([(lon, lat) for lat, lon in rec["footprint"]]) if len(rec["footprint"]) >= 3 else None
    targets = rec["targets"]
    fixes = [f for f in ais_at(df, acquired, cfg) if foot is None or foot.contains(Point(f.lon, f.lat))]
    names = {f.mmsi: f.name for f in fixes}
    base = {"pass_id": rec["pass_id"], "satellite": satellite_name(rec["platform"]),
            "acquired": acquired.strftime("%H:%M UTC"), "published": parse_time(rec["available_at"]).strftime("%H:%M UTC")}

    # 1. asociere unu-la-unu în interiorul razelor
    match: dict[int, tuple[int, float]] = {}
    if targets and fixes:
        cost = np.full((len(targets), len(fixes)), UNMATCHED)
        for i, t in enumerate(targets):
            for j, f in enumerate(fixes):
                d = haversine_km(t["lat"], t["lon"], f.lat, f.lon)
                if d <= _gate_km(f, cfg):
                    cost[i, j] = d
        for i, j in zip(*linear_sum_assignment(cost)):
            if cost[i, j] < UNMATCHED:
                match[int(i)] = (int(j), float(cost[i, j]))

    # Fără AIS înregistrat în jurul momentului imaginii (înregistratorul era oprit), lipsa AIS nu dovedește nimic.
    win = pd.Timedelta(minutes=c["recording_window_min"])
    recorded = int(((df["timestamp"] >= pd.Timestamp(acquired) - win) & (df["timestamp"] <= pd.Timestamp(acquired) + win)).sum())
    unchecked = recorded < c["min_recording_messages"]

    statuses: list[TargetStatus] = []
    dark: list[int] = []
    for i, t in enumerate(targets):
        if unchecked and not t.get("fixed") and t["coast_km"] >= c["dark_min_coast_km"]:
            statuses.append(TargetStatus(t["target_id"], "unchecked", note="no AIS recorded at the image time"))
        elif i in match:
            j, d = match[i]
            statuses.append(TargetStatus(t["target_id"], "matched", fixes[j].mmsi, fixes[j].name, round(d, 2)))
        elif t.get("fixed"):
            statuses.append(TargetStatus(t["target_id"], "fixed", note=t["fixed"]))
        elif t["coast_km"] < c["dark_min_coast_km"]:
            statuses.append(TargetStatus(t["target_id"], "coastal", note="harbour / coastal clutter"))
        elif zone := is_excluded("sar_dark_target", t["lat"], t["lon"], cfg, learned):
            statuses.append(TargetStatus(t["target_id"], "excluded", note=f"exclusion zone {zone}"))
        else:
            covered = is_covered(t["lat"], t["lon"], learned)
            statuses.append(TargetStatus(t["target_id"], "dark" if covered else "dark_uncovered"))
            dark.append(i)

    # 2. ținte dark față de navele care tăcuseră la momentul imaginii (aceleași condiții ca ais_gap):
    #    unu-la-unu, în zona în care putea ajunge fiecare, preferând ținta cea mai apropiată de poziția estimată.
    view_t = df[df["timestamp"] <= pd.Timestamp(acquired)]
    silent = [g for g in (detect_gaps(view_t, acquired, cfg, learned) if len(view_t) else [])
              if g.metrics["gap_min"] <= c["gap_lookback_min"] and g.metrics["gap_min"] >= c["gap_min_silent_min"]]
    last_cog = view_t.sort_values("timestamp").groupby("mmsi")["cog_deg"].last().to_dict() if len(view_t) else {}
    confirm: dict[int, tuple[SensorEvent, float, float]] = {}
    if dark and silent:
        cost = np.full((len(dark), len(silent)), UNMATCHED)
        geo = {}
        for a, i in enumerate(dark):
            t = targets[i]
            for k, g in enumerate(silent):
                silent_min = g.metrics["gap_min"]
                sog = float(g.metrics["last_sog_kn"])
                radius = kn_to_kmh(max(sog, c["gap_min_speed_kn"])) * c["gap_speed_factor"] * silent_min / 60.0 + c["gate_km"]
                dist = haversine_km(t["lat"], t["lon"], g.lat, g.lon)
                if dist > radius:
                    continue
                dr = (g.lat, g.lon)
                cog = last_cog.get(g.mmsi)
                if sog > MOVING_KN and cog is not None and not pd.isna(cog):
                    dr = destination(g.lat, g.lon, float(cog), kn_to_kmh(sog) * silent_min / 60.0)
                cost[a, k] = haversine_km(t["lat"], t["lon"], *dr) / max(radius, 1e-6)
                geo[(a, k)] = (dist, radius)
        for a, k in zip(*linear_sum_assignment(cost)):
            if cost[a, k] < UNMATCHED:
                confirm[dark[int(a)]] = (silent[int(k)], *geo[(int(a), int(k))])

    events: list[SensorEvent] = []
    if unchecked:
        return statuses, events
    for i in dark:
        t, st = targets[i], statuses[i]
        nearest = min((haversine_km(t["lat"], t["lon"], f.lat, f.lon) for f in fixes), default=None)
        m = dict(base, target_id=t["target_id"], length_m=t["length_m"], peak_db=t["peak_db"],
                 coast_km=round(t["coast_km"], 1), nearest_ais_km=None if nearest is None else round(nearest, 1))
        if i in confirm:
            g, dist, radius = confirm[i]
            st.status = "dark"
            st.mmsi, st.vessel_name = g.mmsi, names.get(g.mmsi) or _name(df, g.mmsi)
            st.note = "radar confirms the AIS gap"
            m.update(candidate_name=st.vessel_name or "unknown", candidate_mmsi=g.mmsi, dist_km=round(dist, 1),
                     radius_km=round(radius, 1), silent_min=round(g.metrics["gap_min"]),
                     candidate_length_m=lengths.get(g.mmsi))
            events.append(_event("sar_gap_confirmation", (g.mmsi, t["target_id"]), rec, t["lat"], t["lon"],
                                 max(MIN_CONFIDENCE, 1 - dist / max(radius, 1e-6)), m, mmsi=g.mmsi,
                                 target_id=t["target_id"], simulated=g.simulated))
        elif st.status == "dark":
            events.append(_event("sar_dark_target", (t["target_id"],), rec, t["lat"], t["lon"],
                                 (t["peak_db"] - s["cfar"]["seed_ratio_db"]) / 20 + 0.5, m, target_id=t["target_id"]))
        else:
            events.append(_event("sar_dark_target_uncovered", (t["target_id"],), rec, t["lat"], t["lon"],
                                 MIN_CONFIDENCE, m, target_id=t["target_id"]))

    # 3. nave AIS mari pe care radarul ar fi trebuit să le vadă
    matched = {j for j, _ in match.values()}
    for j, f in enumerate(fixes):
        length = lengths.get(f.mmsi)
        if j in matched or length is None or pd.isna(length) or length < c["min_length_no_return_m"]:
            continue
        if f.extrap_min > c["no_return_max_extrap_min"] or coast_km(f.lat, f.lon) < c["dark_min_coast_km"]:
            continue
        near = min((haversine_km(t["lat"], t["lon"], f.lat, f.lon) for t in targets), default=None)
        events.append(_event("ais_no_radar_return", (f.mmsi, rec["pass_id"]), rec, f.lat, f.lon, 0.5,
                             dict(base, length_m=float(length), nearest_target_km=None if near is None else round(near, 1)),
                             mmsi=f.mmsi, simulated=f.simulated))
    return statuses, events


def _name(df: pd.DataFrame, mmsi: str) -> str | None:
    n = df.loc[df["mmsi"] == mmsi, "vessel_name"].dropna()
    return None if n.empty else str(n.iloc[-1])
