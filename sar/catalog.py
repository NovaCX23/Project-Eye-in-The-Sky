"""Trecerile Sentinel-1 peste zona activă, din catalogul STAC Microsoft Planetary Computer (fără cont).

O "trecere" = un survol al satelitului: feliile GRD cu aceeași platformă și aceeași orbită absolută.

  python -m sar.catalog                      # trecerile din ultimele 14 zile
  python -m sar.catalog --days 30
  python -m sar.catalog --upcoming 7         # trecerile prezise (ciclu de 12 zile per satelit)
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from shapely.geometry import box, shape

from contracts.runtime import active_area, iso, load_config, parse_time, utf8_stdout

REPEAT_DAYS = 12   # ciclul de repetiție al orbitei Sentinel-1, per satelit
DEFAULT_DAYS = 14


@dataclass
class Pass:
    pass_id: str
    platform: str
    absolute_orbit: int
    relative_orbit: int | None
    orbit_state: str
    acquired_at: datetime          # mijlocul feliei care acoperă cea mai mare parte din zonă
    available_at: datetime         # cel mai târziu moment de procesare ESA dintre felii (de atunci se știe)
    area_coverage: float
    items: list = field(default_factory=list)


def area_bbox(cfg: dict) -> dict:
    return cfg["areas"][active_area(cfg)]["bbox"]


def _area_box(cfg: dict):
    b = area_bbox(cfg)
    return box(b["lon_min"], b["lat_min"], b["lon_max"], b["lat_max"])


def client(cfg: dict):
    # Importuri locale: catalogul (rețea) e opțional pentru restul pipeline-ului și pentru teste.
    import planetary_computer
    import pystac_client

    return pystac_client.Client.open(cfg["sar"]["stac_url"], modifier=planetary_computer.sign_inplace)


def pass_id_of(platform: str, acquired: datetime, orbit: int) -> str:
    return f"{platform.upper().replace('SENTINEL-', 'S')}_{acquired.strftime('%Y%m%dT%H%M%S')}_{orbit}"


def find_passes(cfg: dict, start: datetime, end: datetime) -> list[Pass]:
    """Trecerile IW cu polarizare VV care acoperă cel puțin sar.min_area_coverage din zonă, în ordine cronologică."""
    area = _area_box(cfg)
    search = client(cfg).search(collections=[cfg["sar"]["collection"]], intersects=area.__geo_interface__,
                                datetime=f"{iso(start)}/{iso(end)}", limit=100)
    groups: dict[tuple, list] = {}
    for it in search.items():
        p = it.properties
        if p.get("sar:instrument_mode") != "IW" or "VV" not in p.get("sar:polarizations", []):
            continue
        groups.setdefault((p["platform"], p["sat:absolute_orbit"]), []).append(it)
    out = []
    for (platform, orbit), items in groups.items():
        cover = area.intersection(shape(items[0].geometry))
        for it in items[1:]:
            cover = cover.union(area.intersection(shape(it.geometry)))
        frac = cover.area / area.area
        if frac < cfg["sar"]["min_area_coverage"]:
            continue
        main = max(items, key=lambda it: area.intersection(shape(it.geometry)).area)
        mp = main.properties
        acquired = parse_time(mp["datetime"])
        available = max(parse_time(it.properties.get("s1:processing_datetime") or it.properties["datetime"])
                        for it in items)
        out.append(Pass(pass_id=pass_id_of(platform, acquired, orbit), platform=platform, absolute_orbit=orbit,
                        relative_orbit=mp.get("sat:relative_orbit"), orbit_state=mp.get("sat:orbit_state", "?"),
                        acquired_at=acquired, available_at=available, area_coverage=round(frac, 3),
                        items=sorted(items, key=lambda it: it.properties["datetime"])))
    return sorted(out, key=lambda p: p.acquired_at)


def predict_upcoming(passes: list[Pass], now: datetime, days: int) -> list[tuple[datetime, str, str, int | None]]:
    """Trecerile următoare: fiecare (platformă, orbită relativă) revine la 12 zile, la aceeași oră."""
    latest: dict[tuple, Pass] = {}
    for p in passes:
        k = (p.platform, p.relative_orbit)
        if k not in latest or p.acquired_at > latest[k].acquired_at:
            latest[k] = p
    out = []
    for p in latest.values():
        t = p.acquired_at
        while t <= now:
            t += timedelta(days=REPEAT_DAYS)
        while t <= now + timedelta(days=days):
            out.append((t, p.platform, p.orbit_state, p.relative_orbit))
            t += timedelta(days=REPEAT_DAYS)
    return sorted(out)


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=float, default=DEFAULT_DAYS)
    ap.add_argument("--upcoming", type=int, default=None, help="predict passes in the next N days")
    args = ap.parse_args(argv)
    cfg = load_config()
    now = datetime.now(timezone.utc)
    print(f"[sar.catalog] area {active_area(cfg)}")
    if args.upcoming:
        seen = find_passes(cfg, now - timedelta(days=REPEAT_DAYS + 2), now)
        for t, platform, state, rel in predict_upcoming(seen, now, args.upcoming):
            print(f"{iso(t)}  {platform:12s} {state:10s} relative orbit {rel}  (predicted)")
        return 0
    for p in find_passes(cfg, now - timedelta(days=args.days), now):
        print(f"{p.pass_id:32s} acquired {iso(p.acquired_at)}  published {iso(p.available_at)}  "
              f"{p.orbit_state:10s} area {p.area_coverage:.0%}  slices {len(p.items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
