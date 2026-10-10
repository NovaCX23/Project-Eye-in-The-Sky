---
name: verify
description: Pre-commit check for SeaGrid. Runs the tests, regenerates the demo, validates out/timeline.json against the Timeline schema, and confirms the demo-scenario alert is still there. Use before every commit or merge, or whenever someone asks "does main still work?".
allowed-tools: Bash(python .claude/skills/verify/verify.py *) PowerShell(python .claude/skills/verify/verify.py *)
---

# verify

1. From the repo root, with the virtualenv active, run:
   `python .claude/skills/verify/verify.py`
   (add `--skip-tests` only if tests already ran in this session with no edits since).
2. The script runs, in order: `python -m pytest`, `python -m core.demo`,
   `python -m contracts.validate out/timeline.json --model Timeline`, then checks that exactly one alert exists for the
   dark vessel from `data/scenarios/demo.yaml` and that it carries the `ais_gap` factor.
3. If it prints `VERIFY: OK`, the change may be committed. Report the alert id, score and level it printed.
4. If any step fails, do not commit. Show the failing step's output, fix it only if the failing code is in a
   directory the current user owns, otherwise name the owner (see `AGENTS.md`) and stop.
