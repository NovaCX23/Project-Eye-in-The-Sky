"""Transportul de INTRARE (varianta B: fișiere). În varianta A se înlocuiește doar acest modul.

Regulă: nimic cu timestamp > now nu iese de aici.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from contracts.models import SensorEvent
from contracts.runtime import read_json
from data.loader import load_ais
from data.recorded import load_recorded

SENSOR_FILES = ("acoustic_events.json", "fibre_events.json")


@dataclass
class Inputs:
    ais: pd.DataFrame
    sensors: list[SensorEvent]


def load_all(in_dir: Path) -> Inputs:
    """Încarcă tot ce există pe disc; filtrarea după `now` se face în `until`."""
    sensors: list[SensorEvent] = []
    for name in SENSOR_FILES:
        p = in_dir / name
        if p.exists():
            sensors += [SensorEvent.model_validate(e) for e in read_json(p)]
    return Inputs(ais=load_ais(in_dir / "ais.csv"), sensors=sensors)


def load_live(ais_dir: Path, start: datetime, now: datetime, cfg: dict) -> Inputs:
    """AIS real înregistrat între start și now (data/raw/ais/<zonă>/). Niciun mesaj de după now."""
    return Inputs(ais=load_recorded(start, now, ais_dir, cfg["live"]["static_days_before"]), sensors=[])


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
    return Inputs(ais=ais, sensors=sensors)
