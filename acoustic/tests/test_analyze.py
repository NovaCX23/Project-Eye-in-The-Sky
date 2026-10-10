"""Detectorul acustic: tonul de joasă frecvență declanșează, zgomotul de fond nu."""

from __future__ import annotations

from acoustic.analyze import analyze_clip
from acoustic.make_test_clips import make_clips


def _meta(name):
    return {"file": name, "sensor_id": "HYD-T", "lat": 44.2, "lon": 29.4, "offset_min": 10, "simulated": True}


def test_tone_triggers_and_noise_does_not(tmp_path, cfg):
    noise, tone = make_clips(tmp_path)
    assert analyze_clip(noise, _meta(noise.name), cfg) == []
    events = analyze_clip(tone, _meta(tone.name), cfg)
    assert events, "tonul de 50 Hz trebuia să producă un eveniment"
    e = events[0]
    assert e.event_type == "acoustic_lowfreq" and e.source == "acoustic" and e.simulated
    assert e.metrics["lowfreq_ratio"] > cfg["acoustic"]["lowfreq_ratio_threshold"]
