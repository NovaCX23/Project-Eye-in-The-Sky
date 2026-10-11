"""Zone de excludere și acoperire: unde un comportament (ex. viteză mică, tăcere) e normal sau nu dovedește nimic.

Două surse:
  - zonele desenate din assets/infrastructure.geojson (proprietatea "exclusion": true), mereu active;
  - zonele învățate din înregistrarea AIS reală (LearnedZones, construite de core din data/recorded.py):
    ancorajele (excludere) și acoperirea de recepție (o tăcere în afara ei nu e o gaură AIS).
Ce reguli țin cont de excludere se decide în config.yaml: detect.exclusion.applies_to.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from contracts.assets import in_exclusion_zone

LEARNED_ANCHORAGE = "learned-anchorage"


@dataclass(frozen=True)
class LearnedZones:
    """Hărți învățate din datele reale; celule (i, j) = (floor(lat / mărime), floor(lon / mărime))."""

    bbox: dict
    coverage_cell_deg: float
    anchorage_cell_deg: float
    coverage: frozenset = field(default_factory=frozenset)
    anchorages: frozenset = field(default_factory=frozenset)


def _cell(lat: float, lon: float, size: float) -> tuple[int, int]:
    return math.floor(lat / size), math.floor(lon / size)


def is_excluded(rule: str, lat: float, lon: float, cfg: dict, learned: LearnedZones | None = None) -> str | None:
    """Întoarce id-ul zonei care exclude regula în acest punct, sau None."""
    if rule not in cfg["detect"]["exclusion"]["applies_to"]:
        return None
    zone = in_exclusion_zone(lat, lon)
    if zone is None and learned is not None and _cell(lat, lon, learned.anchorage_cell_deg) in learned.anchorages:
        zone = LEARNED_ANCHORAGE
    return zone


def is_covered(lat: float, lon: float, learned: LearnedZones | None) -> bool:
    """Se aude AIS aici? Fără hărți învățate (date sintetice) toată zona de acoperire contează ca acoperită."""
    return learned is None or _cell(lat, lon, learned.coverage_cell_deg) in learned.coverage


def coverage_bbox(cfg: dict, learned: LearnedZones | None) -> dict:
    """Zona AIS urmărită: a zonei live dacă rulăm pe date reale, altfel cea a scenariului."""
    return learned.bbox if learned is not None else cfg["scenario"]["coverage_bbox"]
