# detect/ (Dev 2)

## Ce face
Reguli AIS naive, dar reale (prind scenariul demo), în `ais_rules.py`:

| Regulă | Logică | Prag (config.yaml) |
|---|---|---|
| `ais_gap` | `now - ultimul_mesaj > prag`; ignoră marginea acoperirii și zonele de excludere | `detect.gap.*` |
| `speed_inconsistency` | la reapariție după o pauză: distanța haversine vs. viteza raportată, **prea lent** și **prea rapid** | `detect.speed_consistency.*` |
| `loitering` | fereastră glisantă: viteză medie mică și poziții strânse, în afara zonelor de excludere | `detect.loitering.*` |
| `position_jump` | două mesaje apropiate în timp cu viteză implicită imposibilă | `detect.position_jump.*` |

`zones.py` decide ce reguli țin cont de zonele de excludere (rada de ancoraj, coridorul portului).

## Consumă
DataFrame cu mesaje `PositionMessage` cu timestamp `<= now` (garantat de `core/sources.py`; `run_all` aruncă eroare altfel),
`now`, `config.yaml`.

## Produce
`list[SensorEvent]` cu `source="ais"`, id determinist și toate numerele explicației în `metrics`.
Fără I/O, fără stare: nu știe cum sunt livrate rezultatele.

## Rulare separată
```bash
python -m pytest detect
python -m core.demo && python -m eval.evaluate      # efectul asupra metricilor
```
Din Python: `from detect.ais_rules import run_all`.

## Sarcini (prioritizate)
1. P0: reglați pragurile pe seed-ul de tuning (`/tune-thresholds`): loitering-ul aleator departe de infrastructură e ratat pe held-out.
2. P1: loitering cu rază față de centroid în loc de diagonala bbox; episod care începe la prima poziție lentă, nu la marginea ferestrei.
3. P1: viteză așteptată din istoricul înainte de pauză (nu doar media SOG).
4. P1: regulă nouă cu `/add-rule`, de exemplu rendezvous (două nave lente, apropiate).
5. P2: ignorare a navelor de serviciu (pilot, remorcher) după tip.
