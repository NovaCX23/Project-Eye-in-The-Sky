"""Citește o trecere Sentinel-1 GRD peste zonă și o reeșantionează pe grila de analiză.

Produsele GRD sunt în geometrie radar, cu puncte de control (GCP). Din fiecare felie se citește doar fereastra
care acoperă zona, la nivelul de overview COG cel mai apropiat de rezoluția grilei, apoi se reproiectează cu GCP-urile
(decalate pe fereastră) pe grila Web Mercator. Feliile aceleiași treceri se pun în mozaic.
Valorile sunt numere digitale la pătrat (intensitate necalibrată): detectorul folosește doar rapoarte față de
clutter-ul local al mării, deci calibrarea absolută nu e necesară.
"""

from __future__ import annotations

import math

import numpy as np

from sar.catalog import Pass
from sar.grid import CRS, Grid

GRD_SPACING_M = 10.0       # pasul pixelilor IW GRDH
WINDOW_PAD_PX = 64
GDAL_ENV = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "GDAL_HTTP_MAX_RETRY": "5", "GDAL_HTTP_RETRY_DELAY": "2",
            "VSI_CACHE": "TRUE", "GDAL_HTTP_MULTIRANGE": "YES", "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES"}


def _area_window(src, bbox: dict):
    from rasterio.transform import GCPTransformer
    from rasterio.windows import Window

    gcps, _ = src.gcps
    tr = GCPTransformer(gcps)
    lons = np.linspace(bbox["lon_min"], bbox["lon_max"], 9)
    lats = np.linspace(bbox["lat_min"], bbox["lat_max"], 9)
    lo, la = np.meshgrid(lons, lats)
    rows, cols = tr.rowcol(lo.ravel(), la.ravel(), op=float)
    rows, cols = np.asarray(rows), np.asarray(cols)
    r0 = max(0, int(math.floor(rows.min())) - WINDOW_PAD_PX)
    r1 = min(src.height, int(math.ceil(rows.max())) + WINDOW_PAD_PX)
    c0 = max(0, int(math.floor(cols.min())) - WINDOW_PAD_PX)
    c1 = min(src.width, int(math.ceil(cols.max())) + WINDOW_PAD_PX)
    if r1 <= r0 or c1 <= c0:
        return None
    return Window(c0, r0, c1 - c0, r1 - r0)


def _read_slice(href: str, grid: Grid, bbox: dict, decim: int) -> np.ndarray | None:
    import rasterio
    from rasterio.control import GroundControlPoint
    from rasterio.crs import CRS as RioCRS
    from rasterio.warp import Resampling, reproject

    with rasterio.Env(**GDAL_ENV), rasterio.open(href) as src:
        win = _area_window(src, bbox)
        if win is None:
            return None
        out_h = max(1, int(win.height // decim))
        out_w = max(1, int(win.width // decim))
        arr = src.read(1, window=win, out_shape=(out_h, out_w), resampling=Resampling.average).astype(np.float32)
        gcps, gcp_crs = src.gcps
    sy, sx = win.height / out_h, win.width / out_w
    shifted = [GroundControlPoint(row=(g.row - win.row_off) / sy, col=(g.col - win.col_off) / sx, x=g.x, y=g.y, z=g.z)
               for g in gcps]
    dst = np.zeros(grid.shape, dtype=np.float32)
    reproject(source=arr * arr, destination=dst, gcps=shifted, src_crs=gcp_crs or RioCRS.from_epsg(4326),
              dst_transform=grid.transform, dst_crs=CRS, resampling=Resampling.bilinear,
              src_nodata=0.0, dst_nodata=0.0, SRC_METHOD="GCP_TPS")
    return dst


def load_vv(p: Pass, grid: Grid, bbox: dict) -> np.ndarray:
    """Intensitatea VV pe grilă (0 = fără date), mozaic din feliile trecerii."""
    decim = max(1, int(round(grid.ground_m / GRD_SPACING_M)))
    mosaic = np.zeros(grid.shape, dtype=np.float32)
    for it in p.items:
        if "vv" not in it.assets:
            continue
        arr = _read_slice(it.assets["vv"].href, grid, bbox, decim)
        if arr is None:
            continue
        fill = (mosaic == 0) & (arr > 0)
        mosaic[fill] = arr[fill]
    return mosaic
