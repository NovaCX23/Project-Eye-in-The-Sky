# Metrici SeaGrid (seed held-out, date SIMULATE)

Generat de `python -m eval.evaluate --seed-set both --run --write-md pitch/metrics.md`.
Pragurile au fost reglate DOAR pe seed-ul de tuning.

| Set | Seed | Anomalii | Detectate | Rată detecție | Alerte | Alarme false | AF / navă normală | TTA mediu (min) |
|---|---|---|---|---|---|---|---|---|
| reporting | 1337 | 5 | 4 | 80% | 4 | 0 | 0.00 | 25.1 |

| Set | Tip anomalie | Detectate / total |
|---|---|---|
| reporting | ais_gap | 2 / 2 |
| reporting | loitering | 1 / 2 |
| reporting | position_jump | 1 / 1 |

RATAT (reporting): loitering 264593341 @ 2026-03-15T07:53:18Z
