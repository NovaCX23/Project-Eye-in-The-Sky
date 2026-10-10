"""Generează clipuri SINTETICE de test: zgomot de fond, elice, lanț de ancoră și motor loitering.

Rulare:  python -m acoustic.make_test_clips
Produce: acoustic/clips/background_noise.wav
         acoustic/clips/lowfreq_tone.wav
         acoustic/clips/anchor_drag.wav
         acoustic/clips/engine_rumble.wav
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from contracts.runtime import utf8_stdout

CLIPS_DIR = Path(__file__).resolve().parent / "clips"

# Parametrii sintetici de generare audio pentru scenariul maritim
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

    # 1. Zgomot de fond oceanic ambiental (fără semnal coerent)
    noise = rng.normal(0, 0.05, n)

    # 2. Cavitație elice navă cargo: 50 Hz fundamentală + 100 Hz armonică cu anvelopă de trecere
    env_cargo = np.clip(np.sin(np.pi * t / DURATION_S) * 1.5, 0, 1)
    tone_propeller = env_cargo * (0.35 * np.sin(2 * np.pi * 50 * t) + 0.15 * np.sin(2 * np.pi * 100 * t)) + rng.normal(0, 0.02, n)

    # 3. Lanț de ancoră târât pe fundul mării: frecare metalică 120 Hz + 160 Hz pe cablu submarin
    env_chain = np.clip(np.sin(np.pi * t / DURATION_S) * 1.3, 0, 1)
    scraping_mod = 1.0 + 0.3 * np.sin(2 * np.pi * 4 * t)  # modulație periodică de salt pe roci
    chain_drag = env_chain * (0.30 * np.sin(2 * np.pi * 120 * t) + 0.15 * np.sin(2 * np.pi * 160 * t)) * scraping_mod + rng.normal(0, 0.03, n)

    # 4. Motor auxiliar navă loitering (pescador suspect la turație mică): 65 Hz
    env_loiter = np.clip(np.sin(np.pi * t / DURATION_S) * 1.4, 0, 1)
    engine_rumble = env_loiter * (0.32 * np.sin(2 * np.pi * 65 * t) + 0.10 * np.sin(2 * np.pi * 130 * t)) + rng.normal(0, 0.02, n)

    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [
        out_dir / "background_noise.wav",
        out_dir / "lowfreq_tone.wav",
        out_dir / "anchor_drag.wav",
        out_dir / "engine_rumble.wav",
    ]
    _write_wav(paths[0], noise, SAMPLE_RATE)
    _write_wav(paths[1], tone_propeller, SAMPLE_RATE)
    _write_wav(paths[2], chain_drag, SAMPLE_RATE)
    _write_wav(paths[3], engine_rumble, SAMPLE_RATE)
    return paths


def main() -> int:
    utf8_stdout()
    for p in make_clips():
        print(f"[acoustic.make_test_clips] wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
