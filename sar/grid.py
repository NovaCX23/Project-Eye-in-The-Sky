"""Grila de analiză: zona activă în Web Mercator (EPSG:3857), la o rezoluție fixă la sol.

În 3857, imaginea PNG stă exact pe harta Leaflet, fără reeșantionare în browser.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from affine import Affine

R_MERC = 6378137.0
CRS = "EPSG:3857"


def lonlat_to_merc(lon, lat):
    lon, lat = np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)
    return np.radians(lon) * R_MERC, np.log(np.tan(np.pi / 4 + np.radians(lat) / 2)) * R_MERC


def merc_to_lonlat(x, y):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    return np.degrees(x / R_MERC), np.degrees(2 * np.arctan(np.exp(y / R_MERC)) - np.pi / 2)


@dataclass(frozen=True)
class Grid:
    transform: Affine
    width: int
    height: int
    ground_m: float   # latura unui pixel la sol, în centrul zonei

    @property
    def shape(self) -> tuple[int, int]:
        return self.height, self.width

    def pixel_to_lonlat(self, rows, cols):
        """Centrele pixelilor (rând, coloană; pot fi fracționare) -> lon, lat."""
        rows, cols = np.asarray(rows, dtype=float), np.asarray(cols, dtype=float)
        x = self.transform.c + (cols + 0.5) * self.transform.a
        y = self.transform.f + (rows + 0.5) * self.transform.e
        return merc_to_lonlat(x, y)

    def lonlat_to_pixel(self, lon, lat):
        x, y = lonlat_to_merc(lon, lat)
        return (y - self.transform.f) / self.transform.e - 0.5, (x - self.transform.c) / self.transform.a - 0.5

    def bounds_latlon(self) -> list[list[float]]:
        """[[lat_s, lon_v], [lat_n, lon_e]] ale marginilor exterioare (limitele imaginii în Leaflet)."""
        x0, y1 = self.transform.c, self.transform.f
        x1 = x0 + self.width * self.transform.a
        y0 = y1 + self.height * self.transform.e
        (lon0, lon1), (lat0, lat1) = merc_to_lonlat([x0, x1], [y0, y1])
        return [[round(float(lat0), 5), round(float(lon0), 5)], [round(float(lat1), 5), round(float(lon1), 5)]]


def make_grid(bbox: dict, ground_m: float) -> Grid:
    lat_c = (bbox["lat_min"] + bbox["lat_max"]) / 2
    res = ground_m / math.cos(math.radians(lat_c))   # metri Mercator pe pixel pentru latura dată la sol
    (x0, x1), (y0, y1) = lonlat_to_merc([bbox["lon_min"], bbox["lon_max"]], [bbox["lat_min"], bbox["lat_max"]])
    width = int(math.ceil((x1 - x0) / res))
    height = int(math.ceil((y1 - y0) / res))
    return Grid(Affine(res, 0.0, float(x0), 0.0, -res, float(y1)), width, height, ground_m)
