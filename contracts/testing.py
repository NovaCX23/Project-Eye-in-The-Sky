"""Construiește date AIS mici, controlate, pentru testele tuturor modulelor (format PositionMessage)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from contracts.geo import destination, kn_to_kmh
from contracts.models import PositionMessage

COLUMNS = list(PositionMessage.model_fields)


def straight_track(mmsi: str, t0: datetime, minutes, lat: float, lon: float, sog: float = 12.0,
                   cog: float = 90.0, name: str = "TEST") -> list[dict]:
    """Un mesaj pe minut (la t0 + m), pornind din (lat, lon) la primul minut, cu viteză constantă."""
    minutes = list(minutes)
    rows = []
    for m in minutes:
        la, lo = destination(lat, lon, cog, kn_to_kmh(sog) * (m - minutes[0]) / 60.0)
        rows.append({"mmsi": mmsi, "timestamp": t0 + timedelta(minutes=m), "lat": la, "lon": lo, "sog_kn": sog,
                     "cog_deg": cog, "heading_deg": cog, "vessel_name": name, "ship_type": "cargo",
                     "source": "ais", "simulated": True})
    return rows


def to_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df.sort_values(["mmsi", "timestamp"]).reset_index(drop=True)
