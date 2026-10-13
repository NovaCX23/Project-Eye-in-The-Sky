"""Procesează trecerile Sentinel-1 peste zona activă: citire, detecția navelor, structuri fixe, imagine și decupaje.

  python -m sar.process --latest                 # cea mai nouă trecere publicată
  python -m sar.process --pass S1C_20261007T155945_9781
  python -m sar.process --near 2026-10-12T16:08:00Z
  python -m sar.process --watch                  # rămâne pornit: procesează fiecare trecere nouă când e publicată

Rezultatele stau în data/raw/sar/<zonă>/<pass_id>/ (vezi sar/store.py); a doua rulare e instantanee.
Prima rulare pe o zonă descarcă și linia de coastă OpenStreetMap (o singură dată).
Datele radar: ESA Copernicus Sentinel-1 IW GRD, prin Microsoft Planetary Computer (fără cont).
"""

from __future__ import annotations

import argparse
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from contracts.assets import ASSETS_DIR, area_infrastructure, load_infrastructure
from contracts.geo import haversine_km
from contracts.runtime import active_area, iso, load_config, parse_time, read_json, utf8_stdout, write_json_atomic
from sar import catalog
from sar.grid import Grid, make_grid
from sar.landmask import coast_distance_fn, sea_mask, sea_polygon
from sar.scene import load_vv
from sar.ships import detect
from sar.store import PASS_FILE, RECORD_VERSION, area_dir

STRETCH_PCT = (25.0, 99.9)   # marea întunecată, navele luminoase
LAND_ALPHA = 70              # uscatul se desenează estompat: contează marea
SOURCE_URL = "https://planetarycomputer.microsoft.com/dataset/sentinel-1-grd#{item}"
SEARCH_HOURS = 6             # --near: fereastra de căutare în jurul momentului dat


def _stretch(img: np.ndarray, sea: np.ndarray) -> np.ndarray:
    valid = img > 0
    db = 10 * np.log10(np.maximum(img, 1.0))
    sample = db[valid & sea] if (valid & sea).any() else db[valid]
    lo, hi = np.percentile(sample, STRETCH_PCT) if sample.size else (0.0, 1.0)
    g = np.clip((db - lo) / max(hi - lo, 1e-6) * 255, 0, 255).astype(np.uint8)
    g[~valid] = 0
    return g


def _render_overlay(g: np.ndarray, valid: np.ndarray, sea: np.ndarray, path: Path, max_side: int) -> None:
    from PIL import Image

    f = max(1, int(np.ceil(max(g.shape) / max_side)))
    h, w = (g.shape[0] // f) * f, (g.shape[1] // f) * f
    gs = g[:h, :w].reshape(h // f, f, w // f, f).max(axis=(1, 3))   # maximul păstrează vizibile navele mici
    vs = valid[:h, :w].reshape(h // f, f, w // f, f).any(axis=(1, 3))
    ss = sea[:h, :w].reshape(h // f, f, w // f, f).any(axis=(1, 3))
    alpha = np.where(vs, np.where(ss, 255, LAND_ALPHA), 0).astype(np.uint8)
    Image.fromarray(np.dstack([gs, alpha])).save(path, optimize=True)   # gri + alfa ("LA"): jumătate din RGBA


def _footprint(valid: np.ndarray, grid: Grid) -> list[list[float]]:
    """Conturul convex al pixelilor cu date peste mare, ca [[lat, lon], ...]."""
    from shapely.geometry import MultiPoint

    step = max(1, max(valid.shape) // 400)
    rr, cc = np.nonzero(valid[::step, ::step])
    if rr.size < 3:
        return []
    lon, lat = grid.pixel_to_lonlat(rr * step, cc * step)
    hull = MultiPoint(list(zip(lon, lat))).convex_hull.simplify(0.005)
    if hull.geom_type != "Polygon":
        return []
    return [[round(y, 4), round(x, 4)] for x, y in hull.exterior.coords]


def _platforms(cfg: dict) -> list[tuple[float, float, str]]:
    """Platformele cunoscute (stratul punctat al zonei și cel de referință): ecouri fixe, nu nave."""
    feats = list(area_infrastructure(cfg)) + list(load_infrastructure(ASSETS_DIR / "reference_infrastructure.geojson"))
    return [(f.coords[0], f.coords[1], f.name) for f in feats if f.kind == "platform" and f.geom_type == "Point"]


def run_pass(p: catalog.Pass, cfg: dict, render: bool = True, verbose: bool = True) -> dict:
    """Procesează (sau citește din cache) o trecere. Întoarce înregistrarea (pass.json)."""
    area = active_area(cfg)
    d = area_dir(cfg) / p.pass_id
    meta = d / PASS_FILE
    if meta.exists():
        rec = read_json(meta)
        if rec.get("version") == RECORD_VERSION and (rec.get("rendered") or not render):
            return rec
    if verbose:
        print(f"[sar] {p.pass_id}: reading {len(p.items)} slice(s) over {area} ...", flush=True)
    s = cfg["sar"]
    bbox = cfg["areas"][area]["bbox"]
    grid = make_grid(bbox, s["pixel_m"])
    vv = load_vv(p, grid, bbox)
    sea_poly = sea_polygon(cfg, area, area_dir(cfg))
    sea = sea_mask(sea_poly, grid, s["land_buffer_m"])
    blobs = detect(vv, sea, grid, cfg)
    valid = vv > 0
    coast_km = coast_distance_fn(sea_poly, bbox)
    if verbose:
        print(f"[sar] {p.pass_id}: {len(blobs)} radar targets on the sea", flush=True)
    d.mkdir(parents=True, exist_ok=True)
    rec = {
        "version": RECORD_VERSION,
        "pass_id": p.pass_id,
        "area": area,
        "platform": p.platform,
        "orbit_state": p.orbit_state,
        "relative_orbit": p.relative_orbit,
        "acquired_at": iso(p.acquired_at),
        "available_at": iso(p.available_at),
        "area_coverage": p.area_coverage,
        "pixel_m": grid.ground_m,
        "items": [it.id for it in p.items],
        "source_url": SOURCE_URL.format(item=p.items[0].id),
        "footprint": _footprint(valid & sea, grid),
        "targets": [dict(asdict(b), target_id=f"{p.pass_id}-{k:03d}", lat=round(b.lat, 5), lon=round(b.lon, 5),
                         coast_km=round(coast_km(b.lat, b.lon), 2), fixed=None)
                    for k, b in enumerate(blobs)],
        "rendered": False,
    }
    for t in rec["targets"]:
        del t["row"], t["col"]
    if render:
        from PIL import Image

        g = _stretch(vv, sea)
        _render_overlay(g, valid, sea, d / "overlay.png", s["image_max_side_px"])
        rec["image"] = "overlay.png"
        rec["image_bounds"] = grid.bounds_latlon()
        (d / "chips").mkdir(exist_ok=True)
        half = s["chip_px"] // 2
        for k, (b, t) in enumerate(zip(blobs, rec["targets"])):
            r, c = int(round(b.row)), int(round(b.col))
            Image.fromarray(g[max(0, r - half):r + half, max(0, c - half):c + half]).save(d / "chips" / f"{k:03d}.png")
            t["chip"] = f"chips/{k:03d}.png"
        rec["targets"] = _flag_fixed(rec, cfg, verbose)
        rec["rendered"] = True
    write_json_atomic(meta, rec)
    return rec


def _flag_fixed(rec: dict, cfg: dict, verbose: bool) -> list[dict]:
    """Marchează structurile fixe: lângă o platformă cunoscută, sau în același loc pe mai multe treceri anterioare."""
    fc = cfg["sar"]["fixed"]
    acquired = parse_time(rec["acquired_at"])
    try:
        earlier = catalog.find_passes(cfg, acquired - timedelta(days=fc["lookback_days"]), acquired - timedelta(hours=1))
    except Exception as e:   # catalog indisponibil: rămân doar platformele cunoscute
        print(f"[sar] catalogue unavailable for the fixed-structure check: {type(e).__name__}: {e}")
        earlier = []
    others = []
    for p in earlier[-fc["passes"]:]:
        try:
            others.append(run_pass(p, cfg, render=False, verbose=verbose)["targets"])
        except Exception as e:   # o trecere anterioară eșuată doar slăbește masca de structuri fixe
            print(f"[sar] skipping {p.pass_id} for the fixed-structure check: {type(e).__name__}: {e}")
    plats = _platforms(cfg)
    out = []
    for t in rec["targets"]:
        reason = None
        for lat, lon, name in plats:
            if haversine_km(t["lat"], t["lon"], lat, lon) * 1000 <= fc["platform_radius_m"]:
                reason = f"known platform: {name}"
                break
        if reason is None and others:
            hits = sum(any(haversine_km(t["lat"], t["lon"], o["lat"], o["lon"]) * 1000 <= fc["radius_m"] for o in prev)
                       for prev in others)
            if hits >= fc["min_hits"]:
                reason = f"recurring: same spot on {hits} of {len(others)} earlier passes"
        out.append(dict(t, fixed=reason))
    return out


def select_pass(cfg: dict, pass_id: str | None = None, near: datetime | None = None) -> catalog.Pass:
    now = datetime.now(timezone.utc)
    if pass_id:
        t = datetime.strptime(pass_id.split("_")[1], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
        found = [p for p in catalog.find_passes(cfg, t - timedelta(minutes=30), t + timedelta(minutes=30))
                 if p.pass_id == pass_id]
    elif near:
        found = catalog.find_passes(cfg, near - timedelta(hours=SEARCH_HOURS), near + timedelta(hours=SEARCH_HOURS))
        found.sort(key=lambda p: abs((p.acquired_at - near).total_seconds()))
    else:
        found = catalog.find_passes(cfg, now - timedelta(days=catalog.DEFAULT_DAYS), now)[::-1]
    if not found:
        raise SystemExit("No Sentinel-1 pass found for that request.")
    return found[0]


def _summary(rec: dict) -> str:
    ts = rec["targets"]
    fixed = sum(1 for t in ts if t.get("fixed"))
    return (f"[sar] {rec['pass_id']} acquired {rec['acquired_at']}, published {rec['available_at']}: "
            f"{len(ts)} targets, {fixed} fixed structures")


def watch(cfg: dict) -> None:
    """Rămâne pornit: la fiecare sar.watch_interval_min întreabă catalogul și procesează trecerile noi."""
    interval = cfg["sar"]["watch_interval_min"] * 60
    print(f"[sar] watching for new Sentinel-1 passes over {active_area(cfg)} every "
          f"{cfg['sar']['watch_interval_min']} min (Ctrl+C to stop)", flush=True)
    while True:
        now = datetime.now(timezone.utc)
        try:
            for p in catalog.find_passes(cfg, now - timedelta(days=1), now):
                if not (area_dir(cfg) / p.pass_id / PASS_FILE).exists() or not read_json(
                        area_dir(cfg) / p.pass_id / PASS_FILE).get("rendered"):
                    print(_summary(run_pass(p, cfg)), flush=True)
        except Exception as e:   # rețea căzută: se reîncearcă la următorul ciclu
            print(f"[sar] {iso(now)}: {type(e).__name__}: {e}; retrying in {cfg['sar']['watch_interval_min']} min",
                  flush=True)
        time.sleep(interval)


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--pass", dest="pass_id")
    g.add_argument("--near", help="the pass closest to this time (ISO 8601)")
    g.add_argument("--latest", action="store_true", help="the newest published pass (default)")
    g.add_argument("--watch", action="store_true", help="keep running and process every new pass")
    args = ap.parse_args(argv)
    cfg = load_config()
    if args.watch:
        try:
            watch(cfg)
        except KeyboardInterrupt:
            print("Stopped.")
        return 0
    rec = run_pass(select_pass(cfg, args.pass_id, parse_time(args.near) if args.near else None), cfg)
    print(f"{_summary(rec)} -> {area_dir(cfg) / rec['pass_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
