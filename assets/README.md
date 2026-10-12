# assets/ (shared)

**The coordinates are APPROXIMATE and illustrative. The patrol units are FICTITIOUS (simulated).**

## What it contains
- `infrastructure.geojson`: two gas platforms, a platform-to-shore pipeline, a subsea cable, the Constanța anchorage
  (polygon), the port approach corridor (polygon). Properties on each feature:
  `id`, `name`, `kind`, `protected` (counts towards the score), `exclusion` (area where low speed is normal), `approximate`.
- `patrol_units.json`: three FICTITIOUS units at real bases (Constanța naval base, Midia, Mangalia). Per unit: `lat`/`lon`
  (home base), `speed_kn` (response speed), `patrol_speed_kn`, `route` (closed loop at sea, `[lat, lon]` points), a
  fictitious `mmsi` (must not collide with AIS traffic) and `simulated: true`. `core/patrol.py` moves them along the route.
- `simulated_submarine_contacts.json`: SIMULATED, hand-authored scenario for the replay: two submerged contacts
  (tracks with uncertainty and confidence) and two low-cost magnetometer buoys. SC-1 has a SCRIPTED critical assessment
  (hand-authored score and factors, same points and thresholds as `config.yaml`). Read only by `web/`, never by the pipeline.
- `areas/<area>/`: the scored layer and patrol units of a real-data area, used only by live mode
  (`config.yaml` `areas.<area>.assets`). `areas/varna/infrastructure.geojson`: the Galata platform and the
  Kaliakra/Kamchia wellheads, the Galata pipeline, the KAFOS Varna branch and the Caucasus Cable System landing at
  Balchik (protected), plus the Varna Bay and Balchik harbour approaches (exclusion); same properties as above, each
  with a `source` link. `areas/varna/patrol_units.json`: three FICTITIOUS units at Varna naval base and Balchik.
  The demo scenario never reads `areas/`.
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
2. P1: decide whether the scored layer (`infrastructure.geojson`) should move to real positions from
   `reference_infrastructure.geojson` (e.g. the Ana platform, the Neptun Deep pipeline, KAFOS). This moves the demo story:
   `data/scenarios/demo.yaml` and `/demo-check` must follow, so it is a team decision.
3. P1: a coastline / land polygon, needed by `core/` for an ETA that routes around land.
4. P2: a second cable and the fishing exclusion zone.

## Done
- ✔ Patrol units at real bases with patrol routes (used by `core/` for moving units).
- ✔ `reference_infrastructure.geojson`: real Black Sea infrastructure from the documents in this folder and public
  sources, each feature with a `source` link; display only, shown as a toggleable layer in `web/`.
