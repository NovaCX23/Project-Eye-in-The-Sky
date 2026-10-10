"""Evaluarea găsește anomaliile scenariului demo."""

from __future__ import annotations

from eval.evaluate import evaluate, table


def test_demo_anomalies_detected(demo_out, cfg):
    m = evaluate(demo_out, cfg)
    assert m.n_anomalies >= 2
    assert not any(miss.startswith(("ais_gap 636012345", "loitering 667001234")) for miss in m.missed)
    assert m.mean_tta_min is not None and m.mean_tta_min >= 0
    assert "Rată detecție" in table([m])
