"""Transportul de INTRARE (varianta B: fișiere). În varianta A se înlocuiește doar acest modul.

Regulă: nimic cu timestamp > now nu iese de aici.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from shapely.geometry import shape

from contracts.models import SensorEvent
from contracts.runtime import REPO_ROOT, parse_time, read_json
from data.loader import load_ais
from data.recorded import load_recorded, vessel_lengths
from sar.landmask import coast_distance_fn
from sar.store import load_records

SENSOR_FILES = ("acoustic_events.json", "fibre_events.json")


@dataclass
class Inputs:
    ais: pd.DataFrame
    sensors: list[SensorEvent]
    # Doar pe date reale: trecerile radar procesate (sar/store.py), distanța până la coastă și lungimile navelor.
    radar: list[dict] = field(default_factory=list)
    coast_km: Callable[[float, float], float] | None = None
    lengths: dict[str, float] = field(default_factory=dict)


def load_all(in_dir: Path) -> Inputs:
    """Încarcă tot ce există pe disc; filtrarea după `now` se face în `until`."""
    sensors: list[SensorEvent] = []
    for name in SENSOR_FILES:
        p = in_dir / name
        if p.exists():
            sensors += [SensorEvent.model_validate(e) for e in read_json(p)]
    return Inputs(ais=load_ais(in_dir / "ais.csv"), sensors=sensors)


def repo_path(p: Path) -> str | None:
    """Calea relativă la rădăcina repo-ului (așa o cere pagina), sau None dacă fișierul e în altă parte."""
    try:
        return p.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return None


def load_live(ais_dir: Path, start: datetime, now: datetime, cfg: dict, sar_dir: Path | None = None) -> Inputs:
    """AIS real înregistrat între start și now (data/raw/ais/<zonă>/) și trecerile radar publicate până la now
    (data/raw/sar/<zonă>/). Niciun mesaj de după now."""
    days = cfg["live"]["static_days_before"]
    ais = load_recorded(start, now, ais_dir, days)
    since = now - timedelta(hours=cfg["detect"]["sar"]["max_age_h"])
    radar = load_records(sar_dir, now, since) if sar_dir is not None else []
    for rec in radar:
        rec["dir"] = repo_path(sar_dir / rec["pass_id"])   # imaginile se servesc din rădăcina repo-ului
    coast = None
    if radar and (sea := sar_dir / "sea.geojson").exists():
        raw = read_json(sea)
        coast = coast_distance_fn(shape(raw["geometry"]), raw["bbox"])
    lengths = vessel_lengths(start, now, ais_dir, days) if radar else {}
    return Inputs(ais=ais, sensors=[], radar=radar, coast_km=coast, lengths=lengths)


def history(ais_dir: Path, now: datetime, cfg: dict) -> Inputs:
    """Istoricul lung (live.coverage_history_days) din care se învață acoperirea și ancorajele."""
    return load_live(ais_dir, now - timedelta(days=cfg["live"]["coverage_history_days"]), now, cfg)


def until(inputs: Inputs, now: datetime) -> Inputs:
    """Vederea "până la now": mesaje și evenimente cu timestamp <= now; sfârșiturile din viitor devin None."""
    ais = inputs.ais[inputs.ais["timestamp"] <= pd.Timestamp(now)]
    sensors = []
    for e in inputs.sensors:
        if e.start <= now:
            sensors.append(e if e.end is None or e.end <= now else e.model_copy(update={"end": None}))
    # O trecere radar există pentru pipeline doar de la publicarea ei (available_at), nu de la achiziție.
    radar = [r for r in inputs.radar if parse_time(r["available_at"]) <= now]
    return Inputs(ais=ais, sensors=sensors, radar=radar, coast_km=inputs.coast_km, lengths=inputs.lengths)
