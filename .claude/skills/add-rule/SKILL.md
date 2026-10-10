---
name: add-rule
description: Adds a new SeaGrid detection rule end to end (threshold in config.yaml, new SensorEvent type, score points, English explanation template, a test on an injected case and one on normal traffic), then runs eval-report and confirms false alarms did not rise. Use when someone asks for a new AIS behaviour to be detected.
---

# add-rule

Touches `detect/` (Dev 2) and, for the score entry and template, `core/` and `config.yaml` sections owned by Dev 4.
If the user does not own both, do the `detect/` part and list the exact `core/` edits for Dev 4 instead of making them.

1. Name the event type in snake_case, e.g. `dark_rendezvous`. No contract change is needed: `event_type` is a free string.
2. Thresholds: add a block under `detect.<rule_name>` in `config.yaml`. No numbers in code.
3. Rule: add `detect_<rule_name>(df, ..., cfg) -> list[SensorEvent]` in `detect/ais_rules.py`.
   Use `contracts.geo` for distances, `_event(...)` for ids, put every number the template needs in `metrics`,
   honour `detect/zones.is_excluded` if it applies, and call it from `run_all`.
4. Score: add `score.points.<event_type>` in `config.yaml` (fusion raises a `KeyError` without it).
5. Template: add `LABELS[<type>]` and `TEMPLATES[<type>]` (English) in `core/explain.py`, using only keys from `metrics`.
6. Tests in `detect/tests/test_rules.py`: one injected positive case and one normal-traffic case that must
   produce no event. Use `contracts.testing.straight_track`.
7. Optional, for evaluation: ask Dev 1 to run `/add-anomaly` so the rule has ground truth.
8. Run `python -m pytest`, then `/eval-report`. Compare false alarms with the previous run on both seeds;
   if they rose, tighten the threshold (tuning seed only) or drop the rule.
9. Run `/verify`.
