# assets/ (comun)

**Coordonatele sunt APROXIMATIVE și ilustrative. Unitățile de patrulare sunt FICTIVE (simulate).**

## Ce conține
- `infrastructure.geojson`: două platforme de gaz, o conductă platformă–țărm, un cablu submarin, rada de ancoraj
  Constanța (poligon), coridorul de apropiere al portului (poligon). Proprietăți pe fiecare element:
  `id`, `name`, `kind`, `protected` (contează la scor), `exclusion` (zonă unde viteza mică e normală), `approximate`.
- `patrol_units.json`: trei unități cu poziție, viteză (kn) și `simulated: true`.

## Consumat de
`contracts/assets.py` (încărcare), `detect/zones.py`, `core/fusion.py`, `core/patrol.py`, `data/generate.py`, `web/`.

## Rulare separată
Nu se rulează. După orice modificare: `python -m pytest` și `python .claude/skills/demo-check/check_story.py`,
pentru că mutarea unui element mută povestea demo.

## Sarcini (prioritizate)
1. P0: nicio schimbare fără acordul echipei; Dev 4 face merge-ul.
2. P1: aliniați coordonatele cu o sursă publică, dacă organizatorii o permit; păstrați mențiunea „aprox.”.
3. P2: al doilea cablu și zona de excludere pentru pescuit.
