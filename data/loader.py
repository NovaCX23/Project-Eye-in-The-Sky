"""Încărcător AIS: CSV -> DataFrame cu coloanele PositionMessage.

Regulă: cu `until=now`, niciun mesaj cu timestamp > now nu iese din această funcție.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from contracts.models import PositionMessage

COLUMNS = list(PositionMessage.model_fields)

# STUB: formatul real AIS al organizatorilor e necunoscut; aici mapăm nume uzuale de coloane.
COLUMN_ALIASES = {
    "MMSI": "mmsi",
    "# Timestamp": "timestamp",
    "Timestamp": "timestamp",
    "BaseDateTime": "timestamp",
    "Latitude": "lat",
    "LAT": "lat",
    "Longitude": "lon",
    "LON": "lon",
    "SOG": "sog_kn",
    "COG": "cog_deg",
    "Heading": "heading_deg",
    "Name": "vessel_name",
    "VesselName": "vessel_name",
    "Ship type": "ship_type",
    "VesselType": "ship_type",
}


def load_ais(path: Path | str, until: datetime | None = None, validate: bool = False) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"mmsi": str, "MMSI": str}, encoding="utf-8")
    df = df.rename(columns={k: v for k, v in COLUMN_ALIASES.items() if k in df.columns})
    for col, default in (("source", "ais"), ("simulated", False)):
        if col not in df.columns:
            df[col] = default
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = None
    df = df[COLUMNS].copy()
    df["mmsi"] = df["mmsi"].astype(str)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["simulated"] = df["simulated"].astype(str).str.lower().isin(["true", "1"])
    if until is not None:
        df = df[df["timestamp"] <= pd.Timestamp(until)]
    df = df.sort_values(["mmsi", "timestamp"]).reset_index(drop=True)
    if validate:
        for rec in df.to_dict("records"):
            PositionMessage.model_validate({k: (None if pd.isna(v) else v) for k, v in rec.items()})
    return df
