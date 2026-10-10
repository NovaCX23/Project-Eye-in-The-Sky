"""Generează două clipuri SINTETICE de test: zgomot de fond și ton de joasă frecvență.

Rulare:  python -m acoustic.make_test_clips
Produce: acoustic/clips/background_noise.wav, acoustic/clips/lowfreq_tone.wav
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from contracts.runtime import utf8_stdout

CLIPS_DIR = Path(__file__).resolve().parent / "clips"

# STUB: parametrii clipurilor de test (nu sunt praguri de detecție, doar conținut sintetic).
SAMPLE_RATE = 4000
DURATION_S = 20
SEED = 2026


def _write_wav(path: Path, y: np.ndarray, sr: int) -> None:
    pcm = (np.clip(y, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def make_clips(out_dir: Path = CLIPS_DIR) -> list[Path]:
    rng = np.random.default_rng(SEED)
    n = SAMPLE_RATE * DURATION_S
    t = np.arange(n) / SAMPLE_RATE
    noise = rng.normal(0, 0.05, n)  # zgomot alb, bandă largă
    # Ton de 50 Hz + armonica de 100 Hz, cu anvelopă (ex. elice / lanț de ancoră târât).
    env = np.clip(np.sin(np.pi * t / DURATION_S) * 1.5, 0, 1)
    tone = env * (0.35 * np.sin(2 * np.pi * 50 * t) + 0.15 * np.sin(2 * np.pi * 100 * t)) + rng.normal(0, 0.02, n)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / "background_noise.wav", out_dir / "lowfreq_tone.wav"]
    _write_wav(paths[0], noise, SAMPLE_RATE)
    _write_wav(paths[1], tone, SAMPLE_RATE)
    return paths


def main() -> int:
    utf8_stdout()
    for p in make_clips():
        print(f"[acoustic.make_test_clips] scris {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
