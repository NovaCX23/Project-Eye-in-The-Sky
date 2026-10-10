"""Zone de excludere: unde un comportament (ex. viteză mică) e normal și nu produce evenimente.

Zonele vin din assets/infrastructure.geojson (proprietatea "exclusion": true).
Ce reguli țin cont de ele se decide în config.yaml: detect.exclusion.applies_to.
"""

from __future__ import annotations

from contracts.assets import in_exclusion_zone


def is_excluded(rule: str, lat: float, lon: float, cfg: dict) -> str | None:
    """Întoarce id-ul zonei care exclude regula în acest punct, sau None."""
    if rule not in cfg["detect"]["exclusion"]["applies_to"]:
        return None
    return in_exclusion_zone(lat, lon)
