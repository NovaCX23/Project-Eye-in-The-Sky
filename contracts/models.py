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
    """Un mesaj AIS de poziție (un rând din out/ais.csv)."""

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
    """Un eveniment produs de un detector (AIS, acustic sau fibră)."""

    event_id: str = Field(description="Id determinist: hash(sursă, tip, mmsi/senzor, start)")
    event_type: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    source: EventSource
    mmsi: str | None = Field(default=None, pattern=r"^\d{9}$")
    sensor_id: str | None = None
    start: datetime
    end: datetime | None = Field(default=None, description="None = în desfășurare la momentul now")
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    confidence: float = Field(ge=0, le=1)
    metrics: dict[str, MetricValue] = Field(
        default_factory=dict, description="Numerele detectorului, folosite în explicații"
    )
    simulated: bool = False


class ScoreFactor(_Model):
    """O componentă a scorului aditiv."""

    code: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label: str
    points: int
    detail: str = Field(description="Propoziție din șablon, cu numerele detectorului")
    event_id: str | None = None
    added_at: datetime = Field(description="Momentul (now) la care factorul a intrat în scor")
    simulated: bool = False


class ScorePoint(_Model):
    """Starea alertei la momentul t; interfața o afișează fără să recalculeze nimic."""

    t: datetime
    score: int = Field(ge=0, le=100)
    level: AlertLevel
    unit_id: str | None = Field(default=None, description="Unitatea recomandată la acest moment")
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
    """O alertă fuzionată pentru un incident al unei nave."""

    alert_id: str = Field(description="Id determinist: hash(mmsi, tip primar, start)")
    mmsi: str = Field(pattern=r"^\d{9}$")
    vessel_name: str | None = None
    alert_type: str = Field(description="Tipul evenimentului care a deschis incidentul")
    start_time: datetime
    created_at: datetime = Field(description="Primul now la care alerta a fost emisă")
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
    """Fișierul out/timeline.json, singura intrare a interfeței web."""

    schema_version: str = SCHEMA_VERSION
    mode: Literal["single", "replay", "watch"]
    batch_index: int = Field(ge=0)
    scenario_start: datetime
    now: datetime = Field(description="Nimic din fișier nu are timestamp > now")
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
