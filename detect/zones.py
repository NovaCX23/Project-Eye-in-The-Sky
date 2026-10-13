"""Zone de excludere și acoperire: unde un comportament (ex. viteză mică, tăcere) e normal sau nu dovedește nimic.

Două surse:
  - zonele desenate din infrastructure.geojson al zonei rulate (proprietatea "exclusion": true), mereu active
    (assets/ pentru scenariul demo, assets/areas/<zonă>/ în modul live, vezi contracts.assets.area_assets_dir);
  - zonele învățate din înregistrarea AIS reală (LearnedZones, construite de core din data/recorded.py):
    ancorajele (excludere) și acoperirea de recepție (o tăcere în afara ei nu e o gaură AIS);
  - pe date reale, zona-tampon de port: mai aproape de coasta OpenStreetMap decât detect.exclusion.port_buffer_km
    (porturi, cheiuri, bazine; core dă funcția de distanță, construită de sar/landmask.py).
Ce reguli țin cont de excludere se decide în config.yaml: detect.exclusion.applies_to.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field

from contracts.assets import area_infrastructure, in_exclusion_zone

LEARNED_ANCHORAGE = "learned-anchorage"
PORT_BUFFER = "port-buffer"


@dataclass(frozen=True)
class LearnedZones:
    """Hărți învățate din datele reale; celule (i, j) = (floor(lat / mărime), floor(lon / mărime))."""

    bbox: dict
    coverage_cell_deg: float
    anchorage_cell_deg: float
    coverage: frozenset = field(default_factory=frozenset)
    anchorages: frozenset = field(default_factory=frozenset)
    # f(lat, lon) -> km până la coastă (0 pe uscat și în bazinele portuare); None = linia de coastă necunoscută.
    coast_km: Callable[[float, float], float] | None = field(default=None, compare=False)


def _cell(lat: float, lon: float, size: float) -> tuple[int, int]:
    return math.floor(lat / size), math.floor(lon / size)


def is_excluded(rule: str, lat: float, lon: float, cfg: dict, learned: LearnedZones | None = None) -> str | None:
    """Întoarce id-ul zonei care exclude regula în acest punct, sau None."""
    if rule not in cfg["detect"]["exclusion"]["applies_to"]:
        return None
    zone = in_exclusion_zone(lat, lon, area_infrastructure(cfg))
    if zone is None and learned is not None and _cell(lat, lon, learned.anchorage_cell_deg) in learned.anchorages:
        zone = LEARNED_ANCHORAGE
    if (zone is None and learned is not None and learned.coast_km is not None
            and learned.coast_km(lat, lon) < cfg["detect"]["exclusion"]["port_buffer_km"]):
        zone = PORT_BUFFER
    return zone


def is_covered(lat: float, lon: float, learned: LearnedZones | None) -> bool:
    """Se aude AIS aici? Fără hărți învățate (date sintetice) toată zona de acoperire contează ca acoperită."""
    return learned is None or _cell(lat, lon, learned.coverage_cell_deg) in learned.coverage


def coverage_bbox(cfg: dict, learned: LearnedZones | None) -> dict:
    """Zona AIS urmărită: a zonei live dacă rulăm pe date reale, altfel cea a scenariului."""
    return learned.bbox if learned is not None else cfg["scenario"]["coverage_bbox"]
