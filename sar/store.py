"""Unde stau trecerile radar procesate și cum se citesc (fără rețea).

data/raw/sar/<zonă>/ (nu se comite):
  coastline.json, sea.geojson      linia de coastă OpenStreetMap și poligonul mării (sar/landmask.py)
  <pass_id>/pass.json              trecerea procesată: momente, amprentă, ținte (sar/process.py)
  <pass_id>/overlay.png            imaginea radar pe grila Web Mercator (doar afișare)
  <pass_id>/chips/NNN.png          decupajul fiecărei ținte (doar afișare)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from contracts.runtime import RAW_DIR, active_area, parse_time, read_json

RAW_SAR_DIR = RAW_DIR / "sar"
RECORD_VERSION = 1
PASS_FILE = "pass.json"


def area_dir(cfg: dict) -> Path:
    return RAW_SAR_DIR / active_area(cfg)


def load_records(sar_dir: Path, until: datetime, since: datetime | None = None) -> list[dict]:
    """Trecerile procesate complet (cu imagine) achiziționate după `since` și publicate până la `until` inclusiv,
    în ordine cronologică.

    Momentul în care o trecere devine cunoscută e `available_at` (procesarea ESA), nu momentul achiziției.
    """
    out = []
    if not sar_dir.exists():
        return out
    for p in sorted(sar_dir.glob(f"*/{PASS_FILE}")):
        rec = read_json(p)
        if rec.get("version") != RECORD_VERSION or not rec.get("rendered"):
            continue
        if parse_time(rec["available_at"]) <= until and (since is None or parse_time(rec["acquired_at"]) >= since):
            out.append(rec)
    return sorted(out, key=lambda r: r["acquired_at"])
