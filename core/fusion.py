"""Fuziune: evenimente (AIS, acustic, fibră) -> alerte cu scor, explicație și recomandare.

Un incident = evenimentele AIS ale aceleiași nave apropiate în timp. Senzorii fără MMSI
(acustic, fibră) și celelalte nave suspecte din zonă se atașează ca factori de context.

# STUB: doar evenimentele AIS deschid alerte; un senzor fără navă AIS în zonă nu produce alertă.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from contracts.assets import distance_to_feature_km, load_infrastructure
from contracts.geo import haversine_km
from contracts.models import KNOWN_EVENT_TYPES, Alert, InfraProximity, ScoreFactor, ScorePoint, SensorEvent
from contracts.runtime import stable_id
from core import explain, patrol, scoring

CONTEXT_SOURCES = ("acoustic", "fibre")
NEAREST_INFRA_COUNT = 3


@dataclass
class AlertMemory:
    """Ce trebuie ținut minte între micro-batch-uri (doar momente, nu rezultate)."""

    created_at: dict[str, datetime] = field(default_factory=dict)
    factor_added: dict[tuple[str, str], datetime] = field(default_factory=dict)
    history: dict[str, list[ScorePoint]] = field(default_factory=dict)
    # Odată ce un eveniment a deschis o alertă, incidentul își păstrează id-ul,
    # chiar dacă ulterior apare un eveniment cu același start (ex. inconsistența de viteză).
    primary_of_event: dict[str, str] = field(default_factory=dict)


def _type_rank(event_type: str) -> int:
    return KNOWN_EVENT_TYPES.index(event_type) if event_type in KNOWN_EVENT_TYPES else len(KNOWN_EVENT_TYPES)


@dataclass
class Episode:
    mmsi: str
    events: list[SensorEvent]
    primary_id: str | None = None

    @property
    def primary(self) -> SensorEvent:
        return next((e for e in self.events if e.event_id == self.primary_id), self.events[0])

    def end(self, now: datetime) -> datetime:
        return max((e.end or now) for e in self.events)


def _episodes(events: list[SensorEvent], now: datetime, cfg: dict) -> list[Episode]:
    window = timedelta(minutes=cfg["fusion"]["same_vessel_window_min"])
    ais = sorted((e for e in events if e.source == "ais" and e.mmsi),
                 key=lambda e: (e.mmsi, e.start, _type_rank(e.event_type), e.event_id))
    out: list[Episode] = []
    for e in ais:
        last = out[-1] if out else None
        if last and last.mmsi == e.mmsi and e.start <= last.end(now) + window:
            last.events.append(e)
        else:
            out.append(Episode(e.mmsi, [e]))
    return out


def _infra(lat: float, lon: float) -> list[InfraProximity]:
    feats = [f for f in load_infrastructure() if f.protected]
    near = sorted(((distance_to_feature_km(lat, lon, f), f) for f in feats), key=lambda x: (x[0], x[1].infra_id))
    return [InfraProximity(infra_id=f.infra_id, name=f.name, kind=f.kind, distance_km=round(d, 2))
            for d, f in near[:NEAREST_INFRA_COUNT]]


def build_alerts(events: list[SensorEvent], now: datetime, cfg: dict, names: dict[str, str],
                 memory: AlertMemory) -> list[Alert]:
    fc = cfg["fusion"]
    episodes = _episodes(events, now, cfg)
    context = sorted((e for e in events if e.source in CONTEXT_SOURCES), key=lambda e: (e.start, e.event_id))
    alerts: list[Alert] = []
    for ep in episodes:
        known = sorted({memory.primary_of_event[e.event_id] for e in ep.events if e.event_id in memory.primary_of_event})
        ep.primary_id = known[0] if known else ep.events[0].event_id
    for ep in episodes:
        p = ep.primary
        alert_id = stable_id(ep.mmsi, p.event_type, p.start, prefix="alr-")
        ep_start, ep_end = p.start, ep.end(now)
        # (code, points, detail, event_id, simulated)
        raw: list[tuple[str, int, str, str | None, bool]] = []

        for code in sorted({e.event_type for e in ep.events}):
            best = max((e for e in ep.events if e.event_type == code), key=lambda e: (e.confidence, e.event_id))
            raw.append((code, scoring.points_for(code, cfg), explain.factor_detail(code, best.metrics, best.simulated),
                        best.event_id, best.simulated))

        infra = _infra(p.lat, p.lon)
        if infra and infra[0].distance_km <= fc["infra_radius_km"]:
            i0 = infra[0]
            raw.append(("near_infrastructure", scoring.points_for("near_infrastructure", cfg),
                        explain.factor_detail("near_infrastructure", {"distance_km": i0.distance_km, "name": i0.name}),
                        None, False))

        lo = ep_start - timedelta(minutes=fc["context_before_min"])
        hi = ep_end + timedelta(minutes=fc["context_after_min"])
        by_type: dict[str, tuple[float, SensorEvent]] = {}
        for c in context:
            d = haversine_km(p.lat, p.lon, c.lat, c.lon)
            if d <= fc["context_radius_km"] and lo <= c.start <= hi:
                cur = by_type.get(c.event_type)
                if cur is None or c.confidence > cur[1].confidence:
                    by_type[c.event_type] = (d, c)
        for code in sorted(by_type):
            d, c = by_type[code]
            vals = dict(c.metrics, dist_km=d, sensor_id=c.sensor_id)
            raw.append((code, scoring.points_for(code, cfg), explain.factor_detail(code, vals, c.simulated),
                        c.event_id, c.simulated))

        related = []
        for other in episodes:
            if other.mmsi == ep.mmsi:
                continue
            d = haversine_km(p.lat, p.lon, other.primary.lat, other.primary.lon)
            overlap = other.primary.start <= ep_end and ep_start <= other.end(now)
            if d <= fc["correlation_radius_km"] and overlap:
                related.append((d, other))
        if related:
            d, other = min(related, key=lambda x: (x[0], x[1].mmsi))
            raw.append(("correlated_vessel", scoring.points_for("correlated_vessel", cfg),
                        explain.factor_detail("correlated_vessel", {
                            "other_name": names.get(other.mmsi) or "unknown", "other_mmsi": other.mmsi, "dist_km": d}),
                        other.primary.event_id, other.primary.simulated))

        score = scoring.total([r[1] for r in raw], cfg)
        if score < cfg["score"]["alert_min"] and alert_id not in memory.created_at:
            continue
        level = scoring.level_for(score, cfg)
        created = memory.created_at.setdefault(alert_id, now)
        for e in ep.events:
            memory.primary_of_event.setdefault(e.event_id, p.event_id)
        factors = []
        for code, pts, detail, eid, sim in raw:
            added = memory.factor_added.setdefault((alert_id, code), now)
            factors.append(ScoreFactor(code=code, label=explain.label(code), points=pts, detail=detail,
                                       event_id=eid, added_at=added, simulated=sim))
        rec = patrol.recommend(p.lat, p.lon, level, cfg)
        hist = memory.history.setdefault(alert_id, [])
        unit = rec.unit_id if rec else None
        if not hist or hist[-1].score != score or hist[-1].unit_id != unit:
            hist.append(ScorePoint(t=now, score=score, level=level, unit_id=unit, eta_min=rec.eta_min if rec else None))
        alerts.append(Alert(
            alert_id=alert_id,
            mmsi=ep.mmsi,
            vessel_name=names.get(ep.mmsi),
            alert_type=p.event_type,
            start_time=ep_start,
            created_at=created,
            updated_at=hist[-1].t,
            lat=p.lat,
            lon=p.lon,
            risk_score=score,
            level=level,
            factors=factors,
            history=list(hist),
            explanation=explain.alert_text(names.get(ep.mmsi), ep.mmsi, score, level, [f.detail for f in factors],
                                           rec.model_dump() if rec else None),
            event_ids=sorted({e.event_id for e in ep.events} | {f.event_id for f in factors if f.event_id}),
            related_mmsis=sorted({o.mmsi for _, o in related}),
            nearest_infrastructure=infra,
            recommendation=rec,
            simulated=any(f.simulated for f in factors) or any(e.simulated for e in ep.events),
        ))
    return sorted(alerts, key=lambda a: (a.created_at, a.alert_id))
