---
name: contract-change
description: The only sanctioned way to change SeaGrid's shared data contracts in contracts/ (models, JSON Schema, examples), updating every stub, consumer and test and listing the affected owners. Manual invocation only, on explicit request.
disable-model-invocation: true
argument-hint: "[what to change and why]"
---

# contract-change

Requested change: $ARGUMENTS

1. Restate the change and why it is needed. If it can be done without a contract change (e.g. a new
   `event_type` value or a new key inside `metrics`), say so and stop.
2. Prefer additive, optional fields with defaults. Removing or renaming a field breaks every owner: ask for
   explicit confirmation first.
3. Edit `contracts/models.py`. Bump `SCHEMA_VERSION` for any breaking change.
4. Run `python -m contracts.export_schema` and update `contracts/examples/<Model>.json` so each example is valid.
5. Find consumers: search for the model and field names in `data/ detect/ acoustic/ core/ eval/ web/ .claude/skills/`.
   Update every producer and stub so the output still matches the schema; update `web/app.js` only to display
   the new field.
6. Update tests: `contracts/tests/` plus any test that builds the changed model.
7. Run `python -m pytest` and `/verify`.
8. Finish with a list: changed fields, files edited per directory, and the owners affected
   (Dev 1 data/eval, Dev 2 detect, Dev 3 acoustic, Dev 4 core, Dev 5 web/pitch), so each can review.
