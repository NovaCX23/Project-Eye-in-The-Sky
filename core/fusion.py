"""Fuziune: evenimente (AIS, radar, acustic, fibră) -> alerte cu scor, explicație și recomandare.

Un incident = evenimentele AIS și radar ale aceleiași nave apropiate în timp; o țintă radar fără AIS e propriul
ei incident (alertă fără MMSI). Senzorii fără MMSI (acustic, fibră) și celelalte nave suspecte din zonă se atașează
ca factori de context.

# STUB: acusticul și fibra nu deschid singure alerte; un astfel de senzor fără navă în zonă nu produce alertă.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from contracts.assets import area_infrastructure, distance_to_feature_km
from contracts.geo import haversine_km
from contracts.models import KNOWN_EVENT_TYPES, Alert, InfraProximity, ScoreFactor, ScorePoint, SensorEvent
from contracts.runtime import stable_id
from core import explain, patrol, scoring

CONTEXT_SOURCES = ("acoustic", "fibre")
INCIDENT_SOURCES = ("ais", "sar")   # deschid incidente: o navă AIS (mmsi) sau o țintă radar fără AIS (target_id)
NEAREST_INFRA_COUNT = 3


@dataclass
class AlertMemory:
    """Ce trebuie ținut minte între micro-batch-uri (doar momente, nu rezultate)."""

    created_at: dict[str, datetime] = field(default_factory=dict)
    factor_added: dict[tuple[str, str], datetime] = field(default_factory=dict)
    # Dovada unui factor (detail, event_id, simulated) se îngheață la intrarea în scor: la derularea înapoi,
    # interfața nu trebuie să arate cifre pe care sistemul nu le știa încă (ex. durata finală a găurii AIS).
    factor_evidence: dict[tuple[str, str], tuple[str, str | None, bool]] = field(default_factory=dict)
    history: dict[str, list[ScorePoint]] = field(default_factory=dict)
    # Odată ce un eveniment a deschis o alertă, incidentul își păstrează id-ul,
    # chiar dacă ulterior apare un eveniment cu același start (ex. inconsistența de viteză).
    primary_of_event: dict[str, str] = field(default_factory=dict)
    dispatched: dict[str, str] = field(default_factory=dict)  # alert_id -> unitatea deja trimisă
    unit_legs: dict[str, list[patrol.Leg]] = field(default_factory=dict)  # unit_id -> trimiterile, în ordine


@dataclass
class _Draft:
    """O alertă cu scorul calculat, înainte de repartizarea unităților de patrulare."""

    alert_id: str
    ep: Episode
    primary: SensorEvent
    start: datetime
    created: datetime
    score: int
    level: str
    factors: list[ScoreFactor]
    infra: list[InfraProximity]
    related: list[str]


def _type_rank(event_type: str) -> int:
    return KNOWN_EVENT_TYPES.index(event_type) if event_type in KNOWN_EVENT_TYPES else len(KNOWN_EVENT_TYPES)


def _key(e: SensorEvent) -> str | None:
    """Cui aparține evenimentul: navei AIS (mmsi) sau țintei radar fără AIS."""
    return e.mmsi or (f"target:{e.target_id}" if e.target_id else None)


@dataclass
class Episode:
    key: str
    events: list[SensorEvent]
    primary_id: str | None = None

    @property
    def mmsi(self) -> str | None:
        return None if self.key.startswith("target:") else self.key

    @property
    def target_id(self) -> str | None:
        return self.key.removeprefix("target:") if self.key.startswith("target:") else None

    @property
    def primary(self) -> SensorEvent:
        return next((e for e in self.events if e.event_id == self.primary_id), self.events[0])

    def end(self, now: datetime) -> datetime:
        return max((e.end or now) for e in self.events)


def _episodes(events: list[SensorEvent], now: datetime, cfg: dict) -> list[Episode]:
    window = timedelta(minutes=cfg["fusion"]["same_vessel_window_min"])
    own = sorted((e for e in events if e.source in INCIDENT_SOURCES and _key(e)),
                 key=lambda e: (_key(e), e.start, _type_rank(e.event_type), e.event_id))
    out: list[Episode] = []
    for e in own:
        last = out[-1] if out else None
        if last and last.key == _key(e) and e.start <= last.end(now) + window:
            last.events.append(e)
        else:
            out.append(Episode(_key(e), [e]))
    return out


def _infra(lat: float, lon: float, cfg: dict) -> list[InfraProximity]:
    feats = [f for f in area_infrastructure(cfg) if f.protected]
    near = sorted(((distance_to_feature_km(lat, lon, f), f) for f in feats), key=lambda x: (x[0], x[1].infra_id))
    return [InfraProximity(infra_id=f.infra_id, name=f.name, kind=f.kind, distance_km=round(d, 2))
            for d, f in near[:NEAREST_INFRA_COUNT]]


def build_alerts(events: list[SensorEvent], now: datetime, cfg: dict, names: dict[str, str],
                 memory: AlertMemory, last_seen: dict[str, tuple[float, float]] | None = None) -> list[Alert]:
    """last_seen: ultima poziție AIS a fiecărei nave la `now`; unitatea trimisă merge acolo (altfel la poziția alertei)."""
    last_seen = last_seen or {}
    fc = cfg["fusion"]
    weak = set(fc["weak_event_types"])
    episodes = _episodes(events, now, cfg)
    context = sorted((e for e in events if e.source in CONTEXT_SOURCES), key=lambda e: (e.start, e.event_id))
    alerts: list[Alert] = []
    drafts: list[_Draft] = []
    for ep in episodes:
        known = sorted({memory.primary_of_event[e.event_id] for e in ep.events if e.event_id in memory.primary_of_event})
        ep.primary_id = known[0] if known else ep.events[0].event_id
    for ep in episodes:
        p = ep.primary
        alert_id = stable_id(ep.mmsi or ep.target_id, p.event_type, p.start, prefix="alr-")
        ep_start, ep_end = p.start, ep.end(now)
        # (code, points, detail, event_id, simulated)
        raw: list[tuple[str, int, str, str | None, bool]] = []

        for code in sorted({e.event_type for e in ep.events}):
            best = max((e for e in ep.events if e.event_type == code), key=lambda e: (e.confidence, e.event_id))
            vals = dict(best.metrics, since=explain.clock(best.start))
            raw.append((code, scoring.points_for(code, cfg), explain.factor_detail(code, vals, best.simulated),
                        best.event_id, best.simulated))

        infra = _infra(p.lat, p.lon, cfg)
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
            vals = dict(c.metrics, dist_km=d, sensor_id=c.sensor_id, since=explain.clock(c.start))
            raw.append((code, scoring.points_for(code, cfg), explain.factor_detail(code, vals, c.simulated),
                        c.event_id, c.simulated))

        related = []
        for other in episodes:
            # Un indiciu slab (ex. o țintă radar unde recepția AIS nu e dovedită) nu face suspectă o altă navă.
            if other.key == ep.key or all(e.event_type in weak for e in other.events):
                continue
            d = haversine_km(p.lat, p.lon, other.primary.lat, other.primary.lon)
            overlap = other.primary.start <= ep_end and ep_start <= other.end(now)
            if d <= fc["correlation_radius_km"] and overlap:
                related.append((d, other))
        if related:
            d, other = min(related, key=lambda x: (x[0], x[1].key))
            raw.append(("correlated_vessel", scoring.points_for("correlated_vessel", cfg),
                        explain.factor_detail("correlated_vessel", {
                            "other_label": explain.vessel_label(names.get(other.mmsi), other.mmsi, other.target_id),
                            "dist_km": d}),
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
            detail, eid, sim = memory.factor_evidence.setdefault((alert_id, code), (detail, eid, sim))
            factors.append(ScoreFactor(code=code, label=explain.label(code), points=pts, detail=detail,
                                       event_id=eid, added_at=added, simulated=sim))
        drafts.append(_Draft(alert_id, ep, p, ep_start, created, score, level, factors, infra,
                             sorted({o.mmsi for _, o in related if o.mmsi})))

    # Unitățile se repartizează după ce se cunosc toate alertele: prioritate după nivel, scor, vechime.
    drafts.sort(key=lambda d: (-patrol.LEVEL_ORDER.index(d.level), -d.score, d.created, d.alert_id))
    recs = patrol.assign([(d.alert_id, *last_seen.get(d.ep.key, (d.primary.lat, d.primary.lon)), d.level)
                          for d in drafts], cfg, memory.dispatched, now, memory.unit_legs)
    eta_step = cfg["patrol"]["eta_update_min"]
    for d in drafts:
        rec = recs.get(d.alert_id)
        hist = memory.history.setdefault(d.alert_id, [])
        unit = rec.unit_id if rec else None
        eta = rec.eta_min if rec else None
        eta_moved = eta is not None and hist and hist[-1].eta_min is not None and (
            abs(hist[-1].eta_min - eta) >= eta_step or (eta == 0 and hist[-1].eta_min != 0))
        if not hist or hist[-1].score != d.score or hist[-1].unit_id != unit or eta_moved:
            hist.append(ScorePoint(t=now, score=d.score, level=d.level, unit_id=unit,
                                   eta_min=rec.eta_min if rec else None))
        name = names.get(d.ep.mmsi) if d.ep.mmsi else None
        alerts.append(Alert(
            alert_id=d.alert_id,
            mmsi=d.ep.mmsi,
            target_id=d.ep.target_id,
            vessel_name=name,
            alert_type=d.primary.event_type,
            start_time=d.start,
            created_at=d.created,
            updated_at=hist[-1].t,
            lat=d.primary.lat,
            lon=d.primary.lon,
            risk_score=d.score,
            level=d.level,
            factors=d.factors,
            history=list(hist),
            explanation=explain.alert_text(name, d.ep.mmsi, d.score, d.level, [f.detail for f in d.factors],
                                           rec.model_dump() if rec else None, target_id=d.ep.target_id),
            event_ids=sorted({e.event_id for e in d.ep.events} | {f.event_id for f in d.factors if f.event_id}),
            related_mmsis=d.related,
            nearest_infrastructure=d.infra,
            recommendation=rec,
            simulated=any(f.simulated for f in d.factors) or any(e.simulated for e in d.ep.events),
        ))
    return sorted(alerts, key=lambda a: (a.created_at, a.alert_id))
