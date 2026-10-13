# sar/ (Dev 3)

## What it does
Finds ships on **real Sentinel-1 radar images** of the active live area. Radar sees steel whether or not a ship
transmits AIS, so a ship-sized return with no AIS vessel next to it is a vessel that is not transmitting.

1. `catalog.py` asks the Microsoft Planetary Computer STAC catalogue (no account needed) which Sentinel-1 IW GRD
   passes cover the area (`areas.<area>.bbox`), and when ESA published each one.
2. `scene.py` reads only the window over the area from each image slice (cloud-optimised GeoTIFF over HTTP),
   warps it with the image's ground control points onto a 20 m Web Mercator grid (`grid.py`).
3. `landmask.py` builds the sea mask from the OpenStreetMap coastline (Overpass API, downloaded once per area).
   Harbour basins fall outside the sea face, so ships in port are never "dark".
4. `ships.py` finds ships with a two-parameter CFAR detector: a pixel is a candidate when it is
   `k_sigma` standard deviations and `min_ratio_db` above the local sea clutter (ring around a guard window);
   candidates are grouped into targets with a ship-like size.
5. `process.py` writes the targets, the image (PNG) and one crop per target, and flags **fixed structures**:
   a return near a known platform, or seen at the same spot on several earlier passes (buoys, wrecks).

The cross-reference with AIS is **not** here: it is a detection rule, `detect/sar_rules.py`, run by `core/` when the
pass is published.

## Consumes
The Planetary Computer catalogue and Sentinel-1 GRD images, the OpenStreetMap coastline, `config.yaml` (`sar`,
`areas`, `live.area`), the area's platforms (`contracts.assets`).

## Produces
`data/raw/sar/<area>/` (never committed): `coastline.json`, `sea.geojson`, and per pass `<pass_id>/pass.json`
(times, footprint, targets with size, brightness, distance to the coast and fixed-structure reason),
`overlay.png` and `chips/NNN.png`. `sar/store.py` reads them back for `core/`.

## Running it on its own
```bash
python -m sar.catalog                          # passes of the last 14 days, with the share of the area each covers
python -m sar.catalog --upcoming 3             # predicted passes (12-day repeat cycle per satellite)
python -m sar.process --latest                 # process the newest pass (about 1-2 min the first time)
python -m sar.process --near 2026-10-12T16:08:00Z
python -m sar.process --watch                  # keep running next to the AIS recorder and core.live
python -m pytest sar detect/tests/test_sar_rules.py
```
`SEAGRID_AREA=constanta` (or `live.area` in `config.yaml`) picks the area. Each area keeps its own cache.

## Limits
- Radar sees steel and size, not identity. Boats under about 20 m, or made of wood or fibreglass, can be missed;
  sidelobes make the apparent length longer than the hull.
- Each spot is imaged a few times a week, so the radar is a periodic check, not continuous surveillance. The
  cross-reference needs AIS recorded while the satellite passed.
- Strong wind raises the sea clutter; very bright ships can produce ghost targets (azimuth ambiguities).
- Sentinel-1 data: Copernicus programme (ESA), free and open; the page credits it on the map.

## Tasks (prioritised)
1. P2: use the VH polarisation as well (better ship/sea contrast in rough sea).
2. P2: azimuth-ambiguity filter for very bright ships.

## Done
- ✔ Catalogue, windowed image reading, OSM sea mask, CFAR ship detection, fixed-structure flags, image and crops,
  `--watch` for live mode.
