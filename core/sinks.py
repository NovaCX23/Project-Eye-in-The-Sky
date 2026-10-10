"""Transportul de IEȘIRE (varianta B: fișier JSON scris atomic).

În varianta A (server + WebSocket) se înlocuiește doar acest modul și loader-ul din web/.
"""

from __future__ import annotations

from pathlib import Path

from contracts.models import Timeline
from contracts.runtime import write_json_atomic

TIMELINE_FILE = "timeline.json"


def write_timeline(tl: Timeline, out_dir: Path) -> Path:
    path = out_dir / TIMELINE_FILE
    write_json_atomic(path, tl.model_dump(mode="json"))
    return path
