"""Geometrie sferică partajată. Toate distanțele trec pe aici (haversine).

Regulă: niciodată distanță euclidiană pe lat/lon.
"""

from __future__ import annotations

import math

import numpy as np

EARTH_RADIUS_KM = 6371.0088  # raza medie IUGG
KM_PER_NM = 1.852            # definiția milei marine


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distanța pe cerc mare între două puncte, în km."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def haversine_km_np(lat1, lon1, lat2, lon2) -> np.ndarray:
    """Varianta vectorizată (numpy) a haversine_km."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dlmb = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.minimum(1.0, np.sqrt(a)))


def initial_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def destination(lat: float, lon: float, bearing_deg: float, distance_km: float) -> tuple[float, float]:
    """Punctul aflat la distance_km pe azimutul bearing_deg (sferă)."""
    d = distance_km / EARTH_RADIUS_KM
    b = math.radians(bearing_deg)
    p1, l1 = math.radians(lat), math.radians(lon)
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(b))
    l2 = l1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(p1), math.cos(d) - math.sin(p1) * math.sin(p2))
    return math.degrees(p2), (math.degrees(l2) + 540.0) % 360.0 - 180.0


def point_to_segment_km(lat: float, lon: float, a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distanța minimă de la un punct la un segment de cerc mare (cross-track / along-track)."""
    lat1, lon1 = a
    lat2, lon2 = b
    d13 = haversine_km(lat1, lon1, lat, lon)
    d12 = haversine_km(lat1, lon1, lat2, lon2)
    if d12 == 0.0:
        return d13
    th13 = math.radians(initial_bearing_deg(lat1, lon1, lat, lon))
    th12 = math.radians(initial_bearing_deg(lat1, lon1, lat2, lon2))
    r = EARTH_RADIUS_KM
    dxt = math.asin(max(-1.0, min(1.0, math.sin(d13 / r) * math.sin(th13 - th12)))) * r
    cos_ratio = math.cos(d13 / r) / max(1e-12, math.cos(dxt / r))
    dat = math.acos(max(-1.0, min(1.0, cos_ratio))) * r
    if math.cos(th13 - th12) < 0:  # proiecția cade înaintea lui A
        return d13
    if dat > d12:  # proiecția cade după B
        return haversine_km(lat2, lon2, lat, lon)
    return abs(dxt)


def point_to_polyline_km(lat: float, lon: float, coords_latlon: list[tuple[float, float]]) -> float:
    if len(coords_latlon) == 1:
        return haversine_km(lat, lon, *coords_latlon[0])
    return min(point_to_segment_km(lat, lon, a, b) for a, b in zip(coords_latlon, coords_latlon[1:]))


def kn_to_kmh(kn: float) -> float:
    return kn * KM_PER_NM


def kmh_to_kn(kmh: float) -> float:
    return kmh / KM_PER_NM
