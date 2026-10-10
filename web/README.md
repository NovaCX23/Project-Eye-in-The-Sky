# web/ (Dev 5)

## What it does
A static page (Leaflet from a CDN, plain JavaScript, no build) that replays `out/timeline.json`:
- the map with the demo infrastructure (approx.), a toggleable reference layer of real infrastructure (approx., not scored), the patrol units (simulated) and the moving vessels;
- patrol units: their bases, their moving tracks (`ship_type: "patrol"` in the timeline), and a dashed line with the ETA
  from a dispatched unit to its target ("on scene" once it arrives); mission and ETA come from the alert history;
- a vessel with AIS off: grey marker and an uncertainty circle that grows over time (the rate comes from the pipeline, `metrics.uncertainty_km_per_h`);
- the alert list at the cursor time, the score broken down by factor, the explanation lines, the recommended unit with ETA;
- time slider, play/pause, replay speed, "Live" mode for `--watch`;
- "SIMULATED" labels on everything simulated and the "SIMULATED DATA" badge.

**Display only.** No rule, threshold or score is computed here.

## Files
`index.html`, `app.js` (rendering and replay), `loader.js` (transport: periodically reads `timeline.json`; the only file
to change for variant A with WebSocket), `style.css`.

## Consumes
`../out/timeline.json` (or `?src=<path>`), `../assets/infrastructure.geojson`, `../assets/reference_infrastructure.geojson`, `../assets/patrol_units.json`.

## Running it on its own
```bash
python -m core.demo            # once, so out/timeline.json exists
python -m http.server 8000     # from the repo root
# http://localhost:8000/web/
```
Live: in another terminal run `python -m core.pipeline --watch`, then tick "Live".
The map tiles (OpenStreetMap) need internet. Without a network, the SeaGrid layers show on a blank background.

## Tasks (prioritised)
1. P0: demo rehearsal: the story must read clearly at 300× (alert, rising score, recommended unit).
2. P1: a timeline with markers for the alert moments under the slider.
3. P1: highlight the infrastructure nearest to the selected alert.
4. P2: an offline map background (an image of the coast) for a room without internet.

## Done
- ✔ Critical alerts pulse on the map.
- ✔ Toggleable reference layer of real infrastructure (approx., not scored).
- ✔ Acoustic panel: hydrophone and DAS fibre sensors shown separately, signatures, spectrograms and acoustic history.
- ✔ Patrol units drawn on the map: bases, moving tracks, dispatch line with ETA, "on scene".
