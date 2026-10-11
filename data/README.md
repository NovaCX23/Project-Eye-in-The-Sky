# data/ (Dev 1)

## What it does
- `loader.py`: reads AIS from CSV into a DataFrame with the `PositionMessage` columns; with `until=now` it returns nothing from the future.
  `COLUMN_ALIASES` maps common column names (STUB until we know the organisers' format).
- `generate.py`: synthetic normal traffic with a fixed seed: port arrivals, departures, north–south transit, vessels at anchor,
  trawlers working the shelf north of Constanța (parallel tows at trawling speed), a pilot boat shuttling between the berth
  and the approach entry, GPS noise and short normal transmission dropouts. The slow traffic uses its own RNG stream, so the
  other vessels stay identical for a given seed.
- Random anomalies are placed only on the ship types in `injector.random_ship_types` (cargo, tanker).
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
3. P2: more reporting seeds, average across seeds in `eval/`.

## Done
- ✔ Random anomalies now include rendezvous (two vessels) and identity spoofing (cloned transponder), each with ground truth; both detected on the tuning and reporting seeds, 0 false alarms.
- ✔ Slow normal traffic: 3 trawlers outside the exclusion zones and a pilot boat in the port area. No events on them (tuning and reporting seeds, plus 8 extra seeds checked); 0 false alarms.
