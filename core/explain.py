"""Explicații din șabloane, completate cu numerele detectorului. Fără LLM."""

from __future__ import annotations

from datetime import datetime

LEVEL_TEXT = {"low": "low", "medium": "medium", "high": "high", "critical": "critical"}
DIRECTION_TEXT = {"too_slow": "too slow", "too_fast": "too fast"}
SIGNATURE_TEXT = {
    "propeller": "propeller cavitation / shaft harmonics",
    "anchor_chain": "anchor chain friction",
    "lowfreq_mixed": "mixed low-frequency noise",
}

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
    "sar_gap_confirmation": "Radar sees the silent vessel",
    "sar_dark_target": "Radar target with no AIS",
    "sar_dark_target_uncovered": "Radar target with no AIS (reception unproven)",
    "ais_no_radar_return": "AIS position with no radar return",
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
    "correlated_vessel": "Another suspicious vessel ({other_label}) in the same area, {dist_km:.1f} km away.",
    "sar_gap_confirmation": (
        "{satellite} radar image of {acquired} (published {published}): a {length_m:.0f} m target with no AIS, "
        "{dist_km:.1f} km from where {candidate_name} went silent {silent_min:.0f} min earlier, within the "
        "{radius_km:.1f} km it could have covered: the vessel is sailing dark."
    ),
    "sar_dark_target": (
        "{satellite} radar image of {acquired} (published {published}): a {length_m:.0f} m vessel-sized target "
        "with no AIS, {coast_km:.1f} km off the coast, where AIS reception is proven."
    ),
    "sar_dark_target_uncovered": (
        "{satellite} radar image of {acquired}: a {length_m:.0f} m target with no AIS, {coast_km:.1f} km off the "
        "coast, but no receiver is proven to hear AIS there."
    ),
    "ais_no_radar_return": (
        "Reported a near-certain position on open sea at {acquired} ({length_m:.0f} m long by its own AIS), but the "
        "{satellite} radar image shows no return there: possible false position."
    ),
}

# Propoziții opționale: se adaugă doar dacă detectorul a furnizat cheia respectivă în metrics.
OPTIONAL_TEMPLATES = {
    "acoustic_lowfreq": [("signature", " Signature: {signature_text}, dominant frequency {dominant_freq_hz:.0f} Hz.")],
    "sar_dark_target": [("nearest_ais_km", " Nearest AIS vessel: {nearest_ais_km:.1f} km.")],
    "sar_dark_target_uncovered": [("nearest_ais_km", " Nearest AIS vessel: {nearest_ais_km:.1f} km.")],
    "ais_no_radar_return": [("nearest_target_km", " Nearest radar target: {nearest_target_km:.1f} km.")],
}

GENERIC = "Event {code} (no dedicated template)."
SIMULATED_SUFFIX = " [SIMULATED]"
HEADER = "{name} (MMSI {mmsi}): risk {score}/100, level {level_text}."
HEADER_TARGET = "Unidentified radar target {target_id} (no AIS): risk {score}/100, level {level_text}."
VESSEL_LABEL = "{name}, MMSI {mmsi}"
TARGET_LABEL = "radar target {target_id}, no AIS"
RECOMMENDATION = "Recommendation: {unit_name}, ETA {eta_min:.0f} min ({distance_km:.1f} km)."
RECOMMENDATION_ON_SCENE = "Recommendation: {unit_name} is on scene."
UNKNOWN_VESSEL = "Unknown vessel"


def clock(t: datetime) -> str:
    return t.strftime("%H:%M UTC")


def label(code: str) -> str:
    return LABELS.get(code, code)


def factor_detail(code: str, values: dict, simulated: bool = False) -> str:
    v = dict(values)
    if "direction" in v:
        v["direction_text"] = DIRECTION_TEXT.get(v["direction"], v["direction"])
    if "signature" in v:
        v["signature_text"] = SIGNATURE_TEXT.get(v["signature"], v["signature"])
    try:
        text = TEMPLATES[code].format(**v)
    except (KeyError, ValueError, TypeError):
        text = GENERIC.format(code=code)
    for key, extra in OPTIONAL_TEMPLATES.get(code, []):
        if v.get(key) is not None:
            try:
                text += extra.format(**v)
            except (KeyError, ValueError, TypeError):
                pass
    return text + (SIMULATED_SUFFIX if simulated else "")


def vessel_label(name: str | None, mmsi: str | None, target_id: str | None = None) -> str:
    """Cum e numită o navă în explicații: nume și MMSI, sau ținta radar fără AIS."""
    if mmsi is None and target_id:
        return TARGET_LABEL.format(target_id=target_id)
    return VESSEL_LABEL.format(name=name or "unknown", mmsi=mmsi)


def alert_text(name: str | None, mmsi: str | None, score: int, level: str, details: list[str], rec: dict | None,
               target_id: str | None = None) -> str:
    if mmsi is None and target_id:
        head = HEADER_TARGET.format(target_id=target_id, score=score, level_text=LEVEL_TEXT[level])
    else:
        head = HEADER.format(name=name or UNKNOWN_VESSEL, mmsi=mmsi, score=score, level_text=LEVEL_TEXT[level])
    parts = [head]
    parts += [f"- {d}" for d in details]
    if rec:
        parts.append((RECOMMENDATION_ON_SCENE if rec["eta_min"] == 0 else RECOMMENDATION).format(**rec))
    return "\n".join(parts)
