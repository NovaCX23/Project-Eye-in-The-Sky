"""Detecția navelor pe intensitatea Sentinel-1: CFAR cu doi parametri peste mare, apoi gruparea în ținte.

Pentru fiecare pixel de mare, clutter-ul local = media și abaterea standard pe un inel de fond (pătratul
`background_px` minus pătratul de gardă `guard_px`, ca ținta să nu-și ridice singură fondul). Un pixel e candidat
când depășește media + k * abaterea și e cu cel puțin `min_ratio_db` peste medie. Candidații se grupează; grupurile
fără un pixel de cel puțin `seed_ratio_db` sau cu dimensiuni care nu sunt de navă se elimină. Componentele apropiate
(navă + lobi laterali) se unesc într-o singură țintă.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

from sar.grid import Grid


@dataclass
class Blob:
    row: float           # centrul ponderat cu intensitatea (pixeli de grilă)
    col: float
    lat: float
    lon: float
    length_m: float
    width_m: float
    peak_db: float       # cel mai luminos pixel față de media clutter-ului local
    pixels: int


def _box_mean(a: np.ndarray, size: int) -> np.ndarray:
    return ndimage.uniform_filter(a, size=size, mode="constant", cval=0.0)


def clutter_stats(img: np.ndarray, valid: np.ndarray, bg: int, guard: int) -> tuple[np.ndarray, np.ndarray]:
    """Media și abaterea standard locale ale `img` pe inel (pătratul bg minus pătratul de gardă), doar pixeli valizi."""
    x = np.where(valid, img, 0.0).astype(np.float32)
    v = valid.astype(np.float32)
    nb, ng = bg * bg, guard * guard
    s1 = _box_mean(x, bg) * nb - _box_mean(x, guard) * ng
    s2 = _box_mean(x * x, bg) * nb - _box_mean(x * x, guard) * ng
    n = np.maximum(_box_mean(v, bg) * nb - _box_mean(v, guard) * ng, 1.0)
    mean = s1 / n
    return mean, np.sqrt(np.maximum(s2 / n - mean * mean, 0.0))


def detect(img: np.ndarray, sea: np.ndarray, grid: Grid, cfg: dict) -> list[Blob]:
    s, c = cfg["sar"], cfg["sar"]["cfar"]
    valid = sea & (img > 0)
    mean, std = clutter_stats(img, valid, c["background_px"], c["guard_px"])
    cand = valid & (img > mean + c["k_sigma"] * std) & (img > mean * 10 ** (c["min_ratio_db"] / 10))
    labels, n = ndimage.label(cand, structure=np.ones((3, 3), bool))
    if n == 0:
        return []
    ratio = np.where(mean > 0, img / np.maximum(mean, 1e-6), 0.0)
    comps = []
    for i, sl in enumerate(ndimage.find_objects(labels), start=1):
        m = labels[sl] == i
        rr, cc = np.nonzero(m)
        comps.append((rr + sl[0].start, cc + sl[1].start, img[sl][m], float(ratio[sl][m].max())))
    # O navă se rupe des în mai multe părți luminoase: componentele cu centre apropiate sunt aceeași țintă.
    centres = np.array([[np.average(r, weights=w), np.average(cc, weights=w)] for r, cc, w, _ in comps])
    parent = list(range(len(comps)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a, b in cKDTree(centres).query_pairs(s["merge_distance_m"] / grid.ground_m):
        parent[find(a)] = find(b)
    groups: dict[int, list[int]] = {}
    for k in range(len(comps)):
        groups.setdefault(find(k), []).append(k)

    seed_ratio = 10 ** (c["seed_ratio_db"] / 10)
    out = []
    for members in groups.values():
        rr = np.concatenate([comps[k][0] for k in members])
        cc = np.concatenate([comps[k][1] for k in members])
        w = np.concatenate([comps[k][2] for k in members])
        peak = max(comps[k][3] for k in members)
        if peak < seed_ratio or len(rr) < s["min_pixels"]:
            continue
        r_c, c_c = float(np.average(rr, weights=w)), float(np.average(cc, weights=w))
        ev = np.sort(np.linalg.eigvalsh(np.cov(np.vstack([rr, cc]))))[::-1] if len(rr) >= 2 else np.zeros(2)
        # Elipsă uniformă: axa completă = 4 * sqrt(valoare proprie), plus un pixel pentru amprenta pixelului.
        length = (4 * np.sqrt(max(ev[0], 0.0)) + 1) * grid.ground_m
        width = (4 * np.sqrt(max(ev[1], 0.0)) + 1) * grid.ground_m
        if not s["min_length_m"] <= length <= s["max_length_m"]:
            continue
        lon, lat = grid.pixel_to_lonlat(r_c, c_c)
        out.append(Blob(row=r_c, col=c_c, lat=float(lat), lon=float(lon), length_m=round(float(length)),
                        width_m=round(float(width)), peak_db=round(float(10 * np.log10(peak)), 1), pixels=int(len(rr))))
    return sorted(out, key=lambda b: (-b.peak_db, b.row, b.col))
