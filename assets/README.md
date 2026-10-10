# assets/ (shared)

**The coordinates are APPROXIMATE and illustrative. The patrol units are FICTITIOUS (simulated).**

## What it contains
- `infrastructure.geojson`: two gas platforms, a platform-to-shore pipeline, a subsea cable, the Constanța anchorage
  (polygon), the port approach corridor (polygon). Properties on each feature:
  `id`, `name`, `kind`, `protected` (counts towards the score), `exclusion` (area where low speed is normal), `approximate`.
- `patrol_units.json`: three units with position, speed (kn) and `simulated: true`.
- `simulated_submarine_contacts.json`: SIMULATED, hand-authored scenario for the replay: two submerged contacts
  (tracks with uncertainty and confidence) and two low-cost magnetometer buoys. SC-1 has a SCRIPTED critical assessment
  (hand-authored score and factors, same points and thresholds as `config.yaml`). Read only by `web/`, never by the pipeline.
- `reference_infrastructure.geojson`: DISPLAY ONLY. Real-world infrastructure from the documents in this folder
  (`Rezumat.docx` and its subfolders): Neptun Deep (Domino, Pelican Sud) and its pipeline to Tuzla, the Port of
  Constanța and its maritime security hub, the BSSC power cable, the KAFOS data cable (Mangalia landing) and the
  Romanian EEZ boundary; plus public-source infrastructure within ~500 km of Constanța (Midia/Ana, Petrom Istria
  fields, Galata/Kaliakra/Kamchia, Sakarya, TurkStream, Odesa/Golitsyn, Caucasus Cable System, Diamond Link, ITUR)
  ports (Midia, Mangalia), naval sites (Constanța base, Capu Midia range), the onshore Tuzla–Podișor pipeline,
  and approximate licence blocks (XIX Neptun Deep, XV Midia, XVIII Istria, XIII Pelican, EX-30 Trident) read from the
  maps inside the .docx files.
  Each feature has a `source` link. Approximate coordinates; `protected` and `exclusion` are false. Only `web/` reads it,
  so it never changes detection, scoring or the demo story.

## Consumed by
`contracts/assets.py` (loading), `detect/zones.py`, `core/fusion.py`, `core/patrol.py`, `data/generate.py`, `web/`.

## Running it on its own
Nothing to run. After any change: `python -m pytest` and `python .claude/skills/demo-check/check_story.py`,
because moving a feature moves the demo story.

## Tasks (prioritised)
1. P0: no change without the team's agreement; Dev 4 does the merge.
2. P1: align the coordinates with a public source, if the organisers allow it; keep the "approx." note.
3. P2: a second cable and the fishing exclusion zone.
