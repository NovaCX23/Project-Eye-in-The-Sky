# eval/ (Dev 1)

## Ce face
`evaluate.py` compară alertele din `timeline.json` cu `ground_truth.json` și tipărește:
rata de detecție, numărul de alarme false, alarme false raportate la navele normale, timpul mediu până la alertă
(`created_at` minus începutul anomaliei), defalcarea pe tipuri și lista anomaliilor ratate.

Potrivire (STUB): o alertă detectează o anomalie dacă are același MMSI și a fost creată în
`[start, end + eval.match_grace_min]`. Orice altă alertă e alarmă falsă.

## Consumă
`out/ground_truth.json`, `out/timeline.json` (sau `out/eval/<set>/...`), `config.yaml` (`eval`, `scenario.seeds`).

## Produce
Tabel markdown la consolă; cu `--write-md`, tabelul seed-ului held-out în `pitch/metrics.md`.

## Rulare separată
```bash
python -m eval.evaluate                                             # evaluează out/ (după make demo)
python -m eval.evaluate --seed-set tuning --run                     # = make eval
python -m eval.evaluate --seed-set both --run --write-md pitch/metrics.md   # = make eval-report
python -m pytest eval
```

Seed-ul `reporting` (1337) e held-out: nu se reglează nimic pe el.

## Sarcini (prioritizate)
1. P0: aflați cum evaluează organizatorii (format, potrivire, ce înseamnă „alarmă falsă”) și aliniați `evaluate.py`.
2. P1: alarme false pe oră de trafic, pe lângă cele pe navă.
3. P1: medie pe mai multe seed-uri de raportare.
4. P2: export CSV al potrivirilor pentru depanare.
