# core/ (Dev 4, responsabil de integrare)

## Ce face
- `sources.py`: transportul de intrare (fișiere). `until(now)` e singura poartă: nimic cu timestamp `> now` nu trece.
- `pipeline.py`: un micro-batch = intrări `<= now` -> `detect.run_all` -> stocarea evenimentelor (id-uri deterministe,
  upsert) -> fuziune -> `Timeline`. Moduri: replay (implicit, ceas simulat pas cu pas), `--now` (un batch), `--watch`.
- `fusion.py`: grupează evenimentele AIS ale unei nave în incidente; atașează senzorii (acustic, fibră) din apropiere,
  proximitatea de infrastructură și corelarea cu alte nave suspecte; ține minte `created_at`, momentul fiecărui factor
  și istoricul scorului.
- `scoring.py`: scor aditiv cu punctele din `config.yaml`, plafonat; niveluri low/medium/high/critical.
- `explain.py`: șabloane în română, completate cu numerele detectorului. Fără LLM.
- `patrol.py`: unitatea cu ETA minim (haversine, linie dreaptă, STUB).
- `sinks.py`: transportul de ieșire (scriere atomică `out/timeline.json`).
- `demo.py`: lanțul complet pentru `make demo`.

## Consumă
`out/ais.csv`, `out/acoustic_events.json`, `out/fibre_events.json`, `assets/`, `config.yaml`
(`fusion`, `score`, `patrol`, `pipeline`, `web`).

## Produce
`out/timeline.json` (contractul `Timeline`).

## Rulare separată
```bash
python -m core.pipeline                              # replay până la finalul scenariului
python -m core.pipeline --now 2026-03-15T08:30:00Z   # un singur batch
python -m core.pipeline --watch --interval-s 3 --sim-step-min 5
python -m pytest core
```

Varianta A (server + WebSocket): se înlocuiesc doar `sources.py` și `sinks.py`; restul rămâne.

## Sarcini (prioritizate)
1. P0: păstrați `main` verde (`/verify`, `/demo-check`); integrați ramurile cu `/integrate`.
2. P1: textele factorilor (`detail`) reflectă starea de la `now`; la derularea înapoi UI-ul arată, de exemplu,
   durata finală a găurii AIS. Variantă: istoric de `detail` pe factor (necesită `/contract-change`).
3. P1: alerte deschise și de senzori fără navă AIS în zonă (o vibrație pe cablu fără nicio navă vizibilă e suspectă).
4. P1: ETA care ocolește uscatul; disponibilitatea unităților.
5. P2: persistarea stării între reporniri ale `--watch`.
