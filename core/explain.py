"""Explicații din șabloane, completate cu numerele detectorului. Fără LLM."""

from __future__ import annotations

LEVEL_RO = {"low": "scăzut", "medium": "mediu", "high": "ridicat", "critical": "critic"}
DIRECTION_RO = {"prea_lent": "prea lent", "prea_rapid": "prea rapid"}

LABELS = {
    "ais_gap": "Semnal AIS pierdut",
    "speed_inconsistency": "Viteză inconsistentă la reapariție",
    "loitering": "Staționare suspectă (loitering)",
    "position_jump": "Salt de poziție",
    "acoustic_lowfreq": "Semnătură acustică de joasă frecvență",
    "fibre_vibration": "Vibrație pe fibra cablului",
    "near_infrastructure": "Aproape de infrastructură critică",
    "correlated_vessel": "Corelare cu altă navă suspectă",
}

TEMPLATES = {
    "ais_gap": "AIS oprit de {gap_min:.0f} min (prag {threshold_min} min); ultima viteză raportată {last_sog_kn:.1f} kn.",
    "speed_inconsistency": (
        "La reapariție a parcurs {distance_km:.1f} km în {gap_min:.0f} min ({implied_kn:.1f} kn), deși raporta "
        "{reported_kn:.1f} kn (așteptat ~{expected_km:.0f} km): {direction_ro}."
    ),
    "loitering": (
        "Staționează de {duration_min:.0f} min cu viteză medie {mean_sog_kn:.1f} kn (prag {max_mean_sog_kn} kn), "
        "într-o zonă de {extent_km:.1f} km."
    ),
    "position_jump": (
        "Salt de poziție de {distance_km:.1f} km în {dt_min:.1f} min ({implied_kn:.0f} kn; "
        "maxim plauzibil {max_implied_kn:.0f} kn)."
    ),
    "acoustic_lowfreq": (
        "Hidrofonul {sensor_id} a detectat energie de joasă frecvență ({band_low_hz:.0f}–{band_high_hz:.0f} Hz, "
        "raport {lowfreq_ratio:.2f}, prag {ratio_threshold}) la {dist_km:.1f} km."
    ),
    "fibre_vibration": "Senzorul de fibră a semnalat vibrații la km {cable_km:.1f} al cablului, la {dist_km:.1f} km.",
    "near_infrastructure": "Poziția de referință e la {distance_km:.1f} km de {name}.",
    "correlated_vessel": "Altă navă suspectă ({other_name}, MMSI {other_mmsi}) în aceeași zonă, la {dist_km:.1f} km.",
}

GENERIC = "Eveniment {code} (fără șablon dedicat)."
SIMULATED_SUFFIX = " [SIMULAT]"
HEADER = "{name} (MMSI {mmsi}): risc {score}/100, nivel {level_ro}."
RECOMMENDATION = "Recomandare: {unit_name}, ETA {eta_min:.0f} min ({distance_km:.1f} km)."


def label(code: str) -> str:
    return LABELS.get(code, code)


def factor_detail(code: str, values: dict, simulated: bool = False) -> str:
    v = dict(values)
    if "direction" in v:
        v["direction_ro"] = DIRECTION_RO.get(v["direction"], v["direction"])
    try:
        text = TEMPLATES[code].format(**v)
    except (KeyError, ValueError, TypeError):
        text = GENERIC.format(code=code)
    return text + (SIMULATED_SUFFIX if simulated else "")


def alert_text(name: str | None, mmsi: str, score: int, level: str, details: list[str], rec: dict | None) -> str:
    parts = [HEADER.format(name=name or "Navă necunoscută", mmsi=mmsi, score=score, level_ro=LEVEL_RO[level])]
    parts += [f"- {d}" for d in details]
    if rec:
        parts.append(RECOMMENDATION.format(**rec))
    return "\n".join(parts)
