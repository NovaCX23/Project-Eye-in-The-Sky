"""Recomandarea unității de patrulare: ETA minim, pe distanță haversine."""

from __future__ import annotations

from contracts.assets import load_patrol_units
from contracts.geo import haversine_km, kn_to_kmh
from contracts.models import PatrolRecommendation

LEVEL_ORDER = ("low", "medium", "high", "critical")


def recommend(lat: float, lon: float, level: str, cfg: dict) -> PatrolRecommendation | None:
    if LEVEL_ORDER.index(level) < LEVEL_ORDER.index(cfg["patrol"]["recommend_min_level"]):
        return None
    best = None
    for u in load_patrol_units():
        # STUB: linie dreaptă, fără ocolirea uscatului, fără disponibilitatea unității.
        dist = haversine_km(u.lat, u.lon, lat, lon)
        eta = dist / kn_to_kmh(u.speed_kn) * 60.0
        if best is None or eta < best.eta_min:
            best = PatrolRecommendation(unit_id=u.unit_id, unit_name=u.name, distance_km=round(dist, 1),
                                        eta_min=round(eta, 1), simulated=u.simulated)
    return best
