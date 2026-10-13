"""Masca de mare din linia de coastă OpenStreetMap (căile natural=coastline, prin API-ul Overpass).

Linia de coastă din zonă se nodează cu conturul zonei și se poligonizează; fața care conține `areas.<zonă>.sea_seed`
e marea. Bazinele portuare din spatele digurilor rămân în afara feței "mare", deci porturile sunt mascate ca uscat:
navele din port nu sunt nave "dark" pentru această aplicație.
Cache: data/raw/sar/<zonă>/coastline.json (răspunsul Overpass) și sea.geojson (poligonul mării).
"""

from __future__ import annotations

import time
from functools import lru_cache
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Point, box, mapping, shape
from shapely.ops import polygonize, unary_union

from contracts.geo import haversine_km
from contracts.runtime import read_json, write_json_atomic
from sar.grid import Grid, lonlat_to_merc

USER_AGENT = "SeaGrid/1.0 (maritime surveillance prototype)"
OVERPASS_TIMEOUT_S = 180
RETRY_WAIT_S = 5


def _download_coastline(cfg: dict, bbox: dict, path: Path) -> dict:
    """Interogare Overpass; serverele publice sunt des ocupate, deci se reîncearcă și se trece la următorul."""
    import requests

    m = cfg["sar"]["coastline_margin_deg"]
    q = (f'[out:json][timeout:120];way["natural"="coastline"]'
         f'({bbox["lat_min"] - m},{bbox["lon_min"] - m},{bbox["lat_max"] + m},{bbox["lon_max"] + m});out geom;')
    errors = []
    for url in cfg["sar"]["coastline_urls"]:
        for attempt in range(cfg["sar"]["coastline_attempts"]):
            try:
                r = requests.post(url, data={"data": q}, headers={"User-Agent": USER_AGENT}, timeout=OVERPASS_TIMEOUT_S)
                r.raise_for_status()
                data = r.json()
            except (requests.RequestException, ValueError) as e:
                errors.append(f"{url}: {type(e).__name__}")
                time.sleep(RETRY_WAIT_S * (attempt + 1))
                continue
            write_json_atomic(path, data)
            return data
    raise SystemExit("OpenStreetMap coastline unavailable (" + "; ".join(errors[-3:]) + "); try again later")


def sea_polygon(cfg: dict, area: str, cache_dir: Path):
    """Poligonul mării (lon, lat) al zonei; se calculează o singură dată și se ține în cache."""
    bbox, seed = cfg["areas"][area]["bbox"], cfg["areas"][area]["sea_seed"]
    sea_file = cache_dir / "sea.geojson"
    if sea_file.exists():
        cached = read_json(sea_file)
        if cached.get("bbox") == bbox:
            return shape(cached["geometry"])
    coast_file = cache_dir / "coastline.json"
    coast = read_json(coast_file) if coast_file.exists() else _download_coastline(cfg, bbox, coast_file)
    bb = box(bbox["lon_min"], bbox["lat_min"], bbox["lon_max"], bbox["lat_max"])
    lines = [LineString([(p["lon"], p["lat"]) for p in e["geometry"]])
             for e in coast["elements"] if e.get("type") == "way" and len(e.get("geometry", [])) > 1]
    noded = unary_union([ln.intersection(bb) for ln in lines] + [bb.exterior])
    faces = [f for f in polygonize(noded) if f.contains(Point(seed[1], seed[0]))]
    if not faces:
        raise SystemExit(f"No coastline face contains areas.{area}.sea_seed; check the seed point in config.yaml")
    write_json_atomic(sea_file, {"bbox": bbox, "geometry": mapping(faces[0])})
    return faces[0]


@lru_cache(maxsize=2)
def _sea_raster(grid: Grid, buffer_m: float, sea_wkb: bytes) -> np.ndarray:
    from rasterio.features import rasterize
    from scipy import ndimage
    from shapely import wkb
    from shapely.ops import transform

    sea = transform(lambda x, y, z=None: lonlat_to_merc(x, y), wkb.loads(sea_wkb))
    mask = rasterize([(sea, 1)], out_shape=grid.shape, transform=grid.transform, fill=0, dtype="uint8").astype(bool)
    n = int(round(buffer_m / grid.ground_m))
    if n > 0:
        mask = ndimage.binary_erosion(mask, structure=np.ones((3, 3), bool), iterations=n)
    return mask


def sea_mask(sea, grid: Grid, buffer_m: float) -> np.ndarray:
    """True unde pixelul e mare deschisă, la cel puțin buffer_m de coastă."""
    return _sea_raster(grid, float(buffer_m), sea.wkb)


def coast_distance_fn(sea, bbox: dict):
    """f(lat, lon) -> distanța în km până la cel mai apropiat punct al coastei reale (0 pe uscat).

    Punctul cel mai apropiat se alege pe geometrie (shapely); distanța se măsoară cu haversine.
    """
    # Fața mării e mărginită și de conturul zonei; contează doar linia de coastă reală.
    edge = box(bbox["lon_min"], bbox["lat_min"], bbox["lon_max"], bbox["lat_max"]).exterior.buffer(1e-6)
    coast = sea.boundary.difference(edge)

    def dist(lat: float, lon: float) -> float:
        p = Point(lon, lat)
        if not sea.contains(p):
            return 0.0
        if coast.is_empty:
            return float("inf")
        q = coast.interpolate(coast.project(p))
        return haversine_km(lat, lon, q.y, q.x)

    return dist
