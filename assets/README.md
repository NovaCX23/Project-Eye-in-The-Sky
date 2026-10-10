# assets/ (shared)

**The coordinates are APPROXIMATE and illustrative. The patrol units are FICTITIOUS (simulated).**

## What it contains
- `infrastructure.geojson`: two gas platforms, a platform-to-shore pipeline, a subsea cable, the Constanța anchorage
  (polygon), the port approach corridor (polygon). Properties on each feature:
  `id`, `name`, `kind`, `protected` (counts towards the score), `exclusion` (area where low speed is normal), `approximate`.
- `patrol_units.json`: three units with position, speed (kn) and `simulated: true`.

## Consumed by
`contracts/assets.py` (loading), `detect/zones.py`, `core/fusion.py`, `core/patrol.py`, `data/generate.py`, `web/`.

## Running it on its own
Nothing to run. After any change: `python -m pytest` and `python .claude/skills/demo-check/check_story.py`,
because moving a feature moves the demo story.

## Tasks (prioritised)
1. P0: no change without the team's agreement; Dev 4 does the merge.
2. P1: align the coordinates with a public source, if the organisers allow it; keep the "approx." note.
3. P2: a second cable and the fishing exclusion zone.
