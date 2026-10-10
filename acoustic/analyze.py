"""Detector de energie de joasă frecvență pe clipuri audio -> SensorEvent `acoustic_lowfreq`.

Rezultatele sunt PRE-CALCULATE (o singură rulare), apoi pipeline-ul le citește filtrate după `now`.

Rulare:  python -m acoustic.analyze --out-dir out
Consumă: acoustic/clips/manifest.json + fișierele .wav, config.yaml (acoustic.*)
Produce: <out-dir>/acoustic_events.json (listă de SensorEvent)
"""

from __future__ import annotations

import argparse
from datetime import timedelta
from pathlib import Path

import librosa
import numpy as np

from acoustic.make_test_clips import CLIPS_DIR, make_clips
from contracts.models import SensorEvent
from contracts.runtime import OUT_DIR, load_config, parse_time, read_json, stable_id, utf8_stdout, write_json_atomic


def lowfreq_frames(y: np.ndarray, sr: int, cfg: dict) -> tuple[np.ndarray, np.ndarray]:
    """Pentru fiecare cadru: raportul energie_în_bandă / energie_totală și RMS."""
    c = cfg["acoustic"]
    n_fft = int(sr * c["frame_s"])
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=n_fft, center=False)) ** 2
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    band = (freqs >= c["band_hz"][0]) & (freqs <= c["band_hz"][1])
    total = S.sum(axis=0) + 1e-12
    ratio = S[band].sum(axis=0) / total
    rms = librosa.feature.rms(y=y, frame_length=n_fft, hop_length=n_fft, center=False)[0]
    k = min(len(ratio), len(rms))
    return ratio[:k], rms[:k]


def analyze_clip(path: Path, meta: dict, cfg: dict) -> list[SensorEvent]:
    # STUB: doar raportul de energie în bandă; fără clasificare, fără estimare de direcție.
    c = cfg["acoustic"]
    y, sr = librosa.load(path, sr=None, mono=True)
    ratio, rms = lowfreq_frames(y, sr, cfg)
    hot = (ratio > c["lowfreq_ratio_threshold"]) & (rms > c["min_rms"])
    clip_start = parse_time(cfg["scenario"]["start"]) + timedelta(minutes=meta["offset_min"])
    events = []
    i = 0
    while i < len(hot):
        if not hot[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(hot) and hot[j + 1]:
            j += 1
        dur_s = (j - i + 1) * c["frame_s"]
        if dur_s >= c["min_event_s"]:
            start = clip_start + timedelta(seconds=i * c["frame_s"])
            mean_ratio = float(ratio[i : j + 1].mean())
            events.append(SensorEvent(
                event_id=stable_id("acoustic", meta["sensor_id"], start, prefix="evt-"),
                event_type="acoustic_lowfreq",
                source="acoustic",
                sensor_id=meta["sensor_id"],
                start=start,
                end=start + timedelta(seconds=dur_s),
                lat=meta["lat"],
                lon=meta["lon"],
                confidence=round(min(1.0, mean_ratio * c["confidence_scale"]), 3),
                metrics={
                    "duration_s": dur_s,
                    "lowfreq_ratio": round(mean_ratio, 3),
                    "ratio_threshold": c["lowfreq_ratio_threshold"],
                    "band_low_hz": c["band_hz"][0],
                    "band_high_hz": c["band_hz"][1],
                    "rms": round(float(rms[i : j + 1].mean()), 4),
                    "clip": meta["file"],
                },
                simulated=bool(meta.get("simulated", True)),
            ))
        i = j + 1
    return events


def analyze_all(cfg: dict, clips_dir: Path = CLIPS_DIR) -> list[SensorEvent]:
    manifest = read_json(clips_dir / "manifest.json")
    missing = [m for m in manifest["clips"] if not (clips_dir / m["file"]).exists()]
    if missing and clips_dir == CLIPS_DIR:
        make_clips(clips_dir)  # STUB: lipsesc clipurile de test => le regenerăm
    events: list[SensorEvent] = []
    for meta in manifest["clips"]:
        events.extend(analyze_clip(clips_dir / meta["file"], meta, cfg))
    return sorted(events, key=lambda e: (e.start, e.event_id))


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args(argv)
    events = analyze_all(load_config())
    path = args.out_dir / "acoustic_events.json"
    write_json_atomic(path, [e.model_dump(mode="json") for e in events])
    print(f"[acoustic.analyze] {len(events)} acoustic events -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
