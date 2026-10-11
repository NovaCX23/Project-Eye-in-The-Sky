# SeaGrid: architecture slide

## Today: micro-batch, no server

```
data/      AIS (synthetic), fibre events, ground truth ─┐
acoustic/  hydrophone events (precomputed)  ────────────┼─> core/sources.py ─> detect/ rules ─> core/fusion ─> core/sinks.py ─> out/timeline.json ─> web/
assets/    infrastructure, patrol units  ───────────────┘    (only t <= now)    (AIS rules)     (score, explanation,  (atomic write)                  (Leaflet replay,
                                                                                                  patrol unit + ETA)                                       polls the file)
```

Talking points (one line each):
- **Nothing from the future.** Every input passes one gate, `sources.until(now)`, and an automated test enforces it.
- **One file of thresholds.** Every threshold and score point is in `config.yaml`; the code has no magic numbers.
- **Explainable.** The score is additive, each factor's points are visible, and the explanation is a template filled with
  the detector's numbers. No LLM.
- **Reproducible.** Deterministic alert ids; the same seed gives the same data and the same alerts.
- **Honest evaluation.** Thresholds are tuned on one seed and reported on another (held-out), see `metrics.md`.

## Path to live (variant A: server + WebSocket)

Only the three transport files change:

| Today | Live |
|---|---|
| `core/sources.py` reads files up to `now` | reads an AIS stream / sensor feeds up to `now` |
| `core/sinks.py` writes `out/timeline.json` | pushes the timeline over a WebSocket |
| `web/loader.js` polls the file | subscribes to the WebSocket |

`contracts/`, `detect/` and `acoustic/` do not change: they never assume how data arrives.
