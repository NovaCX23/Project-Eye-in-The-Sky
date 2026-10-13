"""Modul live: pipeline-ul pe AIS REAL înregistrat chiar acum (data.aisstream), pe ceasul real.

Rulare (patru terminale, din rădăcina repo-ului):
  python -m data.aisstream          # 1: înregistrează AIS real (zona live.area din config.yaml)
  python -m sar.process --watch     # 2: (opțional) procesează fiecare trecere Sentinel-1 nouă peste zonă
  python -m core.live               # 3: rescrie out/live/timeline.json la fiecare live.tick_s secunde
  python -m http.server 8000        # 4: http://localhost:8000/web/?mode=live (butonul "Live")

  python -m core.live --once                                   # un singur batch, apoi iese
  python -m core.live --at 2026-10-08T16:00:00Z --ais-dir DIR  # un batch la un moment trecut al unei înregistrări

Fără anomalii injectate: tot ce se vede e real, în afară de unitățile de patrulare (simulate).
"""

from __future__ import annotations

import argparse
import copy
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from contracts.models import Timeline
from contracts.runtime import OUT_DIR, iso, load_config, parse_time, utf8_stdout
from core import pipeline, sources
from core.sinks import write_timeline
from data.aisstream import active_area, area_dir
from sar.landmask import sea_polygon
from sar.store import area_dir as sar_area_dir
from data.recorded import anchorage_cells, coverage_boxes, coverage_cells
from detect.zones import LearnedZones

LIVE_OUT_DIR = OUT_DIR / "live"

MODE = "live"


class Live:
    """Starea modului live între batch-uri: zonele învățate, memoria alertelor, epoca unităților de patrulare."""

    def __init__(self, cfg: dict, ais_dir: Path, out_dir: Path, sar_dir: Path | None = None,
                 fetch_coast: bool = False):
        # Copie: epoca rutelor de patrulare (scenario.start) devine începutul primei ferestre, fără a atinge config-ul.
        self.cfg = copy.deepcopy(cfg)
        self.lc = cfg["live"]
        self.ais_dir, self.out_dir, self.sar_dir = ais_dir, out_dir, sar_dir
        area = active_area(cfg)
        # Zona rulată: infrastructura și unitățile de patrulare vin din assets/areas/<zonă>/ (contracts.assets).
        self.cfg["active_area"] = area
        self.area_name = cfg["areas"][area]["name"]
        self.bbox = cfg["areas"][area]["bbox"]
        self.coast_km = self._coast(area, fetch_coast)
        self.learned: LearnedZones | None = None
        self.learned_at: datetime | None = None
        self.state = pipeline.PipelineState()
        self.last_now: datetime | None = None

    def _coast(self, area: str, fetch: bool):
        """Distanța până la coastă pentru zona-tampon de port; cu `fetch`, linia de coastă OSM se descarcă o dată
        (sar/landmask, aceeași cache ca radarul)."""
        if self.sar_dir is None:
            return None
        if fetch and not (self.sar_dir / "sea.geojson").exists():
            try:
                sea_polygon(self.cfg, area, self.sar_dir)
            except (SystemExit, Exception) as e:   # Overpass ocupat: se continuă fără zona-tampon
                print(f"[core.live] no coastline yet, port buffer off ({e})", flush=True)
                return None
        return sources.coast_fn(self.sar_dir)

    def refresh_zones(self, now: datetime) -> None:
        if self.learned_at is not None and now - self.learned_at < timedelta(minutes=self.lc["zones_refresh_min"]):
            return
        hist = sources.history(self.ais_dir, now, self.cfg).ais
        self.learned = LearnedZones(
            bbox=self.bbox, coverage_cell_deg=self.lc["coverage_cell_deg"],
            anchorage_cell_deg=self.lc["anchorage_cell_deg"],
            coverage=frozenset(coverage_cells(hist, self.cfg)), anchorages=frozenset(anchorage_cells(hist, self.cfg)),
            coast_km=self.coast_km)
        self.learned_at = now

    def _prune(self, window_start: datetime) -> None:
        """Uită evenimentele încheiate de mult: în modul live starea ar crește la nesfârșit."""
        keep_after = window_start - timedelta(minutes=self.cfg["fusion"]["same_vessel_window_min"])
        self.state.events = {k: e for k, e in self.state.events.items() if e.end is None or e.end >= keep_after}

    def tick(self, now: datetime) -> Timeline | None:
        start = now - timedelta(minutes=self.lc["window_min"])
        inputs = sources.load_live(self.ais_dir, start - timedelta(minutes=self.lc["lookback_min"]), now, self.cfg,
                                   self.sar_dir)
        if inputs.ais.empty:
            print(f"[core.live] {iso(now)}: no AIS recorded in the last {self.lc['window_min']} min "
                  f"in {self.ais_dir}; is python -m data.aisstream running?", flush=True)
            return None
        self.refresh_zones(now)
        coverage = coverage_boxes(set(self.learned.coverage), self.lc["coverage_cell_deg"])
        kw = dict(learned=self.learned, window_start=start, area_name=self.area_name, coverage=coverage)
        if self.last_now is None:
            self.cfg["scenario"]["start"] = iso(start)
            # Încălzire: se rulează fereastra pas cu pas, ca alertele să aibă istoric (când a intrat fiecare factor).
            step = timedelta(minutes=self.cfg["pipeline"]["replay_step_min"])
            t = start + step
            while t < now:
                pipeline.run_batch(inputs, t, self.cfg, self.state, MODE, emit=False, **kw)
                t += step
        tl = pipeline.run_batch(inputs, now, self.cfg, self.state, MODE, **kw)
        self._prune(start)
        loaded = {r["pass_id"] for r in inputs.radar}
        self.state.radar = {k: v for k, v in self.state.radar.items() if k in loaded}
        write_timeline(tl, self.out_dir)
        self.last_now = now
        print(f"[core.live] {iso(now)} batch {tl.batch_index}: {len(tl.vessels)} tracks, {len(tl.events)} events, "
              f"{len(tl.alerts)} alerts, {len(self.learned.coverage)} covered cells", flush=True)
        return tl


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    cfg = load_config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true", help="one batch, then exit")
    ap.add_argument("--at", help="one batch at this past moment of the recording (ISO 8601); implies --once")
    ap.add_argument("--ais-dir", type=Path, default=None, help="recording folder (default: data/raw/ais/<area>)")
    ap.add_argument("--sar-dir", type=Path, default=None,
                    help="processed Sentinel-1 passes (default: data/raw/sar/<area>, written by python -m sar.process)")
    # Fișier separat de demo: core.demo / verify nu suprascriu modul live (și invers).
    ap.add_argument("--out-dir", type=Path, default=LIVE_OUT_DIR, help="default: out/live")
    args = ap.parse_args(argv)
    live = Live(cfg, args.ais_dir or area_dir(cfg), args.out_dir, args.sar_dir or sar_area_dir(cfg), fetch_coast=True)
    if args.at:
        return 0 if live.tick(parse_time(args.at)) else 1
    try:
        while True:
            t0 = time.monotonic()
            live.tick(datetime.now(timezone.utc).replace(microsecond=0))
            if args.once:
                return 0
            time.sleep(max(1.0, cfg["live"]["tick_s"] - (time.monotonic() - t0)))
    except KeyboardInterrupt:
        print("Stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
