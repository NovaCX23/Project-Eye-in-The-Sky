"""Generator de trafic AIS sintetic NORMAL (fără anomalii), cu seed fix.

Rulare:  python -m data.generate --seed 42 --out-dir out
Produce: <out-dir>/ais_clean.csv
"""

from __future__ import annotations

import argparse
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from shapely.geometry import Point

from contracts.assets import load_infrastructure
from contracts.runtime import OUT_DIR, REPO_ROOT, load_config, parse_time, utf8_stdout
from data import tracks

SCENARIO_PATH = REPO_ROOT / "data" / "scenarios" / "demo.yaml"
COLUMNS = [
    "mmsi", "timestamp", "lat", "lon", "sog_kn", "cog_deg", "heading_deg",
    "vessel_name", "ship_type", "source", "simulated",
]

# Coduri MID (țara de pavilion) folosite pentru MMSI fictive.
_MIDS = ("264", "207", "271", "215", "538", "636", "229", "248")
_NAMES = (
    "AURORA", "DELTA STAR", "MIRCEA", "PONTUS", "TOMIS", "ZEPHYR", "HALCYON", "ORION", "VEGA",
    "BOREAS", "CALLISTO", "DANUBIUS", "ELIZA", "FORTUNA", "GALATEA", "HELIOS", "IRIS", "JUNO",
    "KESTREL", "LYRA", "MARINA", "NEREID", "OCEANA", "PERSEUS",
)


def load_scenario(path: Path = SCENARIO_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _mmsi(rng: np.random.Generator, used: set[str]) -> str:
    while True:
        m = str(rng.choice(_MIDS)) + f"{int(rng.integers(0, 1_000_000)):06d}"
        if m not in used:
            used.add(m)
            return m


def _uniform_point(rng: np.random.Generator, box: dict) -> tuple[float, float]:
    return float(rng.uniform(box["lat_min"], box["lat_max"])), float(rng.uniform(box["lon_min"], box["lon_max"]))


def generate(seed: int, cfg: dict, scenario: dict) -> pd.DataFrame:
    # STUB: rute drepte între waypoints, viteză constantă; fără COLREG, vreme sau uscat.
    rng = np.random.default_rng(seed)
    g = cfg["generator"]
    sc = cfg["scenario"]
    traffic = scenario["traffic"]
    t0 = parse_time(sc["start"])
    t_end = t0 + timedelta(minutes=sc["duration_min"])
    dt = sc["report_interval_s"]
    berth, entry = tuple(traffic["port_berth"]), tuple(traffic["approach_entry"])
    used: set[str] = set()
    names = list(_NAMES)
    rng.shuffle(names)
    name_iter = iter(names * 4)
    rows: list[dict] = []

    def speed() -> float:
        return float(rng.uniform(g["speed_kn_min"], g["speed_kn_max"]))

    def add(track, ship_type, prefix="MV"):
        rows.extend(tracks.to_rows(track, _mmsi(rng, used), f"{prefix} {next(name_iter)}", ship_type, rng, g, dropouts=True))

    # Nave care intră în port: din larg -> intrarea în coridor -> dană.
    for _ in range(g["n_transit_inbound"]):
        start = _uniform_point(rng, traffic["inbound_start_box"])
        t_start = t0 + timedelta(minutes=float(rng.uniform(0, 60)))
        add(tracks.sail([start, entry, berth], [speed(), g["approach_speed_kn"]], t_start, t_end, dt), "cargo")

    # Nave care pleacă: stau la dană, apoi ies din zona de acoperire.
    for _ in range(g["n_transit_outbound"]):
        exit_pt = tuple(traffic["outbound_exits"][int(rng.integers(0, len(traffic["outbound_exits"])))])
        dep = t0 + timedelta(minutes=float(rng.uniform(0, g["departure_window_min"])))
        moored = tracks.anchored(berth, t0, dep - timedelta(seconds=dt), dt, g["anchored_max_sog_kn"], rng)
        moving = tracks.sail([berth, entry, exit_pt], [g["approach_speed_kn"], speed()], dep, t_end, dt)
        add(moored + moving, "tanker")

    # Trafic de tranzit nord-sud, departe de port.
    lanes = traffic["through_lanes"]
    for i in range(g["n_through"]):
        s = (lanes["south"]["lat"], float(rng.uniform(lanes["south"]["lon_min"], lanes["south"]["lon_max"])))
        n = (lanes["north"]["lat"], float(rng.uniform(lanes["north"]["lon_min"], lanes["north"]["lon_max"])))
        a, b = (s, n) if i % 2 == 0 else (n, s)
        t_start = t0 + timedelta(minutes=float(rng.uniform(0, 30)))
        add(tracks.sail([a, b], [speed()], t_start, t_end, dt), "cargo")

    # Nave la ancoră în radă (comportament lent NORMAL, în zona de excludere).
    anch = next(f for f in load_infrastructure() if f.infra_id == traffic["anchorage_id"])
    lats = [c[0] for c in anch.coords]
    lons = [c[1] for c in anch.coords]
    box = {"lat_min": min(lats), "lat_max": max(lats), "lon_min": min(lons), "lon_max": max(lons)}
    for _ in range(g["n_anchored"]):
        while True:
            p = _uniform_point(rng, box)
            if anch.shape.contains(Point(p[1], p[0])):
                break
        add(tracks.anchored(p, t0, t_end, dt, g["anchored_max_sog_kn"], rng), "tanker")

    df = pd.DataFrame(rows, columns=COLUMNS)
    return df.sort_values(["timestamp", "mmsi"]).reset_index(drop=True)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    out.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    cfg = load_config()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=cfg["scenario"]["seeds"]["tuning"])
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args(argv)
    df = generate(args.seed, cfg, load_scenario())
    path = args.out_dir / "ais_clean.csv"
    write_csv(df, path)
    print(f"[data.generate] seed={args.seed}: {df['mmsi'].nunique()} vessels, {len(df)} messages -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
