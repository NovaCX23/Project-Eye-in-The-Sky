"""Detector de energie de joasă frecvență pe clipuri audio -> SensorEvent `acoustic_lowfreq`.

Rezultatele sunt PRE-CALCULATE (o singură rulare), apoi pipeline-ul le citește filtrate după `now`.

Rulare:  python -m acoustic.analyze --out-dir out
Consumă: acoustic/clips/manifest.json + fișierele .wav, config.yaml (acoustic.*)
Produce: <out-dir>/acoustic_events.json (listă de SensorEvent)
         <out-dir>/spectrograms/*.png (spectrograme salvate pentru pitch și analiză)
"""

from __future__ import annotations

import argparse
import struct
import zlib
from datetime import timedelta
from pathlib import Path

import librosa
import numpy as np

from acoustic.make_test_clips import CLIPS_DIR, make_clips
from contracts.models import SensorEvent
from contracts.runtime import OUT_DIR, load_config, parse_time, read_json, stable_id, utf8_stdout, write_json_atomic

REAL_CLIPS_DIR = CLIPS_DIR / "real"


def compute_stft(y: np.ndarray, sr: int, cfg: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Calculează STFT, frecvențele FFT, raportul de energie în bandă și RMS pe cadre."""
    c = cfg["acoustic"]
    n_fft = int(sr * c["frame_s"])
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=n_fft, center=False)) ** 2
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    band = (freqs >= c["band_hz"][0]) & (freqs <= c["band_hz"][1])
    total = S.sum(axis=0) + 1e-12
    ratio = S[band].sum(axis=0) / total
    rms = librosa.feature.rms(y=y, frame_length=n_fft, hop_length=n_fft, center=False)[0]
    k = min(len(ratio), len(rms), S.shape[1])
    return ratio[:k], rms[:k], S[:, :k], freqs


def lowfreq_frames(y: np.ndarray, sr: int, cfg: dict) -> tuple[np.ndarray, np.ndarray]:
    """Pentru fiecare cadru: raportul energie_în_bandă / energie_totală și RMS."""
    ratio, rms, _, _ = compute_stft(y, sr, cfg)
    return ratio, rms


def compute_adaptive_threshold(ratio: np.ndarray, cfg: dict) -> tuple[float, float]:
    """Calculează pragul adaptiv relativ la nivelul de zgomot ambiant (percentila joasă).

    Returnează (prag_efectiv, nivel_zgomot_fond).
    """
    c = cfg["acoustic"]
    base_thresh = float(c["lowfreq_ratio_threshold"])
    if len(ratio) == 0:
        return base_thresh, 0.0

    quantile = float(c.get("noise_floor_quantile", 0.25))
    noise_floor = float(np.percentile(ratio, quantile * 100))

    if c.get("adaptive_threshold", False):
        margin = float(c.get("adaptive_margin", 0.25))
        max_thresh = float(c.get("max_adaptive_threshold", 0.85))
        # Dacă întreaga înregistrare este dominată de semnal (noise_floor >= base_thresh),
        # folosim pragul de bază pentru a nu masca evenimentul.
        if noise_floor >= base_thresh:
            effective_thresh = base_thresh
        else:
            effective_thresh = min(max_thresh, max(base_thresh, noise_floor + margin))
    else:
        effective_thresh = base_thresh

    return effective_thresh, noise_floor


def compute_confidence(
    mean_ratio: float,
    dur_s: float,
    mean_rms: float,
    threshold: float,
    cfg: dict,
) -> float:
    """Calculează încrederea combinând raportul energetic, durata susținută și intensitatea RMS."""
    c = cfg["acoustic"]
    weights = c.get("confidence_weights", {"ratio": 0.5, "duration": 0.3, "rms": 0.2})
    target_dur = float(c.get("target_duration_s", 15.0))
    target_rms = float(c.get("target_rms", 0.15))
    scale = float(c.get("confidence_scale", 1.0))

    ratio_score = min(1.0, mean_ratio * scale)
    dur_score = min(1.0, dur_s / target_dur) if target_dur > 0 else 1.0
    rms_score = min(1.0, mean_rms / target_rms) if target_rms > 0 else 1.0

    w_r = float(weights.get("ratio", 0.5))
    w_d = float(weights.get("duration", 0.3))
    w_i = float(weights.get("rms", 0.2))
    w_sum = w_r + w_d + w_i
    if w_sum <= 0:
        w_sum = 1.0

    conf = (w_r * ratio_score + w_d * dur_score + w_i * rms_score) / w_sum
    return round(float(np.clip(conf, 0.0, 1.0)), 3)


def classify_signature(
    S: np.ndarray,
    freqs: np.ndarray,
    i: int,
    j: int,
    cfg: dict,
) -> tuple[str, float]:
    """Clasifică semnătura în bandă (elice vs. lanț de ancoră) și află frecvența dominantă."""
    c = cfg["acoustic"]
    sig_cfg = c.get("signatures", {})
    prop_band = sig_cfg.get("propeller_band_hz", [20.0, 75.0])
    chain_band = sig_cfg.get("anchor_chain_band_hz", [75.0, 180.0])

    band_cfg = c["band_hz"]
    in_band = (freqs >= band_cfg[0]) & (freqs <= band_cfg[1])
    prop_idx = (freqs >= prop_band[0]) & (freqs <= prop_band[1])
    chain_idx = (freqs >= chain_band[0]) & (freqs <= chain_band[1])

    segment_S = S[:, i : j + 1]
    prop_energy = float(segment_S[prop_idx].sum())
    chain_energy = float(segment_S[chain_idx].sum())

    mean_spectrum = segment_S[in_band].mean(axis=1) if in_band.any() else np.array([])
    if len(mean_spectrum) > 0 and mean_spectrum.sum() > 0:
        band_freqs = freqs[in_band]
        dominant_freq_hz = float(band_freqs[int(np.argmax(mean_spectrum))])
    else:
        dominant_freq_hz = 0.0

    if prop_energy > 1.2 * chain_energy:
        signature = "propeller"
    elif chain_energy > 1.2 * prop_energy:
        signature = "anchor_chain"
    else:
        signature = "lowfreq_mixed"

    return signature, round(dominant_freq_hz, 1)


def save_spectrogram_png(path: Path, S: np.ndarray, freqs: np.ndarray, max_freq_hz: float = 500.0) -> None:
    """Generează și salvează o spectrogramă PNG fără dependențe externe de plotting."""
    idx = freqs <= max_freq_hz
    sub_S = S[idx, :]
    if sub_S.size == 0:
        return

    db = 10.0 * np.log10(sub_S + 1e-12)
    db_min = float(np.percentile(db, 5))
    db_max = float(np.percentile(db, 99))
    if db_max <= db_min:
        db_max = db_min + 1.0
    norm = np.clip((db - db_min) / (db_max - db_min), 0.0, 1.0)
    norm = np.flipud(norm)

    target_h = 256
    target_w = max(300, min(800, sub_S.shape[1] * 20))
    y_idx = (np.linspace(0, norm.shape[0] - 1, target_h)).astype(int)
    x_idx = (np.linspace(0, norm.shape[1] - 1, target_w)).astype(int)
    scaled = norm[np.ix_(y_idx, x_idx)]

    # Colormap marin/sonar contrastant (albastru închis -> cyan -> galben -> alb)
    r = np.clip(np.where(scaled < 0.5, scaled * 0.4, (scaled - 0.5) * 2.0), 0.0, 1.0)
    g = np.clip(
        np.where(scaled < 0.3, scaled * 1.5, np.where(scaled < 0.8, 0.45 + (scaled - 0.3) * 1.1, 1.0)),
        0.0,
        1.0,
    )
    b = np.clip(np.where(scaled < 0.4, 0.3 + scaled * 1.75, (1.0 - scaled) * 2.0), 0.0, 1.0)
    rgb = (np.stack([r, g, b], axis=-1) * 255).astype(np.uint8)

    path.parent.mkdir(parents=True, exist_ok=True)
    raw_rows = b"".join(b"\x00" + rgb[row].tobytes() for row in range(target_h))
    compressed = zlib.compress(raw_rows)

    def png_chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", target_w, target_h, 8, 2, 0, 0, 0)
    png_bytes = b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", ihdr) + png_chunk(b"IDAT", compressed) + png_chunk(b"IEND", b"")
    path.write_bytes(png_bytes)


def analyze_clip(path: Path, meta: dict, cfg: dict, out_dir: Path | None = None) -> list[SensorEvent]:
    """Analizează un clip audio individual cu prag adaptiv, filtrare tranzitorii și clasificare semnătură."""
    c = cfg["acoustic"]
    y, sr = librosa.load(path, sr=None, mono=True)
    ratio, rms, S, freqs = compute_stft(y, sr, cfg)

    threshold, noise_floor = compute_adaptive_threshold(ratio, cfg)
    hot = (ratio > threshold) & (rms > c["min_rms"])

    clip_start = parse_time(cfg["scenario"]["start"]) + timedelta(minutes=meta["offset_min"])
    transient_filter_s = float(c.get("transient_filter_s", 2.0))
    min_event_s = float(c["min_event_s"])

    # Salvare spectrogramă pentru pitch / revizuire dacă este configurat
    if out_dir is not None and c.get("save_spectrograms", True):
        spec_path = out_dir / "spectrograms" / f"{Path(meta['file']).stem}.png"
        save_spectrogram_png(spec_path, S, freqs)

    events: list[SensorEvent] = []
    i = 0
    while i < len(hot):
        if not hot[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(hot) and hot[j + 1]:
            j += 1
        dur_s = (j - i + 1) * c["frame_s"]

        # Ignoră tranzitorii scurți (ex. impulsuri scurte sau zgomote sub min_event_s)
        if dur_s >= min_event_s and dur_s > transient_filter_s:
            start = clip_start + timedelta(seconds=i * c["frame_s"])
            mean_ratio = float(ratio[i : j + 1].mean())
            mean_rms = float(rms[i : j + 1].mean())
            conf = compute_confidence(mean_ratio, dur_s, mean_rms, threshold, cfg)
            signature, dominant_freq_hz = classify_signature(S, freqs, i, j, cfg)

            events.append(
                SensorEvent(
                    event_id=stable_id("acoustic", meta["sensor_id"], start, prefix="evt-"),
                    event_type="acoustic_lowfreq",
                    source="acoustic",
                    sensor_id=meta["sensor_id"],
                    start=start,
                    end=start + timedelta(seconds=dur_s),
                    lat=meta["lat"],
                    lon=meta["lon"],
                    confidence=conf,
                    metrics={
                        "duration_s": dur_s,
                        "lowfreq_ratio": round(mean_ratio, 3),
                        "ratio_threshold": round(threshold, 3),
                        "band_low_hz": c["band_hz"][0],
                        "band_high_hz": c["band_hz"][1],
                        "rms": round(mean_rms, 4),
                        "clip": meta["file"],
                        "noise_floor": round(noise_floor, 3),
                        "signature": signature,
                        "dominant_freq_hz": dominant_freq_hz,
                    },
                    simulated=bool(meta.get("simulated", True)),
                )
            )
        i = j + 1
    return events


def analyze_all(cfg: dict, clips_dir: Path = CLIPS_DIR, out_dir: Path | None = None) -> list[SensorEvent]:
    """Procesează toate clipurile din manifest și returnează lista sortată de SensorEvent."""
    REAL_CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = read_json(clips_dir / "manifest.json")
    missing = [m for m in manifest["clips"] if not (clips_dir / m["file"]).exists()]
    if missing and clips_dir == CLIPS_DIR:
        make_clips(clips_dir)  # Regenerăm clipurile de test sintetice dacă lipsesc

    events: list[SensorEvent] = []
    for meta in manifest["clips"]:
        clip_path = clips_dir / meta["file"]
        if not clip_path.exists():
            print(f"[acoustic.analyze] Warning: clip not found, skipping: {clip_path}")
            continue
        events.extend(analyze_clip(clip_path, meta, cfg, out_dir=out_dir))
    return sorted(events, key=lambda e: (e.start, e.event_id))


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args(argv)

    cfg = load_config()
    events = analyze_all(cfg, out_dir=args.out_dir)
    path = args.out_dir / "acoustic_events.json"
    write_json_atomic(path, [e.model_dump(mode="json") for e in events])
    print(f"[acoustic.analyze] {len(events)} acoustic events -> {path}")
    if cfg["acoustic"].get("save_spectrograms", True):
        spec_dir = args.out_dir / "spectrograms"
        print(f"[acoustic.analyze] Spectrograms saved -> {spec_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
