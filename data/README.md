# data/ (Dev 1)

## Ce face
- `loader.py`: citește AIS din CSV într-un DataFrame cu coloanele `PositionMessage`; cu `until=now` nu întoarce nimic din viitor.
  `COLUMN_ALIASES` mapează nume uzuale de coloane (STUB până aflăm formatul organizatorilor).
- `generate.py`: trafic normal sintetic cu seed fix: intrări în port, plecări, tranzit nord–sud, nave la ancoră în radă,
  zgomot GPS și pauze scurte normale de transmisie.
- `inject.py`: adaugă scenariul demo (nava care se stinge, nava care staționează), anomalii aleatoare din seed
  (gaură AIS, salt de poziție, loitering), evenimentele de fibră SIMULATE și `ground_truth.json`.
- `tracks.py`: deplasare pe waypoints, staționare, loitering (geometrie sferică).
- `scenarios/demo.yaml`: geografia traficului și povestea demo (poziții, minute, nume de nave fictive).

## Consumă
`config.yaml` (`scenario`, `generator`, `injector`), `assets/infrastructure.geojson`, `contracts`.

## Produce
- `out/ais_clean.csv`: trafic normal
- `out/ais.csv`: trafic + anomalii (rânduri `PositionMessage`, `simulated=true`)
- `out/ground_truth.json`: lista anomaliilor (tip, MMSI, start, end, poziție, `expected_event_types`) + MMSI-urile normale
- `out/fibre_events.json`: listă de `SensorEvent` cu `source="fibre"`, `simulated=true`

## Rulare separată
```bash
python -m data.generate --seed 42 --out-dir out
python -m data.inject --seed 42 --out-dir out
python -m pytest data
```

## Sarcini (prioritizate)
1. P0: adaptor pentru formatul AIS real al organizatorilor în `loader.py` (după răspunsul lor).
2. P0: păstrați scenariul demo stabil; verificați cu `/demo-check` după fiecare schimbare.
3. P1: mai mult realism normal: pescadoare lente în afara zonelor de excludere, pilot la intrarea în port.
   Acestea testează alarmele false.
4. P1: tipuri noi de anomalii pentru evaluare (`/add-anomaly`): spoofing de identitate, rendezvous între două nave.
5. P2: mai multe seed-uri de raportare, medie pe seed-uri în `eval/`.
