"""Recomandarea unității de patrulare: ETA minim, pe distanță haversine, dintre unitățile disponibile."""

from __future__ import annotations

from collections.abc import Container

from contracts.assets import load_patrol_units
from contracts.geo import haversine_km, kn_to_kmh
from contracts.models import PatrolRecommendation

LEVEL_ORDER = ("low", "medium", "high", "critical")


def eligible(level: str, cfg: dict) -> bool:
    return LEVEL_ORDER.index(level) >= LEVEL_ORDER.index(cfg["patrol"]["recommend_min_level"])


def recommend(lat: float, lon: float, level: str, cfg: dict, busy: Container[str] = (),
              only: str | None = None) -> PatrolRecommendation | None:
    """Unitatea cu ETA minim care nu e în `busy`; cu `only`, doar acea unitate (deja trimisă)."""
    if not eligible(level, cfg):
        return None
    best = None
    for u in load_patrol_units():
        if u.unit_id in busy or (only is not None and u.unit_id != only):
            continue
        # STUB: linie dreaptă, fără ocolirea uscatului.
        dist = haversine_km(u.lat, u.lon, lat, lon)
        eta = dist / kn_to_kmh(u.speed_kn) * 60.0
        if best is None or eta < best.eta_min:
            best = PatrolRecommendation(unit_id=u.unit_id, unit_name=u.name, distance_km=round(dist, 1),
                                        eta_min=round(eta, 1), simulated=u.simulated)
    return best


def assign(candidates: list[tuple[str, float, float, str]], cfg: dict,
           dispatched: dict[str, str]) -> dict[str, PatrolRecommendation]:
    """Repartizează unitățile pe alerte, în ordinea priorității (candidații vin deja sortați).

    candidates: (alert_id, lat, lon, level). `dispatched` (alert_id -> unit_id) e memoria între batch-uri:
    o unitate deja trimisă rămâne la alerta ei. Cu patrol.one_alert_per_unit, o unitate servește o singură alertă.
    """
    exclusive = cfg["patrol"]["one_alert_per_unit"]
    out: dict[str, PatrolRecommendation] = {}
    busy: set[str] = set()
    if exclusive:
        for alert_id, lat, lon, level in candidates:
            prev = dispatched.get(alert_id)
            if prev is not None and prev not in busy:
                rec = recommend(lat, lon, level, cfg, only=prev)
                if rec:
                    out[alert_id] = rec
                    busy.add(prev)
    for alert_id, lat, lon, level in candidates:
        if alert_id in out:
            continue
        rec = recommend(lat, lon, level, cfg, busy=busy if exclusive else ())
        if rec:
            out[alert_id] = rec
            busy.add(rec.unit_id)
            dispatched[alert_id] = rec.unit_id
    return out
