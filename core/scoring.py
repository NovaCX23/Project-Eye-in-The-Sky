"""Scor aditiv: suma punctelor factorilor (din config.yaml), plafonată la score.max."""

from __future__ import annotations


def points_for(code: str, cfg: dict) -> int:
    pts = cfg["score"]["points"]
    if code not in pts:
        raise KeyError(f"Missing score.points.{code} in config.yaml (see the add-rule skill)")
    return int(pts[code])


def total(points: list[int], cfg: dict) -> int:
    return int(min(cfg["score"]["max"], max(0, sum(points))))


def level_for(score: int, cfg: dict) -> str:
    levels = sorted(cfg["score"]["levels"].items(), key=lambda kv: kv[1])
    current = levels[0][0]
    for name, threshold in levels:
        if score >= threshold:
            current = name
    return current
