---
paths:
  - "web/**"
---

# web/ (owner: Dev 5)

- Owns: `index.html`, `app.js` (rendering and replay), `loader.js` (transport: polls `timeline.json`),
  `style.css`. Plain JavaScript, Leaflet from CDN, no build step, no npm.
- Consumes: `out/timeline.json` (Timeline contract), `assets/infrastructure.geojson`, `assets/patrol_units.json`
  (in live mode the same two files from the folder named by `timeline.area_assets`, e.g. `assets/areas/varna/`).
- Produces: the demo screen: map, alert list, score broken down by factor, explanation lines, recommended unit,
  time slider with speed control, growing uncertainty circle for a dark vessel, visible SIMULATED labels.
- Commands: `python -m core.demo`, then `python -m http.server 8000` at the repo root and open
  http://localhost:8000/web/ (`?src=<path>` loads another timeline). Live mode: also run `python -m core.pipeline --watch`.
- Done when: the dark-vessel alert appears at its `created_at` during replay, its score grows factor by factor,
  and every simulated item is labelled.
- Hard rule: display only. No thresholds, scoring, or detection in JS. If a value is missing from the timeline,
  ask Dev 4 for it via `/contract-change`; never compute it in the page. Display constants (trail length,
  marker size) are fine.
- Allowed shortcuts: online OSM tiles (`// STUB`), simple DOM rebuild each tick.
