"""Șabloanele de explicație: semnătura acustică apare doar când detectorul o furnizează."""

from __future__ import annotations

from core import explain

ACOUSTIC = {"sensor_id": "HYD-1", "band_low_hz": 10.0, "band_high_hz": 200.0, "lowfreq_ratio": 0.96,
            "ratio_threshold": 0.6, "dist_km": 1.2}


def test_acoustic_detail_names_signature():
    text = explain.factor_detail("acoustic_lowfreq", dict(ACOUSTIC, signature="propeller", dominant_freq_hz=50.0))
    assert "propeller cavitation" in text
    assert "50 Hz" in text


def test_acoustic_detail_without_signature_is_unchanged():
    text = explain.factor_detail("acoustic_lowfreq", ACOUSTIC, simulated=True)
    assert "Signature" not in text
    assert text.startswith("Hydrophone HYD-1") and text.endswith("[SIMULATED]")


def test_unknown_signature_falls_back_to_raw_value():
    text = explain.factor_detail("acoustic_lowfreq", dict(ACOUSTIC, signature="whale", dominant_freq_hz=20.0))
    assert "Signature: whale" in text
