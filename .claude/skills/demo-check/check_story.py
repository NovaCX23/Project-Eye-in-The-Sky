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
    ap.add_argument("--no-regen", action="store_true", help="nu regenera; verifică out/timeline.json existent")
    args = ap.parse_args()
    if not args.no_regen:
        if subprocess.run([sys.executable, "-m", "core.demo"], cwd=ROOT).returncode != 0:
            print("core.demo a eșuat")
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
        lim = f" (termen {mins(deadline)})" if deadline else ""
        print(f"[{'OK ' if ok else 'ERR'}] {name}: {mins(when) if when else 'lipsește'}{lim} {extra}")

    gap = next((e for e in tl["events"] if e["mmsi"] == dark and e["event_type"] == "ais_gap"), None)
    beat("nava se stinge (ultimul mesaj AIS)", t(gap["start"]) if gap else None,
         at(sc["dark_vessel"]["gap_start_min"]))
    beat("alertă pentru nava stinsă", t(dark_alert["created_at"]) if dark_alert else None, at(exp["dark_alert_by_min"]))
    beat("a doua navă staționează (alertă loitering)", t(loit_alert["created_at"]) if loit_alert else None,
         at(exp["loiter_alert_by_min"]))
    ac = next((e for e in tl["events"] if e["event_type"] == "acoustic_lowfreq"), None)
    beat("eveniment acustic", t(ac["start"]) if ac else None, at(exp["acoustic_event_min"] + 5),
         "SIMULAT" if ac and ac["simulated"] else "")
    fb = [e for e in tl["events"] if e["event_type"] == "fibre_vibration" and t(e["start"]) >= at(exp["fibre_event_min"])]
    beat("eveniment fibră", t(fb[0]["start"]) if fb else None, at(exp["fibre_event_min"] + 5),
         "SIMULAT" if fb and fb[0]["simulated"] else "")
    crit = next((h for h in (dark_alert or {}).get("history", []) if h["level"] == "critical"), None)
    beat("scorul ajunge la critic", t(crit["t"]) if crit else None, at(exp["critical_by_min"]),
         f"scor {crit['score']}" if crit else "")
    rec = next((h for h in (dark_alert or {}).get("history", []) if h.get("unit_id")), None)
    beat("unitate recomandată", t(rec["t"]) if rec else None, at(exp["critical_by_min"]),
         f"{rec['unit_id']} ETA {rec['eta_min']:.0f} min" if rec else "")
    si = next((f for f in (dark_alert or {}).get("factors", []) if f["code"] == "speed_inconsistency"), None)
    beat("reapariție inconsistentă cu viteza", t(si["added_at"]) if si else None, None, si["detail"] if si else "")
    ok = all(beats)
    print("\nDEMO-CHECK: " + ("toate momentele sunt la locul lor." if ok else "lipsesc momente din poveste."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
