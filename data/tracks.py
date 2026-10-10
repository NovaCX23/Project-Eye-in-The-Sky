"""Simulare de traiectorii: navigare pe waypoints, staționare, loitering.

Toate deplasările folosesc geometria sferică din contracts.geo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from contracts.geo import destination, haversine_km, initial_bearing_deg, kn_to_kmh


@dataclass
class TruePoint:
    t: datetime
    lat: float
    lon: float
    sog: float
    cog: float


def sail(
    waypoints: list[tuple[float, float]],
    speeds_kn: list[float],
    t0: datetime,
    t_end: datetime,
    interval_s: int,
) -> list[TruePoint]:
    """Navă care urmează waypoints cu viteză constantă pe fiecare tronson, apoi stă pe loc."""
    assert len(speeds_kn) == len(waypoints) - 1
    lat, lon = waypoints[0]
    leg = 0
    cog = initial_bearing_deg(*waypoints[0], *waypoints[1]) if len(waypoints) > 1 else 0.0
    out: list[TruePoint] = []
    t = t0
    dt_h = interval_s / 3600.0
    while t <= t_end:
        moving = leg < len(waypoints) - 1
        out.append(TruePoint(t, lat, lon, speeds_kn[leg] if moving else 0.0, cog))
        remaining = kn_to_kmh(speeds_kn[leg]) * dt_h if moving else 0.0
        while remaining > 0 and leg < len(waypoints) - 1:
            nxt = waypoints[leg + 1]
            d = haversine_km(lat, lon, *nxt)
            if d <= remaining:
                lat, lon = nxt
                remaining -= d
                leg += 1
                if leg < len(waypoints) - 1:
                    cog = initial_bearing_deg(lat, lon, *waypoints[leg + 1])
            else:
                cog = initial_bearing_deg(lat, lon, *nxt)
                lat, lon = destination(lat, lon, cog, remaining)
                remaining = 0.0
        t += timedelta(seconds=interval_s)
    return out


def travel_minutes(waypoints: list[tuple[float, float]], speeds_kn: list[float]) -> float:
    return sum(
        haversine_km(*a, *b) / kn_to_kmh(s) * 60.0 for a, b, s in zip(waypoints, waypoints[1:], speeds_kn)
    )


def loiter(
    center: tuple[float, float],
    t0: datetime,
    t_end: datetime,
    interval_s: int,
    sog_kn: float,
    radius_km: float,
    rng: np.random.Generator,
) -> list[TruePoint]:
    """Mers lent, în cerc larg, în jurul unui punct."""
    out: list[TruePoint] = []
    theta = float(rng.uniform(0, 360))
    t = t0
    step_deg = np.degrees(kn_to_kmh(sog_kn) * interval_s / 3600.0 / max(radius_km, 1e-6))
    while t <= t_end:
        lat, lon = destination(*center, theta, radius_km)
        sog = max(0.0, float(rng.normal(sog_kn, sog_kn * 0.3)))
        out.append(TruePoint(t, lat, lon, sog, (theta + 90.0) % 360.0))
        theta = (theta + step_deg) % 360.0
        t += timedelta(seconds=interval_s)
    return out


def anchored(
    pos: tuple[float, float], t0: datetime, t_end: datetime, interval_s: int, max_sog_kn: float, rng: np.random.Generator
) -> list[TruePoint]:
    out: list[TruePoint] = []
    t = t0
    heading = float(rng.uniform(0, 360))
    while t <= t_end:
        heading = (heading + float(rng.normal(0, 3))) % 360.0
        out.append(TruePoint(t, pos[0], pos[1], float(rng.uniform(0, max_sog_kn)), heading))
        t += timedelta(seconds=interval_s)
    return out


def to_rows(
    track: list[TruePoint],
    mmsi: str,
    name: str,
    ship_type: str,
    rng: np.random.Generator,
    gen_cfg: dict,
    dropouts: bool,
    t_min: datetime | None = None,
) -> list[dict]:
    """Adaugă zgomot GPS și pauze scurte normale; produce rânduri PositionMessage."""
    rows = []
    skip_until: datetime | None = None
    for p in track:
        if t_min is not None and p.t < t_min:
            continue
        if skip_until is not None and p.t < skip_until:
            continue
        if dropouts and rng.random() < gen_cfg["dropout_probability"]:
            skip_until = p.t + timedelta(seconds=float(rng.uniform(gen_cfg["dropout_min_s"], gen_cfg["dropout_max_s"])))
            continue
        noise_km = abs(float(rng.normal(0, gen_cfg["position_noise_km"])))
        lat, lon = destination(p.lat, p.lon, float(rng.uniform(0, 360)), noise_km)
        sog = max(0.0, p.sog + float(rng.normal(0, gen_cfg["sog_noise_kn"]))) if p.sog > 0 else p.sog
        cog = (p.cog + float(rng.normal(0, gen_cfg["cog_noise_deg"]))) % 360.0
        rows.append(
            {
                "mmsi": mmsi,
                "timestamp": p.t,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "sog_kn": round(sog, 2),
                "cog_deg": round(cog, 1) % 360.0,
                "heading_deg": round(cog, 1) % 360.0,
                "vessel_name": name,
                "ship_type": ship_type,
                "source": "ais",
                "simulated": True,
            }
        )
    return rows
