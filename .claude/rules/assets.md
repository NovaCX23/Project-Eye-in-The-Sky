---
paths:
  - "assets/**"
---

# assets/ (shared)

- Owns: `infrastructure.geojson` (2 platforms, 1 pipeline, 1 cable, anchorage polygon, port approach corridor),
  `patrol_units.json` (3 fictional units), and per real-data area `areas/<area>/` with the same two files
  (live mode only, `config.yaml` `areas.<area>.assets`).
- Every feature carries `id`, `name`, `kind`, `protected`, `exclusion`, `approximate`. Coordinates are
  APPROXIMATE and illustrative; keep "(approx.)" in names. Patrol units are simulated.
- Consumed by: `contracts/assets.py` (loading), `detect/zones.py` (exclusion), `core/fusion.py` (proximity),
  `core/patrol.py` (ETA), `data/` (anchorage for synthetic traffic), `web/` (map layers).
- Commands: `python -m pytest` and `/demo-check` after any change: moving a feature moves the demo story.
- Done when: the team agreed the change, the demo still tells the same story, and Dev 4 merged it.
- Allowed shortcuts: approximate coordinates. Never present them as official positions.
