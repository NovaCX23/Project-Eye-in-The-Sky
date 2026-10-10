# pitch/ (Dev 5)

## Ce face
Materialul de prezentare, în română.
- `outline.md`: structura prezentării și momentele demo-ului.
- `jury_questions.md`: întrebări probabile și răspunsuri scurte.
- `metrics.md`: GENERAT de `/eval-report`, doar seed-ul held-out. Nu se editează manual.

## Consumă
`pitch/metrics.md`, capturi din demo.

## Produce
Prezentarea.

## Rulare separată
```bash
python -m eval.evaluate --seed-set both --run --write-md pitch/metrics.md
```

## Sarcini (prioritizate)
1. P0: repetiție cronometrată pe `outline.md` cu demo-ul live.
2. P0: cifrele din prezentare doar din `metrics.md` (held-out).
3. P1: răspunsuri de 20 de secunde la fiecare întrebare din `jury_questions.md`.
4. P2: un slide de arhitectură și drum spre varianta live (WebSocket).
