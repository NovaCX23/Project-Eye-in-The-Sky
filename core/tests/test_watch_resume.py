"""--watch reia de unde a rămas după repornire, cu aceeași ieșire ca o rulare fără pauză."""

from __future__ import annotations

import shutil

from contracts.runtime import read_json
from core import pipeline
from core.state import STATE_FILE

STEP_MIN = 30
TOTAL_TICKS = 6     # 06:00 -> 09:00: acoperă alerta navei stinse și repartizarea unităților


def _watch(in_dir, out_dir, cfg, ticks, fresh=False):
    pipeline.watch(in_dir, out_dir, cfg, interval_s=0, sim_step_min=STEP_MIN, max_ticks=ticks, fresh=fresh)
    return read_json(out_dir / "timeline.json")


def test_resumed_run_matches_uninterrupted_run(demo_out, cfg, tmp_path):
    straight = _watch(demo_out, tmp_path / "a", cfg, TOTAL_TICKS)
    _watch(demo_out, tmp_path / "b", cfg, 2)
    resumed = _watch(demo_out, tmp_path / "b", cfg, TOTAL_TICKS - 2)
    assert resumed == straight
    assert straight["alerts"], "the window should contain at least one alert"


def test_fresh_ignores_saved_state(demo_out, cfg, tmp_path):
    _watch(demo_out, tmp_path, cfg, 2)
    again = _watch(demo_out, tmp_path, cfg, 1, fresh=True)
    assert again["batch_index"] == 1


def test_changed_past_data_restarts_from_scenario_start(demo_out, cfg, tmp_path):
    in_dir = tmp_path / "in"
    shutil.copytree(demo_out, in_dir)
    out = tmp_path / "out"
    _watch(in_dir, out, cfg, 2)
    assert (out / STATE_FILE).exists()
    lines = (in_dir / "ais.csv").read_text(encoding="utf-8").splitlines(keepends=True)
    (in_dir / "ais.csv").write_text("".join(lines[:1] + lines[2:]), encoding="utf-8")   # dispare un mesaj din trecut
    again = _watch(in_dir, out, cfg, 1)
    assert again["batch_index"] == 1
