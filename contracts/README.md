# contracts/ (comun)

**Se modifică doar prin skill-ul `contract-change`, la cerere explicită.**

## Ce face
Definește formatul datelor schimbate între module, plus utilitarele pe care toți trebuie să le folosească la fel.

| Fișier | Conținut |
|---|---|
| `models.py` | `PositionMessage`, `SensorEvent`, `Alert` (cu `ScoreFactor`, `ScorePoint`, `PatrolRecommendation`), `Timeline` |
| `schema/*.schema.json` | JSON Schema exportată (generată, nu se editează manual) |
| `examples/*.json` | câte un exemplu valid pentru fiecare model |
| `geo.py` | haversine, distanță punct–segment pe sferă, `destination` |
| `runtime.py` | căi, `load_config`, `stable_id`, timp ISO, scriere JSON atomică, consolă UTF-8 |
| `assets.py` | încărcarea infrastructurii și a unităților de patrulare |
| `testing.py` | constructori de date AIS mici pentru teste |
| `validate.py` | validarea unui fișier JSON contra schemei |

## Consumă
Nimic din alte module.

## Produce
Tipurile importate de toate celelalte module.

## Rulare separată
```bash
python -m contracts.export_schema            # regenerează schema
python -m contracts.export_schema --check    # eșuează dacă schema e depășită
python -m contracts.validate out/timeline.json --model Timeline
python -m pytest contracts
```

## Sarcini (prioritizate)
1. P0: înghețat pentru demo; schimbări doar prin `contract-change`.
2. P1: după ce organizatorii publică formatul AIS/evaluare, adaptați exportul (posibil un model nou de ieșire).
3. P2: versiune de schemă vizibilă în UI.
