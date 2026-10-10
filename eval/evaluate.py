"""Compară alertele din timeline.json cu ground_truth.json și tipărește tabelul de metrici.

Rulare:
  python -m eval.evaluate                                # evaluează out/ (după make demo)
  python -m eval.evaluate --seed-set tuning --run        # regenerează pe seed-ul de reglare
  python -m eval.evaluate --seed-set both --run --write-md pitch/metrics.md
Seed-ul "reporting" e held-out: NU se reglează pragurile pe el.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from contracts.runtime import OUT_DIR, load_config, parse_time, read_json, utf8_stdout


@dataclass
class Metrics:
    label: str
    seed: int | str
    n_anomalies: int
    n_detected: int
    n_alerts: int
    n_false: int
    n_normal_vessels: int
    hours: float
    mean_tta_min: float | None
    per_type: dict[str, tuple[int, int]]
    missed: list[str]

    @property
    def detection_rate(self) -> float:
        return self.n_detected / self.n_anomalies if self.n_anomalies else 0.0

    @property
    def false_alarm_rate(self) -> float:
        """Alarme false raportate la numărul de nave normale."""
        return self.n_false / self.n_normal_vessels if self.n_normal_vessels else 0.0


def evaluate(out_dir: Path, cfg: dict, label: str = "out") -> Metrics:
    # STUB: potrivire doar pe MMSI + fereastră de timp; formatul oficial de evaluare e încă necunoscut.
    gt = read_json(out_dir / "ground_truth.json")
    tl = read_json(out_dir / "timeline.json")
    grace = timedelta(minutes=cfg["eval"]["match_grace_min"])
    alerts = [dict(a, _created=parse_time(a["created_at"])) for a in tl["alerts"]]
    matched_alerts: set[str] = set()
    ttas, per_type, missed = [], {}, []
    for an in gt["anomalies"]:
        start, end = parse_time(an["start"]), parse_time(an["end"])
        hits = sorted((a for a in alerts if a["mmsi"] == an["mmsi"] and start <= a["_created"] <= end + grace),
                      key=lambda a: a["_created"])
        det, tot = per_type.get(an["type"], (0, 0))
        per_type[an["type"]] = (det + (1 if hits else 0), tot + 1)
        if hits:
            ttas.append((hits[0]["_created"] - start).total_seconds() / 60.0)
            matched_alerts.update(a["alert_id"] for a in hits)
        else:
            missed.append(f"{an['type']} {an['mmsi']} @ {an['start']}")
    n_false = sum(1 for a in alerts if a["alert_id"] not in matched_alerts)
    hours = (parse_time(tl["now"]) - parse_time(tl["scenario_start"])).total_seconds() / 3600.0
    return Metrics(
        label=label, seed=gt.get("seed", "?"), n_anomalies=len(gt["anomalies"]), n_detected=len(ttas),
        n_alerts=len(alerts), n_false=n_false, n_normal_vessels=len(gt.get("normal_mmsis", [])), hours=hours,
        mean_tta_min=sum(ttas) / len(ttas) if ttas else None, per_type=per_type, missed=missed,
    )


def table(rows: list[Metrics]) -> str:
    head = ("| Set | Seed | Anomalies | Detected | Detection rate | Alerts | False alarms | "
            "FA / normal vessel | Mean TTA (min) |")
    sep = "|---|---|---|---|---|---|---|---|---|"
    lines = [head, sep]
    for m in rows:
        tta = f"{m.mean_tta_min:.1f}" if m.mean_tta_min is not None else "–"
        lines.append(f"| {m.label} | {m.seed} | {m.n_anomalies} | {m.n_detected} | {m.detection_rate:.0%} | "
                     f"{m.n_alerts} | {m.n_false} | {m.false_alarm_rate:.2f} | {tta} |")
    lines.append("")
    lines.append("| Set | Anomaly type | Detected / total |")
    lines.append("|---|---|---|")
    for m in rows:
        for t, (d, n) in sorted(m.per_type.items()):
            lines.append(f"| {m.label} | {t} | {d} / {n} |")
    for m in rows:
        for miss in m.missed:
            lines.append(f"\nMISSED ({m.label}): {miss}")
    return "\n".join(lines)


def run_seed(seed: int, out_dir: Path) -> None:
    from core import demo  # import local: evaluarea simplă nu are nevoie de pipeline

    demo.run(seed, out_dir, quiet=True)


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    cfg = load_config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--seed-set", choices=["tuning", "reporting", "both"], default=None)
    ap.add_argument("--run", action="store_true", help="regenerate the data and run the pipeline for the seed")
    ap.add_argument("--write-md", type=Path, default=None, help="write the reporting-set table to this file")
    args = ap.parse_args(argv)

    if args.seed_set is None:
        rows = [evaluate(args.out_dir, cfg)]
    else:
        sets = ["tuning", "reporting"] if args.seed_set == "both" else [args.seed_set]
        rows = []
        for name in sets:
            d = args.out_dir / "eval" / name
            if args.run or not (d / "timeline.json").exists():
                run_seed(cfg["scenario"]["seeds"][name], d)
            rows.append(evaluate(d, cfg, label=name))
    text = table(rows)
    print(text)
    if args.write_md:
        rep = [r for r in rows if r.label == "reporting"]
        if not rep:
            print("--write-md needs the reporting set (use --seed-set both or reporting).")
            return 1
        args.write_md.parent.mkdir(parents=True, exist_ok=True)
        args.write_md.write_text(
            "# SeaGrid metrics (held-out seed, SIMULATED data)\n\n"
            f"Generated by `python -m eval.evaluate --seed-set both --run --write-md {args.write_md.as_posix()}`.\n"
            "Thresholds were tuned ONLY on the tuning seed.\n\n" + table(rep) + "\n",
            encoding="utf-8", newline="\n",
        )
        print(f"\nWrote {args.write_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
