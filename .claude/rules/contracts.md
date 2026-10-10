---
paths:
  - "contracts/**"
---

# contracts/ (shared)

Changes here go only through the `/contract-change` skill, and only when a human explicitly asks for one.
If a task seems to need a contract change, say so and stop.

- Owns: `models.py` (PositionMessage, SensorEvent, Alert, Timeline and sub-models), `schema/*.schema.json`
  (generated), `examples/*.json`, `geo.py` (haversine and helpers), `runtime.py` (paths, config, `stable_id`,
  UTF-8 I/O), `assets.py` (infrastructure and patrol loading), `testing.py` (test data builders), `validate.py`.
- Consumes: nothing from other modules. Never import from `data/`, `detect/`, `acoustic/`, `core/`, `web/`.
- Produces: the types every other module imports.
- Commands: `python -m contracts.export_schema [--check]`,
  `python -m contracts.validate <file> --model <Name>`, `python -m pytest contracts`.
- Done when: models, exported schema, and examples agree (`pytest contracts` green), and every consumer
  listed by `contract-change` still passes its tests.
- Allowed shortcuts: none. Contracts are the one place that must be exact. New event types need no contract
  change: `event_type` is a free snake_case string.
