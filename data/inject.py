"""Injector de anomalii: scenariul demo + anomalii aleatoare (din seed) + evenimente fibră simulate.

Rulare:  python -m data.inject --seed 42 --out-dir out
Consumă: <out-dir>/ais_clean.csv, data/scenarios/demo.yaml, config.yaml
Produce: <out-dir>/ais.csv, <out-dir>/ground_truth.json, <out-dir>/fibre_events.json
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from contracts.assets import in_exclusion_zone, load_infrastructure
from contracts.geo import destination, haversine_km
from contracts.models import SensorEvent
from contracts.runtime import OUT_DIR, iso, load_config, parse_time, stable_id, utf8_stdout, write_json_atomic
from data import tracks
from data.generate import load_scenario, write_csv
from data.loader import load_ais


def _gt(kind: str, mmsi: str, start: datetime, end: datetime, lat: float, lon: float, origin: str,
        expected: list[str], description: str) -> dict:
    return {
        "anomaly_id": stable_id(mmsi, kind, start, prefix="gt-"),
        "type": kind,
        "mmsi": mmsi,
        "start": iso(start),
        "end": iso(end),
        "lat": round(lat, 5),
        "lon": round(lon, 5),
        "origin": origin,
        "expected_event_types": expected,
        "description": description,
        "simulated": True,
    }


def inject_dark_vessel(sc: dict, cfg: dict, t0: datetime, t_end: datetime) -> tuple[list[dict], dict]:
    d = sc["dark_vessel"]
    dt = cfg["scenario"]["report_interval_s"]
    gap_start = t0 + timedelta(minutes=d["gap_start_min"])
    gap_end = gap_start + timedelta(minutes=d["gap_duration_min"])
    a, b = tuple(d["start"]), tuple(d["last_seen"])
    first = gap_start - timedelta(minutes=tracks.travel_minutes([a, b], [d["speed_kn"]]))
    before = [p for p in tracks.sail([a, b], [d["speed_kn"]], first, gap_start, dt) if p.t <= gap_start]
    traffic = sc["traffic"]
    after = tracks.sail(
        [tuple(d["reappear"]), tuple(traffic["approach_entry"]), tuple(traffic["port_berth"])],
        [d["speed_kn"], cfg["generator"]["approach_speed_kn"]],
        gap_end, t_end, dt,
    )
    rng = np.random.default_rng(0)  # zgomot fix: scenariul demo arată la fel pentru orice seed
    rows = tracks.to_rows(before + after, d["mmsi"], d["name"], d["ship_type"], rng, cfg["generator"],
                          dropouts=False, t_min=t0)
    last = before[-1]
    gt = _gt("ais_gap", d["mmsi"], last.t, gap_end, last.lat, last.lon, "demo",
             ["ais_gap", "speed_inconsistency"],
             "Cargo spre Constanța închide AIS 2 h lângă platformă și cablu; reapare prea aproape.")
    return rows, gt


def inject_loiter_vessel(sc: dict, cfg: dict, t0: datetime, t_end: datetime) -> tuple[list[dict], dict]:
    v = sc["loiter_vessel"]
    dt = cfg["scenario"]["report_interval_s"]
    rng = np.random.default_rng(1)
    appear = t0 + timedelta(minutes=v["appear_min"])
    start, center = tuple(v["start"]), tuple(v["center"])
    arrive = appear + timedelta(minutes=tracks.travel_minutes([start, center], [v["transit_speed_kn"]]))
    leave = arrive + timedelta(minutes=v["loiter_duration_min"])
    inbound = [p for p in tracks.sail([start, center], [v["transit_speed_kn"]], appear, arrive, dt) if p.t < arrive]
    circle = tracks.loiter(center, arrive, leave, dt, v["loiter_sog_kn"], v["loiter_radius_km"], rng)
    exit_from = (circle[-1].lat, circle[-1].lon)
    outbound = tracks.sail([exit_from, tuple(v["exit"])], [v["exit_speed_kn"]], leave + timedelta(seconds=dt), t_end, dt)
    rows = tracks.to_rows(inbound + circle + outbound, v["mmsi"], v["name"], v["ship_type"], rng, cfg["generator"],
                          dropouts=False)
    gt = _gt("loitering", v["mmsi"], arrive, leave, center[0], center[1], "demo", ["loitering"],
             "A doua navă staționează la viteză mică în aceeași zonă, cu AIS pornit.")
    return rows, gt


def _cable_km(lat: float, lon: float, cable) -> tuple[float, float, float]:
    """Punctul de pe cablu cel mai apropiat (eșantionare la 100 m) și kilometrul de la capătul de țărm."""
    best = (float("inf"), 0.0, lat, lon)
    km = 0.0
    step = 0.1
    for a, b in zip(cable.coords, cable.coords[1:]):
        seg = haversine_km(*a, *b)
        n = max(1, int(seg / step))
        for i in range(n + 1):
            p = (a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)  # HACK: interpolare liniară pe segmente scurte
            dist = haversine_km(lat, lon, *p)
            if dist < best[0]:
                best = (dist, km + seg * i / n, p[0], p[1])
        km += seg
    return best[1], best[2], best[3]


def fibre_events(sc: dict, t0: datetime) -> list[dict]:
    # STUB: senzorul de fibră nu există; evenimentele sunt scriptate în scenariu și marcate simulated.
    cable = next(f for f in load_infrastructure() if f.kind == "cable")
    out = []
    for fe in sc["fibre_events"]:
        km, lat, lon = _cable_km(*fe["near"], cable)
        start = t0 + timedelta(minutes=fe["offset_min"])
        ev = SensorEvent(
            event_id=stable_id("fibre", cable.infra_id, start, round(km, 1), prefix="evt-"),
            event_type="fibre_vibration",
            source="fibre",
            sensor_id=f"DAS-{cable.infra_id}",
            start=start,
            end=start + timedelta(minutes=2),
            lat=round(lat, 5),
            lon=round(lon, 5),
            confidence=fe["confidence"],
            metrics={"cable_km": round(km, 2), "amplitude": fe["amplitude"], "cable_id": cable.infra_id,
                     "note": fe.get("note")},
            simulated=True,
        )
        out.append(ev.model_dump(mode="json"))
    return out


def _edge_km(lat: float, lon: float, bbox: dict) -> float:
    return min(
        haversine_km(lat, lon, bbox["lat_min"], lon), haversine_km(lat, lon, bbox["lat_max"], lon),
        haversine_km(lat, lon, lat, bbox["lon_min"]), haversine_km(lat, lon, lat, bbox["lon_max"]),
    )


def inject_random(df: pd.DataFrame, cfg: dict, seed: int, t0: datetime, t_end: datetime,
                  exclude: set[str]) -> tuple[pd.DataFrame, list[dict]]:
    """Anomalii suplimentare pe nave normale, alese din seed (pentru evaluare)."""
    inj = cfg["injector"]
    bbox = cfg["scenario"]["coverage_bbox"]
    rng = np.random.default_rng(seed + 7919)
    dt = cfg["scenario"]["report_interval_s"]
    durations = {"ais_gap": inj["random_gap_min"], "position_jump": 1, "loitering": inj["random_loiter_min"]}
    margin = timedelta(minutes=inj["random_margin_min"])
    gts: list[dict] = []
    candidates = sorted(set(df["mmsi"]) - exclude)
    rng.shuffle(candidates)
    for kind, count in inj["random_anomalies"].items():
        placed = 0
        for mmsi in list(candidates):
            if placed >= count:
                break
            dur = timedelta(minutes=durations[kind])
            g = df[df["mmsi"] == mmsi].sort_values("timestamp")
            lo, hi = t0 + margin, t_end - margin - dur
            ok = g[(g["timestamp"] >= lo) & (g["timestamp"] <= hi) & (g["sog_kn"] > cfg["detect"]["loitering"]["max_mean_sog_kn"])]
            if ok.empty:
                continue
            row = ok.iloc[int(rng.integers(0, len(ok)))]
            ts, lat, lon = row["timestamp"].to_pydatetime(), float(row["lat"]), float(row["lon"])
            if in_exclusion_zone(lat, lon) or _edge_km(lat, lon, bbox) < inj["edge_safety_km"]:
                continue
            if g["timestamp"].max() < ts + dur + margin:  # trebuie să mai transmită după anomalie
                continue
            candidates.remove(mmsi)
            placed += 1
            mask = df["mmsi"] == mmsi
            if kind == "ais_gap":
                df = df[~(mask & (df["timestamp"] > ts) & (df["timestamp"] <= ts + dur))]
                gts.append(_gt(kind, mmsi, ts, ts + dur, lat, lon, "random", ["ais_gap"], "Gaură AIS injectată."))
            elif kind == "position_jump":
                jlat, jlon = destination(lat, lon, float(rng.uniform(0, 360)), inj["random_jump_km"])
                idx = df.index[mask & (df["timestamp"] == ts)]
                df.loc[idx, ["lat", "lon"]] = [round(jlat, 6), round(jlon, 6)]
                gts.append(_gt(kind, mmsi, ts, ts + dur, jlat, jlon, "random", ["position_jump"],
                               "Salt de poziție (spoofing) injectat."))
            elif kind == "loitering":
                # Nava se oprește dur minute, apoi își reia drumul (restul traseului e decalat în timp).
                circle = tracks.loiter((lat, lon), ts, ts + dur, dt, inj["random_loiter_sog_kn"], 0.3, rng)
                rest = df[mask & (df["timestamp"] > ts)].copy()
                rest["timestamp"] = rest["timestamp"] + dur + timedelta(seconds=dt)
                rest = rest[rest["timestamp"] <= pd.Timestamp(t_end)]
                first = g.iloc[0]
                loit = pd.DataFrame(tracks.to_rows(circle, mmsi, first["vessel_name"], first["ship_type"], rng,
                                                   cfg["generator"], dropouts=False))
                loit["timestamp"] = pd.to_datetime(loit["timestamp"], utc=True)
                df = pd.concat([df[~(mask & (df["timestamp"] >= ts))], loit, rest], ignore_index=True)
                gts.append(_gt(kind, mmsi, ts, ts + dur, lat, lon, "random", ["loitering"], "Loitering injectat."))
    return df, gts


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    cfg = load_config()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=cfg["scenario"]["seeds"]["tuning"])
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args(argv)
    sc = load_scenario()
    t0 = parse_time(cfg["scenario"]["start"])
    t_end = t0 + timedelta(minutes=cfg["scenario"]["duration_min"])

    df = load_ais(args.out_dir / "ais_clean.csv")
    scenario_mmsis = {sc["dark_vessel"]["mmsi"], sc["loiter_vessel"]["mmsi"]}
    df, gts = inject_random(df, cfg, args.seed, t0, t_end, exclude=scenario_mmsis)
    dark_rows, gt_dark = inject_dark_vessel(sc, cfg, t0, t_end)
    loit_rows, gt_loit = inject_loiter_vessel(sc, cfg, t0, t_end)
    extra = pd.DataFrame(dark_rows + loit_rows)
    extra["timestamp"] = pd.to_datetime(extra["timestamp"], utc=True)
    df = pd.concat([df, extra], ignore_index=True)
    df = df[(df["timestamp"] >= pd.Timestamp(t0)) & (df["timestamp"] <= pd.Timestamp(t_end))]
    df = df.sort_values(["timestamp", "mmsi"]).reset_index(drop=True)

    write_csv(df, args.out_dir / "ais.csv")
    ground_truth = {"seed": args.seed, "scenario_start": iso(t0), "simulated": True,
                    "anomalies": [gt_dark, gt_loit] + gts,
                    "normal_mmsis": sorted(set(df["mmsi"]) - {g["mmsi"] for g in [gt_dark, gt_loit] + gts})}
    write_json_atomic(args.out_dir / "ground_truth.json", ground_truth)
    write_json_atomic(args.out_dir / "fibre_events.json", fibre_events(sc, t0))
    print(f"[data.inject] seed={args.seed}: {len(ground_truth['anomalies'])} anomalii "
          f"({', '.join(g['type'] for g in ground_truth['anomalies'])}), {len(df)} mesaje -> {args.out_dir / 'ais.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
