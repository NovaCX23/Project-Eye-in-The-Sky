"""Teste pentru detectorul acustic: prag adaptiv, încredere, semnături și spectrograme."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from acoustic.analyze import (
    analyze_clip,
    classify_signature,
    compute_adaptive_threshold,
    compute_confidence,
    compute_stft,
    save_spectrogram_png,
)
from acoustic.make_test_clips import SAMPLE_RATE, make_clips


def _meta(name: str, simulated: bool = True) -> dict:
    return {"file": name, "sensor_id": "HYD-T", "lat": 44.2, "lon": 29.4, "offset_min": 10, "simulated": simulated}


def _write_custom_wav(path: Path, y: np.ndarray, sr: int = SAMPLE_RATE) -> Path:
    pcm = (np.clip(y, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return path


def test_tone_triggers_and_noise_does_not(tmp_path: Path, cfg: dict) -> None:
    """Verifică că tonul declanșează un eveniment acustic, iar zgomotul alb este ignorat."""
    noise, tone = make_clips(tmp_path)
    assert analyze_clip(noise, _meta(noise.name), cfg) == []
    events = analyze_clip(tone, _meta(tone.name), cfg)
    assert events, "the 50 Hz tone should have produced an event"
    e = events[0]
    assert e.event_type == "acoustic_lowfreq" and e.source == "acoustic" and e.simulated
    assert e.metrics["lowfreq_ratio"] > cfg["acoustic"]["lowfreq_ratio_threshold"]
    assert e.metrics["signature"] == "propeller"
    assert abs(float(e.metrics["dominant_freq_hz"]) - 50.0) <= 5.0
    assert 0.0 <= e.confidence <= 1.0


def test_adaptive_threshold_behavior(cfg: dict) -> None:
    """Verifică adaptabilitatea pragului în funcție de nivelul de zgomot de fond."""
    # Fond silențios -> pragul rămâne la valoarea de bază
    quiet_ratios = np.array([0.08, 0.09, 0.10, 0.11, 0.12])
    t_quiet, floor_quiet = compute_adaptive_threshold(quiet_ratios, cfg)
    assert t_quiet == cfg["acoustic"]["lowfreq_ratio_threshold"]
    assert floor_quiet < 0.15

    # Fond ridicat (zgomot oceanic ambiental mare) -> pragul crește adaptiv
    noisy_ratios = np.array([0.40, 0.42, 0.41, 0.43, 0.45])
    t_noisy, floor_noisy = compute_adaptive_threshold(noisy_ratios, cfg)
    assert t_noisy > cfg["acoustic"]["lowfreq_ratio_threshold"]
    assert t_noisy == min(cfg["acoustic"]["max_adaptive_threshold"], floor_noisy + cfg["acoustic"]["adaptive_margin"])

    # Semnal pur (ton pe tot clipul) -> pragul nu blochează semnalul
    tone_ratios = np.array([0.95, 0.96, 0.98, 0.97, 0.99])
    t_tone, _ = compute_adaptive_threshold(tone_ratios, cfg)
    assert t_tone == cfg["acoustic"]["lowfreq_ratio_threshold"]


def test_transient_rejection(tmp_path: Path, cfg: dict) -> None:
    """Ignoră impulsurile tranzitorii scurte sub min_event_s."""
    sr = SAMPLE_RATE
    total_samples = sr * 10
    t = np.arange(total_samples) / sr
    y = np.random.default_rng(42).normal(0, 0.03, total_samples)

    # Impuls scurt de 1 secundă de ton 50 Hz (sub min_event_s = 3.0s)
    y[sr : 2 * sr] += 0.5 * np.sin(2 * np.pi * 50 * t[sr : 2 * sr])

    clip_path = _write_custom_wav(tmp_path / "transient.wav", y, sr)
    events = analyze_clip(clip_path, _meta(clip_path.name), cfg)
    assert events == [], "impulsul tranzitoriu scurt trebuia ignorat"


def test_confidence_calculation(cfg: dict) -> None:
    """Încrederea crește cu durata și intensitatea și rămâne în [0, 1]."""
    conf_short = compute_confidence(mean_ratio=0.7, dur_s=3.0, mean_rms=0.03, threshold=0.6, cfg=cfg)
    conf_long = compute_confidence(mean_ratio=0.9, dur_s=20.0, mean_rms=0.25, threshold=0.6, cfg=cfg)

    assert 0.0 <= conf_short <= 1.0
    assert 0.0 <= conf_long <= 1.0
    assert conf_long > conf_short


def test_signature_classification_anchor_chain(tmp_path: Path, cfg: dict) -> None:
    """Tonurile în banda superioară (120 Hz) sunt clasificate ca lanț de ancoră."""
    sr = SAMPLE_RATE
    total_samples = sr * 10
    t = np.arange(total_samples) / sr
    # Ton predominant la 120 Hz (în banda anchor_chain [75, 180] Hz)
    y = 0.4 * np.sin(2 * np.pi * 120 * t) + np.random.default_rng(123).normal(0, 0.02, total_samples)
    clip_path = _write_custom_wav(tmp_path / "chain.wav", y, sr)

    events = analyze_clip(clip_path, _meta(clip_path.name), cfg)
    assert events, "tonul de 120 Hz trebuia să declanșeze un eveniment"
    e = events[0]
    assert e.metrics["signature"] == "anchor_chain"
    assert abs(float(e.metrics["dominant_freq_hz"]) - 120.0) <= 5.0


def test_spectrogram_png_generation(tmp_path: Path, cfg: dict) -> None:
    """Verifică generarea unei spectrograme valide în format PNG."""
    sr = SAMPLE_RATE
    t = np.arange(sr * 5) / sr
    y = 0.3 * np.sin(2 * np.pi * 60 * t)
    _, _, S, freqs = compute_stft(y, sr, cfg)

    out_png = tmp_path / "test_spec.png"
    save_spectrogram_png(out_png, S, freqs)

    assert out_png.exists()
    data = out_png.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(data) > 1000
