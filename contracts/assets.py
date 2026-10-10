"""Încărcarea fișierelor din assets/ (infrastructură, unități de patrulare)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from shapely.geometry import Point, shape

from contracts.geo import haversine_km, point_to_polyline_km
from contracts.runtime import ASSETS_DIR, read_json


@dataclass(frozen=True)
class InfraFeature:
    infra_id: str
    name: str
    kind: str            # platform | pipeline | cable | anchorage | port_approach
    geom_type: str       # Point | LineString | Polygon
    coords: tuple        # (lat, lon) pentru Point; listă de (lat, lon) pentru linii/contur
    protected: bool      # infrastructură de protejat (contează la scor)
    exclusion: bool      # zonă unde comportamentul lent e normal
    approximate: bool
    shape: object        # geometria shapely (lon, lat), doar pentru apartenența la poligon


@dataclass(frozen=True)
class PatrolUnit:
    unit_id: str
    name: str
    lat: float
    lon: float
    speed_kn: float
    simulated: bool


@lru_cache(maxsize=4)
def load_infrastructure(path: Path | None = None) -> tuple[InfraFeature, ...]:
    gj = read_json(path or ASSETS_DIR / "infrastructure.geojson")
    out = []
    for f in gj["features"]:
        g, p = f["geometry"], f["properties"]
        if g["type"] == "Point":
            coords = (g["coordinates"][1], g["coordinates"][0])
        elif g["type"] == "LineString":
            coords = tuple((c[1], c[0]) for c in g["coordinates"])
        elif g["type"] == "Polygon":
            coords = tuple((c[1], c[0]) for c in g["coordinates"][0])
        else:
            raise ValueError(f"Geometrie nesuportată: {g['type']}")
        out.append(
            InfraFeature(
                infra_id=p["id"],
                name=p["name"],
                kind=p["kind"],
                geom_type=g["type"],
                coords=coords,
                protected=bool(p.get("protected", False)),
                exclusion=bool(p.get("exclusion", False)),
                approximate=bool(p.get("approximate", True)),
                shape=shape(g),
            )
        )
    return tuple(out)


def distance_to_feature_km(lat: float, lon: float, feat: InfraFeature) -> float:
    if feat.geom_type == "Point":
        return haversine_km(lat, lon, *feat.coords)
    if feat.geom_type == "Polygon" and feat.shape.contains(Point(lon, lat)):
        return 0.0
    return point_to_polyline_km(lat, lon, list(feat.coords))


def in_exclusion_zone(lat: float, lon: float, features: tuple[InfraFeature, ...] | None = None) -> str | None:
    """Întoarce id-ul zonei de excludere care conține punctul, sau None."""
    for f in features or load_infrastructure():
        if f.exclusion and f.geom_type == "Polygon" and f.shape.contains(Point(lon, lat)):
            return f.infra_id
    return None


@lru_cache(maxsize=4)
def load_patrol_units(path: Path | None = None) -> tuple[PatrolUnit, ...]:
    data = read_json(path or ASSETS_DIR / "patrol_units.json")
    return tuple(
        PatrolUnit(
            unit_id=u["id"],
            name=u["name"],
            lat=u["lat"],
            lon=u["lon"],
            speed_kn=u["speed_kn"],
            simulated=bool(u.get("simulated", True)),
        )
        for u in data["units"]
    )
