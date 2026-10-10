---
paths:
  - "acoustic/**"
---

# acoustic/ (owner: Dev 3)

- Owns: `analyze.py` (low-frequency energy ratio per frame -> `acoustic_lowfreq` events), `make_test_clips.py`
  (two synthetic clips), `clips/manifest.json` (hydrophone id, position, offset from scenario start).
- Consumes: `.wav` clips listed in the manifest, `config.yaml` sections `acoustic` and `scenario.start`.
- Produces: `out/acoustic_events.json` (list of SensorEvent, `source="acoustic"`, `simulated: true` for synthetic
  clips). Results are precomputed once; the pipeline filters them by `now`.
- Commands: `python -m acoustic.make_test_clips`, `python -m acoustic.analyze`, `python -m pytest acoustic`.
- Done when: the tone clip yields an event, the noise clip yields none, and the demo timeline shows the acoustic
  factor on the dark-vessel alert.
- Rules: `librosa` is imported only inside `acoustic/`. Do not download datasets; real clips go in
  `acoustic/clips/real/` (gitignored), as described in `acoustic/README.md`.
- Allowed shortcuts: a single band-energy ratio, fixed sensor positions from the manifest (`# STUB`).
