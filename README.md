# SeaGrid

Detecția activităților suspecte în jurul infrastructurii maritime românești din Marea Neagră:
platforme de gaz, conducte, cabluri submarine, apropierea de portul Constanța.

**Toate datele sunt sintetice (SIMULATE), iar coordonatele infrastructurii sunt aproximative.**

Scenariul demo: un cargo cu destinația Constanța își oprește AIS-ul 2 ore lângă o platformă și un cablu.
La reapariție, poziția nu se potrivește cu viteza raportată. În paralel, o a doua navă staționează la viteză mică
în aceeași zonă. SeaGrid corelează traseele cu harta infrastructurii, cu un hidrofon și cu senzorul de fibră,
apoi ridică o alertă cu scor de risc, explicație și unitatea de patrulare recomandată (cu ETA).

## Pornire rapidă

```bash
python -m venv .venv
# Windows (PowerShell):  .\.venv\Scripts\Activate.ps1      Linux/macOS:  source .venv/bin/activate
python -m devtools.bootstrap        # = make setup: dependențe + hook-uri git
python -m core.demo                 # = make demo: scrie out/timeline.json
python -m http.server 8000          # = make serve
# deschideți http://localhost:8000/web/ și apăsați ▶
```

Python 3.11 sau mai nou. Versiunile din `requirements.txt` sunt fixate și au wheel-uri pentru 3.11–3.14.

## Comenzi

Fiecare țintă `make` e un înveliș subțire peste o comandă `python -m`. Fără `make` (Windows), rulați coloana din dreapta.

| make | comandă directă | ce face |
|---|---|---|
| `make setup` | `python -m devtools.bootstrap` | instalează dependențele, activează `.githooks/` |
| `make test` | `python -m pytest` | toate testele |
| `make demo` | `python -m core.demo` | trafic (seed 42) + scenariu + acustic + pipeline -> `out/timeline.json` |
| `make eval` | `python -m eval.evaluate --seed-set tuning --run` | tabelul de metrici pe seed-ul de tuning |
| `make eval-report` | `python -m eval.evaluate --seed-set both --run --write-md pitch/metrics.md` | tuning + held-out |
| `make watch` | `python -m core.pipeline --watch` | micro-batch-uri pe ceas simulat (după `make demo`) |
| `make serve` | `python -m http.server 8000` | server static; pagina e la `/web/` |
| `make schema` | `python -m contracts.export_schema` | regenerează JSON Schema |
| `make validate` | `python -m contracts.validate out/timeline.json --model Timeline` | validează ieșirea |
| `make data` | `python -m data.generate` apoi `python -m data.inject` | doar datele |
| `make acoustic` | `python -m acoustic.analyze` | doar evenimentele acustice |
| `make pipeline` | `python -m core.pipeline` | doar pipeline-ul (replay) |

Mod live: într-un terminal `python -m core.pipeline --watch`, în altul `python -m http.server 8000`, apoi bifați „Live” în pagină.

## Arhitectură (varianta B, micro-batch)

```
data/ ──> out/ais.csv, out/fibre_events.json, out/ground_truth.json
acoustic/ ──> out/acoustic_events.json
core/sources.py (doar date <= now) -> detect/ (reguli) -> core/fusion (scor, explicații, patrulă) -> core/sinks.py -> out/timeline.json
web/ citește out/timeline.json și îl redă cu slider și control de viteză
```

Fără server, bază de date, Docker sau cloud. Trecerea la varianta A (server + WebSocket) schimbă doar
`core/sources.py`, `core/sinks.py` și `web/loader.js`.

## Structură și proprietari

| Director | Proprietar | Rol |
|---|---|---|
| `contracts/` | comun (doar prin skill-ul `contract-change`) | modele, JSON Schema, exemple, haversine |
| `assets/` | comun | infrastructură (aprox.), unități de patrulare (simulate) |
| `data/`, `eval/` | Dev 1 | date AIS, generator, injector, ground truth, evaluare |
| `detect/` | Dev 2 | reguli AIS, zone de excludere |
| `acoustic/` | Dev 3 | detector de joasă frecvență |
| `core/` | Dev 4 (integrare) | pipeline, fuziune, scor, explicații, recomandare, `--watch` |
| `web/`, `pitch/` | Dev 5 | interfața, prezentarea |

Ramuri: `main` (rulează mereu demo-ul) plus `role/data-eval`, `role/detect`, `role/acoustic`, `role/core`, `role/web-pitch`.

Reguli complete de lucru și de design: [AGENTS.md](AGENTS.md). Fiecare director are propriul `README.md` cu sarcini.

## Autorat

Commit-urile sunt făcute doar de oameni, cu identitatea git configurată pe mașină. Hook-ul `.githooks/commit-msg`
respinge mesajele care atribuie autorat unui instrument AI (`Co-Authored-By`, „Generated with” etc.).
`make setup` îl activează prin `git config core.hooksPath .githooks`.
