"""Explicații din șabloane, completate cu numerele detectorului. Fără LLM."""

from __future__ import annotations

from datetime import datetime

LEVEL_TEXT = {"low": "low", "medium": "medium", "high": "high", "critical": "critical"}
DIRECTION_TEXT = {"too_slow": "too slow", "too_fast": "too fast"}

LABELS = {
    "ais_gap": "AIS signal lost",
    "speed_inconsistency": "Speed inconsistent on reappearance",
    "loitering": "Suspicious loitering",
    "position_jump": "Position jump",
    "rendezvous": "Ship-to-ship rendezvous / transfer",
    "identity_spoofing": "AIS identity spoofing",
    "acoustic_lowfreq": "Low-frequency acoustic signature",
    "fibre_vibration": "Vibration on cable fibre",
    "near_infrastructure": "Near critical infrastructure",
    "correlated_vessel": "Correlated with another suspicious vessel",
}

TEMPLATES = {
    "ais_gap": (
        "AIS silent since {since}: no message for {gap_min:.0f} min when flagged (threshold {threshold_min} min); "
        "last reported speed {last_sog_kn:.1f} kn."
    ),
    "speed_inconsistency": (
        "On reappearance it had covered {distance_km:.1f} km in {gap_min:.0f} min ({implied_kn:.1f} kn), while reporting "
        "{reported_kn:.1f} kn (expected ~{expected_km:.0f} km): {direction_text}."
    ),
    "loitering": (
        "Loitering since {since}: {duration_min:.0f} min at a mean speed of {mean_sog_kn:.1f} kn when flagged "
        "(threshold {max_mean_sog_kn} kn), within an area of {extent_km:.1f} km."
    ),
    "position_jump": (
        "Position jump of {distance_km:.1f} km in {dt_min:.1f} min ({implied_kn:.0f} kn; "
        "maximum plausible {max_implied_kn:.0f} kn)."
    ),
    "rendezvous": (
        "Potential ship-to-ship rendezvous: within {distance_km:.2f} km of partner vessel {other_mmsi} "
        "at low speed ({mean_sog_kn:.1f} kn, threshold {max_sog_kn} kn) for {duration_min:.0f} min."
    ),
    "identity_spoofing": (
        "Suspected transponder spoofing/cloning: concurrent broadcast {distance_km:.1f} km away "
        "within {dt_min:.1f} min (implied speed {implied_kn:.0f} kn, max plausible {min_implied_kn:.0f} kn)."
    ),
    "acoustic_lowfreq": (
        "Hydrophone {sensor_id} detected low-frequency energy ({band_low_hz:.0f}–{band_high_hz:.0f} Hz, "
        "ratio {lowfreq_ratio:.2f}, threshold {ratio_threshold}) at {dist_km:.1f} km."
    ),
    "fibre_vibration": "The fibre sensor reported vibration at km {cable_km:.1f} of the cable, {dist_km:.1f} km away.",
    "near_infrastructure": "The reference position is {distance_km:.1f} km from {name}.",
    "correlated_vessel": "Another suspicious vessel ({other_name}, MMSI {other_mmsi}) in the same area, {dist_km:.1f} km away.",
}

GENERIC = "Event {code} (no dedicated template)."
SIMULATED_SUFFIX = " [SIMULATED]"
HEADER = "{name} (MMSI {mmsi}): risk {score}/100, level {level_text}."
RECOMMENDATION = "Recommendation: {unit_name}, ETA {eta_min:.0f} min ({distance_km:.1f} km)."
UNKNOWN_VESSEL = "Unknown vessel"


def clock(t: datetime) -> str:
    return t.strftime("%H:%M UTC")


def label(code: str) -> str:
    return LABELS.get(code, code)


def factor_detail(code: str, values: dict, simulated: bool = False) -> str:
    v = dict(values)
    if "direction" in v:
        v["direction_text"] = DIRECTION_TEXT.get(v["direction"], v["direction"])
    try:
        text = TEMPLATES[code].format(**v)
    except (KeyError, ValueError, TypeError):
        text = GENERIC.format(code=code)
    return text + (SIMULATED_SUFFIX if simulated else "")


def alert_text(name: str | None, mmsi: str, score: int, level: str, details: list[str], rec: dict | None) -> str:
    parts = [HEADER.format(name=name or UNKNOWN_VESSEL, mmsi=mmsi, score=score, level_text=LEVEL_TEXT[level])]
    parts += [f"- {d}" for d in details]
    if rec:
        parts.append(RECOMMENDATION.format(**rec))
    return "\n".join(parts)
