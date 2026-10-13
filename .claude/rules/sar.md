---
paths:
  - "sar/**"
---

# sar/ (owner: Dev 3)

- Owns: `catalog.py` (Sentinel-1 passes over the area, Planetary Computer STAC), `scene.py` (windowed GRD read,
  GCP warp), `grid.py` (Web Mercator analysis grid), `landmask.py` (OSM coastline -> sea mask, distance to coast),
  `ships.py` (CFAR ship detection), `process.py` (CLI: targets, fixed structures, image, crops; `--watch`),
  `store.py` (where processed passes live, `load_records`).
- Consumes: the network (catalogue, images, coastline), `config.yaml` sections `sar`, `areas`, `live.area`,
  `contracts.assets` (known platforms).
- Produces: `data/raw/sar/<area>/<pass_id>/pass.json`, `overlay.png`, `chips/*.png` (never committed). No
  SensorEvent: the cross-reference with AIS is the rule `detect/sar_rules.py`, run by `core/`.
- Commands: `python -m sar.catalog`, `python -m sar.process [--latest | --pass ID | --near ISO | --watch]`,
  `python -m pytest sar`.
- Done when: the synthetic-image tests pass (one ship found, none in pure clutter, none on land) and a real pass
  processes with its targets drawn on the live page.
- Rules: network access only in `catalog.py`, `scene.py`, `landmask.py`; tests never touch the network. A pass is
  known from its `available_at` (ESA processing time), never from its acquisition time. Thresholds only in
  `config.yaml` (`sar`). Distances with haversine.
- Allowed shortcuts: uncalibrated intensity (the detector uses ratios to the local clutter), VV only (`# STUB`).
