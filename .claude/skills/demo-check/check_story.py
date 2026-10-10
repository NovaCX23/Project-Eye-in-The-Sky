"""Verifică fiecare moment al poveștii demo în out/timeline.json, la timpul așteptat.

Rulare (din rădăcina repo-ului):  python .claude/skills/demo-check/check_story.py [--no-regen]
Termenele vin din secțiunea `expected` a data/scenarios/demo.yaml (minute de la scenario.start).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def t(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-regen", action="store_true", help="do not regenerate; check the existing out/timeline.json")
    args = ap.parse_args()
    if not args.no_regen:
        if subprocess.run([sys.executable, "-m", "core.demo"], cwd=ROOT).returncode != 0:
            print("core.demo failed")
            return 1
    sc = yaml.safe_load((ROOT / "data/scenarios/demo.yaml").read_text(encoding="utf-8"))
    tl = json.loads((ROOT / "out/timeline.json").read_text(encoding="utf-8"))
    exp = sc["expected"]
    t0 = t(tl["scenario_start"])
    at = lambda m: t0 + timedelta(minutes=m)  # noqa: E731
    mins = lambda d: f"T+{(d - t0).total_seconds() / 60:.0f} min ({d.strftime('%H:%M')})"  # noqa: E731
    dark, loit = sc["dark_vessel"]["mmsi"], sc["loiter_vessel"]["mmsi"]
    dark_alert = next((a for a in tl["alerts"] if a["mmsi"] == dark), None)
    loit_alert = next((a for a in tl["alerts"] if a["mmsi"] == loit), None)
    beats = []

    def beat(name: str, when: datetime | None, deadline: datetime | None, extra: str = "") -> None:
        ok = when is not None and (deadline is None or when <= deadline)
        beats.append(ok)
        lim = f" (deadline {mins(deadline)})" if deadline else ""
        print(f"[{'OK ' if ok else 'ERR'}] {name}: {mins(when) if when else 'missing'}{lim} {extra}")

    gap = next((e for e in tl["events"] if e["mmsi"] == dark and e["event_type"] == "ais_gap"), None)
    beat("vessel goes dark (last AIS message)", t(gap["start"]) if gap else None,
         at(sc["dark_vessel"]["gap_start_min"]))
    beat("alert for the dark vessel", t(dark_alert["created_at"]) if dark_alert else None, at(exp["dark_alert_by_min"]))
    beat("second vessel loiters (loitering alert)", t(loit_alert["created_at"]) if loit_alert else None,
         at(exp["loiter_alert_by_min"]))
    ac = next((e for e in tl["events"] if e["event_type"] == "acoustic_lowfreq"), None)
    beat("acoustic event", t(ac["start"]) if ac else None, at(exp["acoustic_event_min"] + 5),
         "SIMULATED" if ac and ac["simulated"] else "")
    fb = [e for e in tl["events"] if e["event_type"] == "fibre_vibration" and t(e["start"]) >= at(exp["fibre_event_min"])]
    beat("fibre event", t(fb[0]["start"]) if fb else None, at(exp["fibre_event_min"] + 5),
         "SIMULATED" if fb and fb[0]["simulated"] else "")
    crit = next((h for h in (dark_alert or {}).get("history", []) if h["level"] == "critical"), None)
    beat("score reaches critical", t(crit["t"]) if crit else None, at(exp["critical_by_min"]),
         f"score {crit['score']}" if crit else "")
    rec = next((h for h in (dark_alert or {}).get("history", []) if h.get("unit_id")), None)
    beat("patrol unit recommended", t(rec["t"]) if rec else None, at(exp["critical_by_min"]),
         f"{rec['unit_id']} ETA {rec['eta_min']:.0f} min" if rec else "")
    si = next((f for f in (dark_alert or {}).get("factors", []) if f["code"] == "speed_inconsistency"), None)
    beat("reappearance inconsistent with speed", t(si["added_at"]) if si else None, None, si["detail"] if si else "")
    ok = all(beats)
    print("\nDEMO-CHECK: " + ("every story beat is in place." if ok else "story beats are missing."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
