---
name: integrate
description: Pre-merge checklist for the SeaGrid integration owner (Dev 4) - rebase a role branch on main, run verify, open the page and confirm the alert renders, then merge. Manual invocation only.
disable-model-invocation: true
argument-hint: "[role branch, e.g. role/detect]"
---

# integrate

Branch to integrate: $ARGUMENTS

1. `git status` must be clean. `git fetch` if a remote exists.
2. `git switch $ARGUMENTS` and `git rebase main`. On conflicts in a directory the branch's owner does not own,
   stop and report; do not resolve them yourself.
3. Check ownership: `git diff --stat main...HEAD` should only touch the owner's directories (see `AGENTS.md`).
   Changes to `contracts/` must come from `/contract-change`. Report anything else.
4. Run `python .claude/skills/verify/verify.py`. Stop on failure.
5. Run `python .claude/skills/demo-check/check_story.py --no-regen`.
6. Ask the human to run `python -m http.server 8000` in the repo root, open http://localhost:8000/web/, press play,
   and confirm the MV SEA FALCON alert appears with its factor breakdown and SIMULAT labels. Wait for the answer.
7. On confirmation: `git switch main` and `git merge --ff-only $ARGUMENTS`. Do not push unless asked.
8. Commit messages stay human-authored: no AI trailers (the commit-msg hook rejects them; never `--no-verify`).
