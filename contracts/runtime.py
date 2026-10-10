"""Utilitare comune: căi, config, id-uri deterministe, timp, consolă."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config.yaml"
ASSETS_DIR = REPO_ROOT / "assets"
OUT_DIR = REPO_ROOT / "out"


def load_config(path: Path | str | None = None) -> dict[str, Any]:
    with open(path or CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def stable_id(*parts: object, prefix: str = "") -> str:
    """Id determinist: același input => același id, la orice rulare."""
    raw = "|".join(_canon(p) for p in parts)
    return prefix + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _canon(p: object) -> str:
    if isinstance(p, datetime):
        return iso(p)
    return str(p)


def parse_time(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    """ISO 8601 UTC cu sufix Z, fără microsecunde."""
    return parse_time(dt).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utf8_stdout() -> None:
    """Pe Windows, consola redirecționată nu e UTF-8; textul românesc ar da eroare."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def write_json_atomic(path: Path, data: Any) -> None:
    """Scrie întâi un fișier temporar, apoi îl redenumește: pagina nu citește niciodată un fișier pe jumătate."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def read_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
