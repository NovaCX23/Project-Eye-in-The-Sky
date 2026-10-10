"""Unitățile de patrulare: mișcare pe rută, trimitere spre alerte, ETA din poziția curentă, repartizare pe priorități.

Model (determinist): de la scenario.start, fiecare unitate își parcurge ruta în buclă cu patrol_speed_kn.
La fiecare trimitere se adaugă o etapă (moment, țintă, alertă): unitatea pleacă din poziția de atunci spre țintă
cu speed_kn și rămâne la fața locului. Poziția la orice moment se calculează doar din etapele de până atunci.
"""

from __future__ import annotations

from collections.abc import Container
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache

from contracts.assets import load_patrol_units
from contracts.geo import destination, haversine_km, initial_bearing_deg, kn_to_kmh
from contracts.models import PatrolRecommendation, TrackPoint, VesselTrack
from contracts.runtime import ASSETS_DIR, parse_time, read_json

LEVEL_ORDER = ("low", "medium", "high", "critical")
SHIP_TYPE = "patrol"


@dataclass(frozen=True)
class UnitPlan:
    unit_id: str
    name: str
    mmsi: str
    base_name: str
    base: tuple[float, float]
    route: tuple[tuple[float, float], ...]
    patrol_kn: float
    response_kn: float
    simulated: bool


@dataclass(frozen=True)
class Leg:
    """O trimitere: din momentul t, unitatea merge spre (lat, lon) pentru alerta alert_id."""

    t: datetime
    lat: float
    lon: float
    alert_id: str


@dataclass(frozen=True)
class UnitState:
    lat: float
    lon: float
    sog: float
    cog: float | None


@lru_cache(maxsize=4)
def load_plans() -> tuple[UnitPlan, ...]:
    # contracts/assets.py nu citește câmpurile de rută (contractele sunt înghețate), deci le citim aici
    # din același fișier; câmpurile de bază vin tot prin încărcătorul comun.
    raw = {u["id"]: u for u in read_json(ASSETS_DIR / "patrol_units.json")["units"]}
    plans = []
    for u in load_patrol_units():
        r = raw[u.unit_id]
        route = tuple((float(p[0]), float(p[1])) for p in r.get("route") or [(u.lat, u.lon)])
        plans.append(UnitPlan(unit_id=u.unit_id, name=u.name, mmsi=str(r["mmsi"]), base_name=r.get("base", ""),
                              base=(u.lat, u.lon), route=route, patrol_kn=float(r.get("patrol_speed_kn", 0.0)),
                              response_kn=u.speed_kn, simulated=u.simulated))
    return tuple(plans)


def eligible(level: str, cfg: dict) -> bool:
    return LEVEL_ORDER.index(level) >= LEVEL_ORDER.index(cfg["patrol"]["recommend_min_level"])


def _route_state(plan: UnitPlan, t: datetime, start: datetime) -> UnitState:
    segs = [(a, b, haversine_km(*a, *b)) for a, b in zip(plan.route, plan.route[1:])]
    loop_km = sum(s[2] for s in segs)
    if loop_km == 0 or plan.patrol_kn <= 0:
        lat, lon = plan.route[0]
        return UnitState(lat, lon, 0.0, None)
    hours = max(0.0, (t - start).total_seconds() / 3600.0)
    d = (kn_to_kmh(plan.patrol_kn) * hours) % loop_km
    for a, b, km in segs:
        if d <= km:
            brg = initial_bearing_deg(*a, *b)
            lat, lon = destination(*a, brg, d)
            return UnitState(lat, lon, plan.patrol_kn, brg)
        d -= km
    lat, lon = plan.route[-1]
    return UnitState(lat, lon, plan.patrol_kn, None)


def _advance(lat: float, lon: float, target: tuple[float, float], t0: datetime, t1: datetime,
             speed_kn: float) -> UnitState:
    """Poziția după ce unitatea a mers din (lat, lon) spre țintă între t0 și t1; odată ajunsă, stă pe loc."""
    total = haversine_km(lat, lon, *target)
    travelled = kn_to_kmh(speed_kn) * max(0.0, (t1 - t0).total_seconds() / 3600.0)
    if travelled >= total:
        return UnitState(target[0], target[1], 0.0, None)
    brg = initial_bearing_deg(lat, lon, *target)
    nlat, nlon = destination(lat, lon, brg, travelled)
    return UnitState(nlat, nlon, speed_kn, brg)


def state_at(plan: UnitPlan, t: datetime, legs: list[Leg], start: datetime) -> UnitState:
    past = [leg for leg in legs if leg.t <= t]
    if not past:
        return _route_state(plan, t, start)
    s = _route_state(plan, past[0].t, start)
    for k, leg in enumerate(past):
        until = past[k + 1].t if k + 1 < len(past) else t
        s = _advance(s.lat, s.lon, (leg.lat, leg.lon), leg.t, until, plan.response_kn)
    return s


def _recommendation(plan: UnitPlan, s: UnitState, lat: float, lon: float) -> PatrolRecommendation:
    dist = haversine_km(s.lat, s.lon, lat, lon)
    eta = dist / kn_to_kmh(plan.response_kn) * 60.0
    return PatrolRecommendation(unit_id=plan.unit_id, unit_name=plan.name, distance_km=round(dist, 1),
                                eta_min=round(eta, 1), simulated=plan.simulated)


def recommend(lat: float, lon: float, level: str, cfg: dict, now: datetime, legs: dict[str, list[Leg]] | None = None,
              busy: Container[str] = (), only: str | None = None) -> PatrolRecommendation | None:
    """Unitatea cu ETA minim, din poziția ei la `now`, care nu e în `busy`; cu `only`, doar acea unitate."""
    if not eligible(level, cfg):
        return None
    start = parse_time(cfg["scenario"]["start"])
    legs = legs or {}
    best = None
    for plan in load_plans():
        if plan.unit_id in busy or (only is not None and plan.unit_id != only):
            continue
        # STUB: linie dreaptă, fără ocolirea uscatului.
        rec = _recommendation(plan, state_at(plan, now, legs.get(plan.unit_id, []), start), lat, lon)
        if best is None or rec.eta_min < best.eta_min:
            best = rec
    return best


def assign(candidates: list[tuple[str, float, float, str]], cfg: dict, dispatched: dict[str, str],
           now: datetime, legs: dict[str, list[Leg]]) -> dict[str, PatrolRecommendation]:
    """Repartizează unitățile pe alerte, în ordinea priorității (candidații vin deja sortați).

    candidates: (alert_id, lat, lon, level). `dispatched` (alert_id -> unit_id) și `legs` (unit_id -> trimiteri)
    sunt memoria între batch-uri. Cu patrol.one_alert_per_unit, o unitate servește o singură alertă, iar o unitate
    trimisă rămâne la alerta ei; fără, unitățile nu sunt trimise, doar recomandate (pot fi recomandate de mai multe ori).
    """
    exclusive = cfg["patrol"]["one_alert_per_unit"]
    out: dict[str, PatrolRecommendation] = {}
    busy: set[str] = set()
    if exclusive:
        for alert_id, lat, lon, level in candidates:
            prev = dispatched.get(alert_id)
            if prev is not None and prev not in busy:
                rec = recommend(lat, lon, level, cfg, now, legs, only=prev)
                if rec:
                    out[alert_id] = rec
                    busy.add(prev)
                    # Poziția alertei se poate muta (ex. centrul unui loitering care crește): unitatea își corectează
                    # direcția din poziția curentă.
                    last = legs.get(prev, [])[-1:]
                    if last and last[0].alert_id == alert_id and (last[0].lat, last[0].lon) != (lat, lon):
                        legs[prev].append(Leg(now, lat, lon, alert_id))
    for alert_id, lat, lon, level in candidates:
        if alert_id in out:
            continue
        rec = recommend(lat, lon, level, cfg, now, legs, busy=busy if exclusive else ())
        if rec:
            out[alert_id] = rec
            if exclusive:
                busy.add(rec.unit_id)
                dispatched[alert_id] = rec.unit_id
                legs.setdefault(rec.unit_id, []).append(Leg(now, lat, lon, alert_id))
    return out


def tracks(legs: dict[str, list[Leg]], now: datetime, cfg: dict, decimals: int) -> list[VesselTrack]:
    """Traseele unităților de la scenario.start până la `now` (inclusiv), ca piste de navă în timeline."""
    start = parse_time(cfg["scenario"]["start"])
    step = timedelta(minutes=cfg["patrol"]["track_step_min"])
    times = []
    t = start
    while t < now:
        times.append(t)
        t += step
    times.append(now)
    out = []
    for plan in load_plans():
        unit_legs = legs.get(plan.unit_id, [])
        pts = []
        for t in times:
            s = state_at(plan, t, unit_legs, start)
            pts.append(TrackPoint(t=t, lat=round(s.lat, decimals), lon=round(s.lon, decimals), sog=round(s.sog, 1),
                                  cog=None if s.cog is None else round(s.cog, 0)))
        out.append(VesselTrack(mmsi=plan.mmsi, name=plan.name, ship_type=SHIP_TYPE, simulated=plan.simulated, points=pts))
    return out
