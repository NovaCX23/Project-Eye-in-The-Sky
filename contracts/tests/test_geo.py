"""Haversine și distanțe punct-linie."""

from __future__ import annotations

import math

import numpy as np
import pytest

from contracts.geo import (
    EARTH_RADIUS_KM,
    destination,
    haversine_km,
    haversine_km_np,
    point_to_polyline_km,
    point_to_segment_km,
)

ONE_DEG_KM = 2 * math.pi * EARTH_RADIUS_KM / 360.0


def test_zero_distance():
    assert haversine_km(44.17, 28.65, 44.17, 28.65) == 0.0


def test_one_degree_latitude():
    assert haversine_km(44.0, 29.0, 45.0, 29.0) == pytest.approx(ONE_DEG_KM, rel=1e-9)


def test_longitude_shrinks_with_latitude():
    # La 44°N un grad de longitudine are ~80 km, nu ~111 km (eroarea tipică a distanței euclidiene).
    d = haversine_km(44.0, 29.0, 44.0, 30.0)
    assert d == pytest.approx(ONE_DEG_KM * math.cos(math.radians(44.0)), rel=1e-3)
    assert d < 0.75 * ONE_DEG_KM


def test_known_city_pair():
    # Paris – Londra: ~343.5 km pe cerc mare.
    assert haversine_km(48.8566, 2.3522, 51.5074, -0.1278) == pytest.approx(343.5, abs=1.0)


def test_symmetric_and_vectorized():
    a = (44.255, 29.53, 44.235, 29.33)
    assert haversine_km(*a) == pytest.approx(haversine_km(a[2], a[3], a[0], a[1]))
    v = haversine_km_np(np.array([a[0]]), np.array([a[1]]), np.array([a[2]]), np.array([a[3]]))
    assert v[0] == pytest.approx(haversine_km(*a))


def test_destination_roundtrip():
    lat, lon = destination(44.2, 29.4, 73.0, 12.5)
    assert haversine_km(44.2, 29.4, lat, lon) == pytest.approx(12.5, rel=1e-6)


def test_point_to_segment():
    a, b = (0.0, 0.0), (0.0, 1.0)  # pe ecuator
    assert point_to_segment_km(0.0, 0.5, a, b) == pytest.approx(0.0, abs=1e-6)
    assert point_to_segment_km(0.1, 0.5, a, b) == pytest.approx(0.1 * ONE_DEG_KM, rel=1e-3)
    # Proiecția cade în afara segmentului => distanța la capăt.
    assert point_to_segment_km(0.0, 2.0, a, b) == pytest.approx(ONE_DEG_KM, rel=1e-6)
    assert point_to_segment_km(0.0, -1.0, a, b) == pytest.approx(ONE_DEG_KM, rel=1e-6)


def test_point_to_polyline_takes_minimum():
    line = [(44.0, 29.0), (44.0, 29.5), (44.5, 29.5)]
    d = point_to_polyline_km(44.25, 29.6, line)
    assert d == pytest.approx(haversine_km(44.25, 29.6, 44.25, 29.5), rel=1e-2)
