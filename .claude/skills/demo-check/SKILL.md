---
name: demo-check
description: Regenerates the fixed-seed demo and confirms every story beat appears in out/timeline.json at the expected time (vessel goes dark, second vessel loiters, acoustic and fibre events, score reaches critical, patrol unit recommended, inconsistent reappearance). Use before a rehearsal or after changing data, detect, core, assets or the scenario.
allowed-tools: Bash(python .claude/skills/demo-check/check_story.py *) PowerShell(python .claude/skills/demo-check/check_story.py *)
---

# demo-check

1. From the repo root run `python .claude/skills/demo-check/check_story.py`
   (`--no-regen` checks the existing `out/timeline.json` without rerunning `python -m core.demo`).
2. Deadlines come from the `expected` section of `data/scenarios/demo.yaml`, in minutes from `scenario.start`.
3. Report the printed table as is: one line per beat with its simulated time.
4. If a beat fails, find which module produced the missing piece:
   gap/loitering events come from `detect/` (Dev 2), acoustic from `acoustic/` (Dev 3), fibre and story timing from
   `data/` (Dev 1), score, level and recommendation from `core/` (Dev 4). Fix it only if you own that directory;
   otherwise report it to the owner and stop.
5. Never "fix" a beat by moving the deadline in `expected` without the team agreeing.
