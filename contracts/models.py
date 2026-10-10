"""Modelele de date partajate de toate modulele SeaGrid.

Se modifică DOAR prin skill-ul `contract-change` (vezi AGENTS.md).
Toate timpii sunt UTC, serializați ISO 8601. Distanțe în km, viteze în noduri.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0"

# Tipuri de evenimente cunoscute. `event_type` rămâne string liber (format snake_case),
# astfel încât o regulă nouă (skill-ul add-rule) nu cere schimbarea contractului.
KNOWN_EVENT_TYPES = (
    "ais_gap",
    "speed_inconsistency",
    "loitering",
    "position_jump",
    "acoustic_lowfreq",
    "fibre_vibration",
)

EventSource = Literal["ais", "acoustic", "fibre"]
AlertLevel = Literal["low", "medium", "high", "critical"]

MetricValue = float | int | str | bool | None


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PositionMessage(_Model):
    """One AIS position message (one row of out/ais.csv)."""

    mmsi: str = Field(pattern=r"^\d{9}$")
    timestamp: datetime
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    sog_kn: float | None = Field(default=None, ge=0, description="Speed over ground")
    cog_deg: float | None = Field(default=None, ge=0, lt=360, description="Course over ground")
    heading_deg: float | None = Field(default=None, ge=0, lt=360)
    vessel_name: str | None = None
    ship_type: str | None = None
    source: Literal["ais"] = "ais"
    simulated: bool = False


class SensorEvent(_Model):
    """An event produced by a detector (AIS, acoustic or fibre)."""

    event_id: str = Field(description="Deterministic id: hash(source, type, mmsi/sensor, start)")
    event_type: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    source: EventSource
    mmsi: str | None = Field(default=None, pattern=r"^\d{9}$")
    sensor_id: str | None = None
    start: datetime
    end: datetime | None = Field(default=None, description="None = still ongoing at time now")
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    confidence: float = Field(ge=0, le=1)
    metrics: dict[str, MetricValue] = Field(
        default_factory=dict, description="The detector's numbers, used in explanations"
    )
    simulated: bool = False


class ScoreFactor(_Model):
    """One component of the additive score."""

    code: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label: str
    points: int
    detail: str = Field(description="Template sentence filled with the detector's numbers")
    event_id: str | None = None
    added_at: datetime = Field(description="The moment (now) at which the factor entered the score")
    simulated: bool = False


class ScorePoint(_Model):
    """Alert state at time t; the UI displays it without recomputing anything."""

    t: datetime
    score: int = Field(ge=0, le=100)
    level: AlertLevel
    unit_id: str | None = Field(default=None, description="Recommended unit at this moment")
    eta_min: float | None = Field(default=None, ge=0)


class InfraProximity(_Model):
    infra_id: str
    name: str
    kind: str
    distance_km: float = Field(ge=0)


class PatrolRecommendation(_Model):
    unit_id: str
    unit_name: str
    distance_km: float = Field(ge=0)
    eta_min: float = Field(ge=0)
    simulated: bool = False


class Alert(_Model):
    """A fused alert for one vessel incident."""

    alert_id: str = Field(description="Deterministic id: hash(mmsi, primary type, start)")
    mmsi: str = Field(pattern=r"^\d{9}$")
    vessel_name: str | None = None
    alert_type: str = Field(description="Type of the event that opened the incident")
    start_time: datetime
    created_at: datetime = Field(description="First now at which the alert was emitted")
    updated_at: datetime
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    risk_score: int = Field(ge=0, le=100)
    level: AlertLevel
    factors: list[ScoreFactor]
    history: list[ScorePoint]
    explanation: str
    event_ids: list[str]
    related_mmsis: list[str] = Field(default_factory=list)
    nearest_infrastructure: list[InfraProximity] = Field(default_factory=list)
    recommendation: PatrolRecommendation | None = None
    simulated: bool = False


class TrackPoint(_Model):
    t: datetime
    lat: float
    lon: float
    sog: float | None = None
    cog: float | None = None


class VesselTrack(_Model):
    mmsi: str = Field(pattern=r"^\d{9}$")
    name: str | None = None
    ship_type: str | None = None
    simulated: bool = False
    points: list[TrackPoint]


class Timeline(_Model):
    """The out/timeline.json file, the web UI's only input."""

    schema_version: str = SCHEMA_VERSION
    mode: Literal["single", "replay", "watch"]
    batch_index: int = Field(ge=0)
    scenario_start: datetime
    now: datetime = Field(description="Nothing in the file has timestamp > now")
    simulated: bool
    reload_interval_s: float | None = None
    vessels: list[VesselTrack]
    events: list[SensorEvent]
    alerts: list[Alert]


ALL_MODELS: dict[str, type[BaseModel]] = {
    "PositionMessage": PositionMessage,
    "SensorEvent": SensorEvent,
    "Alert": Alert,
    "Timeline": Timeline,
}
