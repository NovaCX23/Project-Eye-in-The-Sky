# data/ (Dev 1)

## What it does
- `loader.py`: reads AIS from CSV into a DataFrame with the `PositionMessage` columns; with `until=now` it returns nothing from the future.
  `COLUMN_ALIASES` maps common column names (STUB until we know the organisers' format).
- `generate.py`: synthetic normal traffic with a fixed seed: port arrivals, departures, north–south transit, vessels at anchor,
  GPS noise and short normal transmission dropouts.
- `inject.py`: adds the demo scenario (the vessel that goes dark, the vessel that loiters), random anomalies from the seed
  (AIS gap, position jump, loitering), the SIMULATED fibre events and `ground_truth.json`.
- `tracks.py`: movement along waypoints, standing still, loitering (spherical geometry).
- `scenarios/demo.yaml`: traffic geography and the demo story (positions, minutes, fictitious vessel names).

## Consumes
`config.yaml` (`scenario`, `generator`, `injector`), `assets/infrastructure.geojson`, `contracts`.

## Produces
- `out/ais_clean.csv`: normal traffic
- `out/ais.csv`: traffic + anomalies (`PositionMessage` rows, `simulated=true`)
- `out/ground_truth.json`: list of anomalies (type, MMSI, start, end, position, `expected_event_types`) + the normal MMSIs
- `out/fibre_events.json`: list of `SensorEvent` with `source="fibre"`, `simulated=true`

## Running it on its own
```bash
python -m data.generate --seed 42 --out-dir out
python -m data.inject --seed 42 --out-dir out
python -m pytest data
```

## Tasks (prioritised)
1. P0: adapter for the organisers' real AIS format in `loader.py` (once they answer).
2. P0: keep the demo scenario stable; check with `/demo-check` after every change.
3. P1: more realistic normal traffic: slow fishing boats outside the exclusion zones, a pilot boat at the port entrance.
   These test false alarms.
4. P1: new anomaly types for evaluation (`/add-anomaly`): identity spoofing, rendezvous between two vessels.
5. P2: more reporting seeds, average across seeds in `eval/`.
