"""Verificarea de dinaintea unui commit: teste, demo, schemă, alerta scenariului.

Rulare (din rădăcina repo-ului):  python .claude/skills/verify/verify.py [--skip-tests]
Ieșire 0 = totul OK.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def step(name: str, *args: str) -> bool:
    print(f"\n=== {name}: python {' '.join(args)}", flush=True)
    ok = subprocess.run([sys.executable, *args], cwd=ROOT).returncode == 0
    print(f"=== {name}: {'OK' if ok else 'FAILED'}", flush=True)
    return ok


def scenario_alert_present() -> bool:
    sc = yaml.safe_load((ROOT / "data/scenarios/demo.yaml").read_text(encoding="utf-8"))
    tl = json.loads((ROOT / "out/timeline.json").read_text(encoding="utf-8"))
    mmsi = sc["dark_vessel"]["mmsi"]
    alerts = [a for a in tl["alerts"] if a["mmsi"] == mmsi]
    ok = len(alerts) == 1 and any(f["code"] == "ais_gap" for f in alerts[0]["factors"])
    print(f"\n=== scenario alert ({mmsi}): {'OK' if ok else 'MISSING or DUPLICATED'}")
    if ok:
        a = alerts[0]
        print(f"    {a['alert_id']} score={a['risk_score']} level={a['level']} created={a['created_at']}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-tests", action="store_true")
    args = ap.parse_args()
    results = []
    if not args.skip_tests:
        results.append(step("tests", "-m", "pytest"))
    results.append(step("demo", "-m", "core.demo"))
    results.append(step("schema", "-m", "contracts.validate", "out/timeline.json", "--model", "Timeline"))
    results.append(scenario_alert_present())
    ok = all(results)
    print("\nVERIFY: " + ("OK, safe to commit." if ok else "FAILED, do not commit."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
