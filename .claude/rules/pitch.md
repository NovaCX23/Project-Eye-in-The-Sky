---
paths:
  - "pitch/**"
---

# pitch/ (owner: Dev 5)

- Owns: `outline.md` (presentation outline), `jury_questions.md` (likely questions + short answers),
  `metrics.md` (generated, do not hand-edit).
- Consumes: `pitch/metrics.md` from `/eval-report` (held-out seed only), screenshots of the running demo.
- Produces: the pitch material, in Romanian.
- Commands: `python -m eval.evaluate --seed-set both --run --write-md pitch/metrics.md` to refresh the numbers.
- Done when: every number in the pitch comes from `metrics.md`, and simulated data and approximate coordinates
  are stated plainly.
- Rules: quote held-out (reporting seed) numbers only. Never claim real-world accuracy from synthetic data.
