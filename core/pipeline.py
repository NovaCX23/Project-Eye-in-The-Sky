"""Orchestrarea pipeline-ului micro-batch: intrări <= now -> reguli -> fuziune -> out/timeline.json.

Rulare:
  python -m core.pipeline                       # replay: now avansează pas cu pas până la final
  python -m core.pipeline --now 2026-03-15T08:30:00Z   # un singur batch
  python -m core.pipeline --watch               # micro-batch-uri la fiecare N secunde, ceas simulat
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from contracts.models import SensorEvent, Timeline, TrackPoint, VesselTrack
from contracts.runtime import OUT_DIR, iso, load_config, parse_time, utf8_stdout
from core import sources
from core.fusion import AlertMemory, build_alerts
from core.sinks import write_timeline
from detect import ais_rules


@dataclass
class PipelineState:
    # STUB: starea trăiește doar în memorie; la repornirea --watch se reconstruiește de la început.
    events: dict[str, SensorEvent] = field(default_factory=dict)
    memory: AlertMemory = field(default_factory=AlertMemory)
    batch_index: int = 0
    last_alerts: list = field(default_factory=list)


def _close_finished_gaps(state: PipelineState, ais: pd.DataFrame) -> None:
    """O gaură AIS rămasă deschisă se închide la primul mesaj de după ea."""
    for eid, e in list(state.events.items()):
        if e.event_type != "ais_gap" or e.end is not None:
            continue
        after = ais[(ais["mmsi"] == e.mmsi) & (ais["timestamp"] > pd.Timestamp(e.start))]
        if not after.empty:
            back = after["timestamp"].min().to_pydatetime()
            gap_min = round((back - e.start).total_seconds() / 60.0, 1)
            state.events[eid] = e.model_copy(update={"end": back, "metrics": {**e.metrics, "gap_min": gap_min}})


def _tracks(ais: pd.DataFrame, decimals: int) -> list[VesselTrack]:
    out = []
    for mmsi, g in ais.groupby("mmsi", sort=True):
        first = g.iloc[0]
        pts = [
            TrackPoint(t=t.to_pydatetime(), lat=round(la, decimals), lon=round(lo, decimals),
                       sog=None if pd.isna(s) else round(float(s), 1), cog=None if pd.isna(c) else round(float(c), 0))
            for t, la, lo, s, c in zip(g["timestamp"], g["lat"], g["lon"], g["sog_kn"], g["cog_deg"])
        ]
        out.append(VesselTrack(mmsi=mmsi, name=None if pd.isna(first["vessel_name"]) else first["vessel_name"],
                               ship_type=None if pd.isna(first["ship_type"]) else first["ship_type"],
                               simulated=bool(g["simulated"].any()), points=pts))
    return out


def run_batch(inputs: sources.Inputs, now: datetime, cfg: dict, state: PipelineState, mode: str,
              emit: bool = True) -> Timeline | None:
    """Un micro-batch. Cu emit=False actualizează doar starea (replay rapid, fără a construi pistele)."""
    view = sources.until(inputs, now)  # singurul loc prin care intră datele: nimic din viitor
    for e in ais_rules.run_all(view.ais, now, cfg) + view.sensors:
        state.events[e.event_id] = e
    _close_finished_gaps(state, view.ais)
    events = sorted(state.events.values(), key=lambda e: (e.start, e.event_id))
    names = (view.ais.dropna(subset=["vessel_name"]).groupby("mmsi")["vessel_name"].first().to_dict()
             if not view.ais.empty else {})
    alerts = build_alerts(events, now, cfg, names, state.memory)
    state.batch_index += 1
    state.last_alerts = alerts
    if not emit:
        return None
    tl = Timeline(
        mode=mode,
        batch_index=state.batch_index,
        scenario_start=parse_time(cfg["scenario"]["start"]),
        now=now,
        simulated=bool(view.ais["simulated"].any()) or any(e.simulated for e in events),
        reload_interval_s=cfg["web"]["reload_interval_s"],
        vessels=_tracks(view.ais, cfg["pipeline"]["coord_decimals"]),
        events=events,
        alerts=alerts,
    )
    return tl


def replay(in_dir: Path, out_dir: Path, cfg: dict, step_min: float | None = None, end: datetime | None = None,
           verbose: bool = True) -> Timeline:
    """Rulează micro-batch-urile pe ceasul simulat, cât de repede se poate (folosit de make demo)."""
    inputs = sources.load_all(in_dir)
    start = parse_time(cfg["scenario"]["start"])
    end = end or start + timedelta(minutes=cfg["scenario"]["duration_min"])
    step = timedelta(minutes=step_min or cfg["pipeline"]["replay_step_min"])
    state = PipelineState()
    now, tl, seen = start + step, None, set()
    while now <= end:
        last = now + step > end
        tl = run_batch(inputs, now, cfg, state, mode="replay", emit=last)
        for a in state.last_alerts:
            if a.alert_id not in seen:
                seen.add(a.alert_id)
                if verbose:
                    print(f"  [{iso(now)}] ALERTĂ {a.alert_id} {a.vessel_name} ({a.mmsi}) {a.alert_type} scor={a.risk_score}")
        now += step
    write_timeline(tl, out_dir)
    return tl


def watch(in_dir: Path, out_dir: Path, cfg: dict, interval_s: float, sim_step_min: float,
          max_ticks: int | None = None) -> None:
    """Micro-batch la fiecare interval_s secunde reale; `now` avansează cu sim_step_min pe ceasul simulat."""
    start = parse_time(cfg["scenario"]["start"])
    end = start + timedelta(minutes=cfg["scenario"]["duration_min"])
    state = PipelineState()
    now, ticks = start, 0
    print(f"[core.pipeline --watch] la fiecare {interval_s}s, +{sim_step_min} min simulate. Ctrl+C pentru oprire.")
    try:
        while now < end and (max_ticks is None or ticks < max_ticks):
            now = min(end, now + timedelta(minutes=sim_step_min))
            inputs = sources.load_all(in_dir)  # recitim fișierele: pot apărea date noi
            tl = run_batch(inputs, now, cfg, state, mode="watch")
            write_timeline(tl, out_dir)
            print(f"  batch {tl.batch_index:3d} now={iso(now)} nave={len(tl.vessels)} "
                  f"evenimente={len(tl.events)} alerte={len(tl.alerts)}")
            ticks += 1
            if now < end and (max_ticks is None or ticks < max_ticks):
                time.sleep(interval_s)
    except KeyboardInterrupt:
        print("Oprit.")


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    cfg = load_config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in-dir", type=Path, default=OUT_DIR, help="unde sunt ais.csv și evenimentele senzorilor")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--now", help="un singur batch la acest moment (ISO 8601)")
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--interval-s", type=float, default=cfg["pipeline"]["watch_interval_s"])
    ap.add_argument("--sim-step-min", type=float, default=cfg["pipeline"]["watch_sim_step_min"])
    ap.add_argument("--max-ticks", type=int, default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    if not (args.in_dir / "ais.csv").exists():
        print(f"Lipsește {args.in_dir / 'ais.csv'}. Rulați întâi: python -m core.demo")
        return 1
    if args.watch:
        watch(args.in_dir, args.out_dir, cfg, args.interval_s, args.sim_step_min, args.max_ticks)
        return 0
    if args.now:
        now = parse_time(args.now)
        tl = run_batch(sources.load_all(args.in_dir), now, cfg, PipelineState(), mode="single")
        write_timeline(tl, args.out_dir)
    else:
        t = time.perf_counter()
        tl = replay(args.in_dir, args.out_dir, cfg, verbose=not args.quiet)
        if not args.quiet:
            print(f"[core.pipeline] replay în {time.perf_counter() - t:.1f}s")
    print(f"[core.pipeline] now={iso(tl.now)}: {len(tl.vessels)} nave, {len(tl.events)} evenimente, "
          f"{len(tl.alerts)} alerte -> {args.out_dir / 'timeline.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
