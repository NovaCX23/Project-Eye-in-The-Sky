"""AIS REAL înregistrat (data/raw/ais/<zonă>/*.csv, scris de data.aisstream) -> tabelul PositionMessage.

Tot de aici, două hărți învățate din înregistrare (nu desenate de mână):
  - acoperirea de recepție: celulele unde AIS chiar se aude (doar acolo o navă poate "dispărea");
  - ancorajele învățate: celulele unde mai multe nave stau pe loc (viteza mică e normală acolo).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from data.loader import COLUMNS

# Coduri ITU de tip de navă (20-99) -> etichete simple, aceleași ca în traficul sintetic.
SHIP_TYPES = {
    30: "fishing", 31: "towing", 32: "towing", 33: "dredging", 34: "diving", 35: "military", 36: "sailing",
    37: "pleasure craft", 50: "pilot", 51: "search and rescue", 52: "tug", 53: "port tender",
    54: "anti-pollution", 55: "law enforcement", 58: "medical", 59: "special craft",
}
SHIP_TYPE_DECADES = {2: "wing in ground", 4: "high-speed craft", 6: "passenger", 7: "cargo", 8: "tanker", 9: "other"}

Cell = tuple[int, int]


def ship_type_label(code) -> str | None:
    try:
        code = int(code)
    except (TypeError, ValueError):
        return None
    return SHIP_TYPES.get(code) or SHIP_TYPE_DECADES.get(code // 10)


def _days(start: datetime, end: datetime) -> list[str]:
    d, out = start.date(), []
    while d <= end.date():
        out.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return out


def _read(prefix: str, days: list[str], ais_dir: Path) -> pd.DataFrame:
    frames = [pd.read_csv(p, dtype={"mmsi": str}, encoding="utf-8")
              for day in days if (p := ais_dir / f"{prefix}-{day}.csv").exists()]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def is_vessel_mmsi(m: pd.Series) -> pd.Series:
    """Navele au MMSI care începe cu 2-7 (stațiile de bază 00, balizele 99, SART 970 nu sunt nave)."""
    return m.str.len().eq(9) & m.str[0].isin(list("234567"))


def static_table(days: list[str], ais_dir: Path) -> pd.DataFrame:
    """Ultimul nume, tip și lungime raportate de fiecare navă."""
    st = _read("static", days, ais_dir)
    if st.empty:
        return pd.DataFrame(columns=["mmsi", "vessel_name", "ship_type", "length_m"])
    st = st.sort_values("received_utc")
    agg = st.groupby("mmsi").agg(vessel_name=("name", "last"), ship_type_code=("ship_type_code", "last"),
                                 length_m=("length_m", "last")).reset_index()
    agg["ship_type"] = agg["ship_type_code"].map(ship_type_label)
    return agg[["mmsi", "vessel_name", "ship_type", "length_m"]]


def vessel_lengths(start: datetime, end: datetime, ais_dir: Path, static_days_before: int) -> dict[str, float]:
    """Lungimea raportată de fiecare navă (rapoartele statice), pentru regulile radar; doar valorile pozitive."""
    st = static_table(_days(start - timedelta(days=static_days_before), end), ais_dir)
    st = st[pd.to_numeric(st["length_m"], errors="coerce") > 0]
    return {str(m): float(v) for m, v in zip(st["mmsi"], st["length_m"])}


def load_recorded(start: datetime, end: datetime, ais_dir: Path, static_days_before: int) -> pd.DataFrame:
    """Rapoartele de poziție cu start <= timestamp <= end, cu numele și tipul din rapoartele statice.

    Aceleași coloane ca data.loader.load_ais (contractul PositionMessage), cu simulated=False.
    """
    pos = _read("positions", _days(start, end), ais_dir)
    if pos.empty:
        return pd.DataFrame(columns=COLUMNS)
    pos = pos[is_vessel_mmsi(pos["mmsi"])].copy()
    pos["timestamp"] = pd.to_datetime(pos["received_utc"], utc=True, format="ISO8601")
    pos = pos[(pos["timestamp"] >= pd.Timestamp(start)) & (pos["timestamp"] <= pd.Timestamp(end))]
    pos = pos.drop_duplicates(subset=["mmsi", "timestamp"])
    st = static_table(_days(start - timedelta(days=static_days_before), end), ais_dir)
    df = pos.merge(st[["mmsi", "vessel_name", "ship_type"]], on="mmsi", how="left")
    for c in ("sog_kn", "cog_deg", "heading_deg"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["source"] = "ais"
    df["simulated"] = False
    for c in ("vessel_name", "ship_type"):
        df[c] = df[c].astype(object).where(df[c].notna(), None)
    return df[COLUMNS].sort_values(["mmsi", "timestamp"]).reset_index(drop=True)


def recorded_range(ais_dir: Path) -> tuple[datetime, datetime] | None:
    """Primul și ultimul moment înregistrat, sau None dacă nu există înregistrări."""
    files = sorted(ais_dir.glob("positions-*.csv"))
    if not files:
        return None
    first = pd.read_csv(files[0], usecols=["received_utc"], nrows=1)["received_utc"]
    last = pd.read_csv(files[-1], usecols=["received_utc"])["received_utc"]
    if first.empty or last.empty:
        return None
    return pd.Timestamp(first.iloc[0]).to_pydatetime(), pd.Timestamp(last.iloc[-1]).to_pydatetime()


def _cells(lat: np.ndarray, lon: np.ndarray, size: float) -> tuple[np.ndarray, np.ndarray]:
    return np.floor(lat / size).astype(int), np.floor(lon / size).astype(int)


def in_cells(lat: float, lon: float, cells: set[Cell], size: float) -> bool:
    return (int(np.floor(lat / size)), int(np.floor(lon / size))) in cells


def coverage_cells(df: pd.DataFrame, cfg: dict) -> set[Cell]:
    """Celulele (i, j) de live.coverage_cell_deg cu destule mesaje de la destule nave, în destule ore diferite."""
    c = cfg["live"]
    if df.empty:
        return set()
    i, j = _cells(df["lat"].to_numpy(), df["lon"].to_numpy(), c["coverage_cell_deg"])
    hour = df["timestamp"].dt.floor("h").to_numpy()
    g = pd.DataFrame({"i": i, "j": j, "mmsi": df["mmsi"].to_numpy(), "h": hour}).groupby(["i", "j"])
    stats = g.agg(n=("mmsi", "size"), v=("mmsi", "nunique"), hours=("h", "nunique"))
    ok = stats[(stats["n"] >= c["coverage_min_messages"]) & (stats["v"] >= c["coverage_min_vessels"])
               & (stats["hours"] >= c["coverage_min_hours"])]
    return {(int(a), int(b)) for a, b in ok.index}


def anchorage_cells(df: pd.DataFrame, cfg: dict) -> set[Cell]:
    """Celulele (i, j) de live.anchorage_cell_deg unde cel puțin N nave diferite au stat pe loc."""
    c = cfg["live"]
    df = df[df["sog_kn"] <= c["anchorage_max_sog_kn"]]
    if df.empty:
        return set()
    i, j = _cells(df["lat"].to_numpy(), df["lon"].to_numpy(), c["anchorage_cell_deg"])
    g = pd.DataFrame({"i": i, "j": j, "mmsi": df["mmsi"].to_numpy()}).groupby(["i", "j"])["mmsi"].nunique()
    return {(int(a), int(b)) for (a, b), v in g.items() if v >= c["anchorage_min_vessels"]}


def coverage_boxes(cells: set[Cell], size: float) -> list[list[float]]:
    """Celulele ca dreptunghiuri [lat_s, lon_v, lat_n, lon_e], pentru hartă."""
    return [[round(i * size, 4), round(j * size, 4), round((i + 1) * size, 4), round((j + 1) * size, 4)]
            for i, j in sorted(cells)]
