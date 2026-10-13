"""Detecția navelor pe o imagine radar sintetică: clutter de mare cu speckle plus o țintă luminoasă."""

from __future__ import annotations

import numpy as np

from contracts.geo import haversine_km
from sar.grid import make_grid
from sar.ships import detect

BBOX = {"lat_min": 44.0, "lat_max": 44.1, "lon_min": 29.0, "lon_max": 29.14}


def _sea(seed: int = 7):
    grid = make_grid(BBOX, 20)
    rng = np.random.default_rng(seed)
    img = rng.exponential(1.0, size=grid.shape).astype(np.float32)   # speckle: intensitate exponențială
    return grid, img, np.ones(grid.shape, dtype=bool)


def test_no_ship_in_pure_sea_clutter(cfg):
    grid, img, sea = _sea()
    assert detect(img, sea, grid, cfg) == []


def test_finds_one_ship_and_its_size(cfg):
    grid, img, sea = _sea()
    r, c = 250, 280
    img[r - 1:r + 2, c - 3:c + 4] += 200.0          # ~140 m x 60 m de ecou puternic
    blobs = detect(img, sea, grid, cfg)
    assert len(blobs) == 1
    b = blobs[0]
    lon, lat = grid.pixel_to_lonlat(r, c)
    assert haversine_km(b.lat, b.lon, float(lat), float(lon)) < 0.05
    assert cfg["sar"]["min_length_m"] <= b.length_m <= 200 and b.peak_db > cfg["sar"]["cfar"]["seed_ratio_db"]


def test_land_is_never_a_target(cfg):
    grid, img, sea = _sea()
    img[100:103, 100:107] += 200.0
    sea[90:115, 90:120] = False                      # aceeași țintă, dar pe uscat / în port
    assert detect(img, sea, grid, cfg) == []


def test_grid_round_trip():
    grid = make_grid(BBOX, 20)
    rows, cols = grid.lonlat_to_pixel(29.07, 44.05)
    lon, lat = grid.pixel_to_lonlat(rows, cols)
    assert abs(float(lon) - 29.07) < 1e-9 and abs(float(lat) - 44.05) < 1e-9
    (s, w), (n, e) = grid.bounds_latlon()
    assert s <= 44.0 and n >= 44.1 and w <= 29.0 and e >= 29.14
