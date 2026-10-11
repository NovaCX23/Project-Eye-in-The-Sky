"""Înregistrator AIS REAL: mesajele aisstream.io din zona activă (config.yaml live.area) -> fișiere CSV zilnice.

Rulare (se lasă pornit; se reconectează singur):
  python -m data.aisstream
  python -m data.aisstream --minutes 5      # un test scurt

Cheia: AISSTREAM_API_KEY în mediu sau în .env (gratuit: https://aisstream.io, autentificare, "API Keys").
Produce, în data/raw/ais/<zonă>/ (nu se comite):
  positions-YYYYMMDD.csv   un rând pe raport de poziție (clasa A și B)
  static-YYYYMMDD.csv      un rând pe raport static/de voiaj (nume, tip, dimensiuni)
  recorder_status.json     contoare, ultimul mesaj, starea conexiunii
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from contracts.runtime import REPO_ROOT, iso, load_config, utf8_stdout, write_json_atomic

RAW_AIS_DIR = REPO_ROOT / "data" / "raw" / "ais"
ENV_PATH = REPO_ROOT / ".env"
AREA_ENV = "SEAGRID_AREA"
KEY_NAME = "AISSTREAM_API_KEY"

POS_FIELDS = ["received_utc", "mmsi", "msg_type", "lat", "lon", "sog_kn", "cog_deg", "heading_deg", "nav_status"]
STATIC_FIELDS = ["received_utc", "mmsi", "msg_type", "name", "ship_type_code", "length_m", "width_m",
                 "imo", "callsign", "destination"]
POSITION_TYPES = ("PositionReport", "StandardClassBPositionReport", "ExtendedClassBPositionReport")
STATIC_TYPES = ("ShipStaticData", "StaticDataReport")

# Valori care înseamnă "indisponibil" în standardul AIS (ITU-R M.1371).
SOG_NA = 102.3
COG_NA = 360.0
HEADING_NA = 511


def active_area(cfg: dict) -> str:
    """Id-ul zonei live active (SEAGRID_AREA are prioritate față de config.yaml)."""
    area = os.environ.get(AREA_ENV) or cfg["live"]["area"]
    if area not in cfg["areas"]:
        raise SystemExit(f"Unknown area {area!r}; config.yaml defines: {', '.join(cfg['areas'])}")
    return area


def area_dir(cfg: dict) -> Path:
    return RAW_AIS_DIR / active_area(cfg)


def secret(name: str, env_path: Path = ENV_PATH) -> str | None:
    """Citește un secret din mediu sau din .env. Nu se tipărește și nu se scrie niciodată în out/."""
    if os.environ.get(name):
        return os.environ[name].strip()
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == name and v.strip():
                return v.strip().strip('"').strip("'")
    return None


def _parse_time(meta_time: str) -> datetime:
    # Format aisstream: "2026-10-10 18:22:32.318353 +0000 UTC" (numărul de zecimale variază)
    s = meta_time.replace(" UTC", "").strip()
    date, clock, _tz = s.split(" ")
    if "." in clock:
        head, frac = clock.split(".")
        clock = f"{head}.{(frac + '000000')[:6]}"
    return datetime.fromisoformat(f"{date}T{clock}").replace(tzinfo=timezone.utc)


def _num(v, na: float | None = None) -> float | None:
    if v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if na is not None and x >= na:
        return None
    return x


def _text(v) -> str | None:
    return (v or "").replace("@", "").strip() or None


def parse_message(msg: dict) -> tuple[str, dict] | None:
    """Un mesaj JSON aisstream -> ("pos" | "static", rând) sau None dacă nu e utilizabil."""
    mtype = msg.get("MessageType")
    meta = msg.get("MetaData") or {}
    body = (msg.get("Message") or {}).get(mtype) or {}
    mmsi = str(meta.get("MMSI") or body.get("UserID") or "")
    if not mmsi.isdigit() or len(mmsi) != 9 or "time_utc" not in meta:
        return None
    t = iso(_parse_time(meta["time_utc"]))
    if mtype in POSITION_TYPES:
        lat, lon = _num(body.get("Latitude")), _num(body.get("Longitude"))
        if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None
        if body.get("Valid") is False:
            return None
        heading = body.get("TrueHeading")
        return "pos", {
            "received_utc": t, "mmsi": mmsi, "msg_type": mtype, "lat": round(lat, 6), "lon": round(lon, 6),
            "sog_kn": _num(body.get("Sog"), SOG_NA), "cog_deg": _num(body.get("Cog"), COG_NA),
            "heading_deg": None if heading is None or heading >= HEADING_NA else heading,
            "nav_status": body.get("NavigationalStatus"),
        }
    if mtype in STATIC_TYPES:
        imo = callsign = dest = None
        if mtype == "StaticDataReport":
            # Clasa B trimite numele (partea A) și tipul/dimensiunile (partea B) în mesaje separate.
            a, b = body.get("ReportA") or {}, body.get("ReportB") or {}
            name = a.get("Name") if a.get("Valid") else None
            stype = b.get("ShipType") if b.get("Valid") else None
            dim = b.get("Dimension") if b.get("Valid") else None
            if b.get("Valid"):
                callsign = b.get("CallSign")
        else:
            name, stype, dim = body.get("Name"), body.get("Type"), body.get("Dimension")
            imo, callsign, dest = body.get("ImoNumber"), body.get("CallSign"), body.get("Destination")
        length = width = None
        if dim:
            length = (dim.get("A") or 0) + (dim.get("B") or 0) or None
            width = (dim.get("C") or 0) + (dim.get("D") or 0) or None
        name = _text(name)
        if not any([name, stype, length]):
            return None
        return "static", {
            "received_utc": t, "mmsi": mmsi, "msg_type": mtype, "name": name, "ship_type_code": stype,
            "length_m": length, "width_m": width, "imo": imo or None,
            "callsign": _text(callsign), "destination": _text(dest),
        }
    return None


class DailyCsv:
    """Adaugă rânduri în <prefix>-YYYYMMDD.csv și trece la fișierul zilei următoare la miezul nopții UTC."""

    def __init__(self, out_dir: Path, prefix: str, fields: list[str]):
        self.out_dir, self.prefix, self.fields = out_dir, prefix, fields
        self.day, self.fh, self.writer = None, None, None

    def write(self, row: dict) -> None:
        day = row["received_utc"][:10].replace("-", "")
        if day != self.day:
            self.close()
            path = self.out_dir / f"{self.prefix}-{day}.csv"
            new = not path.exists()
            self.fh = open(path, "a", newline="", encoding="utf-8")
            self.writer = csv.DictWriter(self.fh, fieldnames=self.fields)
            if new:
                self.writer.writeheader()
            self.day = day
        self.writer.writerow(row)

    def flush(self) -> None:
        if self.fh:
            self.fh.flush()

    def close(self) -> None:
        if self.fh:
            self.fh.close()
        self.fh = None


async def record(cfg: dict, key: str, minutes: float | None, out_dir: Path) -> int:
    import websockets  # import local: restul modulului data/ nu are nevoie de el

    c = cfg["live"]
    bb = cfg["areas"][active_area(cfg)]["bbox"]
    out_dir.mkdir(parents=True, exist_ok=True)
    pos = DailyCsv(out_dir, "positions", POS_FIELDS)
    static = DailyCsv(out_dir, "static", STATIC_FIELDS)
    status = {"area": active_area(cfg), "started": iso(datetime.now(timezone.utc)), "positions": 0, "static": 0,
              "connections": 0, "last_message": None, "state": "connecting", "error": None}
    status_path = out_dir / "recorder_status.json"
    deadline = time.monotonic() + minutes * 60 if minutes else None
    sub = {
        "APIKey": key,
        "BoundingBoxes": [[[bb["lat_min"], bb["lon_min"]], [bb["lat_max"], bb["lon_max"]]]],
        "FilterMessageTypes": list(POSITION_TYPES + STATIC_TYPES),
    }
    backoff = c["reconnect_min_s"]
    last_flush = time.monotonic()
    mmsis: set[str] = set()
    empty_connections = 0  # conexiuni închise înainte de primul mesaj: de obicei cheie respinsă
    while deadline is None or time.monotonic() < deadline:
        got_data = False
        try:
            async with websockets.connect(c["stream_url"], ping_interval=20, ping_timeout=30,
                                          max_size=2 ** 20) as ws:
                await ws.send(json.dumps(sub))
                status.update(connections=status["connections"] + 1, state="connected", error=None)
                write_json_atomic(status_path, status)
                print(f"[data.aisstream] connected; area {status['area']}, bbox {bb}", flush=True)
                while deadline is None or time.monotonic() < deadline:
                    left = c["idle_timeout_s"] if deadline is None else deadline - time.monotonic()
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=max(1.0, min(c["idle_timeout_s"], left)))
                    except asyncio.TimeoutError:
                        if deadline is not None and time.monotonic() >= deadline:
                            break
                        raise ConnectionError(f"no message for {c['idle_timeout_s']} s")
                    msg = json.loads(raw)
                    if not got_data:
                        got_data, empty_connections, backoff = True, 0, c["reconnect_min_s"]
                    if "error" in msg:
                        # aisstream trimite {"error": "..."} pentru cheie sau abonament greșit, apoi închide.
                        raise PermissionError(str(msg["error"]))
                    parsed = parse_message(msg)
                    if parsed is None:
                        continue
                    kind, row = parsed
                    if kind == "pos":
                        pos.write(row)
                        status["positions"] += 1
                        mmsis.add(row["mmsi"])
                    else:
                        static.write(row)
                        status["static"] += 1
                    status["last_message"] = row["received_utc"]
                    if time.monotonic() - last_flush >= c["flush_every_s"]:
                        pos.flush()
                        static.flush()
                        status["vessels_seen"] = len(mmsis)
                        write_json_atomic(status_path, status)
                        print(f"[data.aisstream] {status['positions']} positions, {status['static']} static, "
                              f"{len(mmsis)} vessels, last {status['last_message']}", flush=True)
                        last_flush = time.monotonic()
        except PermissionError as e:
            status.update(state="rejected", error=str(e))
            write_json_atomic(status_path, status)
            print(f"[data.aisstream] aisstream rejected the subscription: {e}", flush=True)
            pos.close()
            static.close()
            return 2
        except Exception as e:  # erori de rețea: reconectare cu backoff
            if not got_data:
                empty_connections += 1
            hint = (" (aisstream closes the connection without a message when the API key is wrong: check .env)"
                    if empty_connections >= 3 else "")
            status.update(state="reconnecting", error=f"{type(e).__name__}: {e}{hint}")
            write_json_atomic(status_path, status)
            print(f"[data.aisstream] connection lost ({type(e).__name__}: {e}){hint}; retry in {backoff} s",
                  flush=True)
            pos.flush()
            static.flush()
            await asyncio.sleep(backoff)
            backoff = min(c["reconnect_max_s"], backoff * 2)
    pos.close()
    static.close()
    status.update(state="stopped", vessels_seen=len(mmsis))
    write_json_atomic(status_path, status)
    print(f"[data.aisstream] stopped: {status['positions']} positions from {len(mmsis)} vessels -> {out_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--minutes", type=float, default=None, help="stop after N minutes (default: run forever)")
    args = ap.parse_args(argv)
    cfg = load_config()
    key = secret(KEY_NAME)
    if not key:
        print(f"Missing {KEY_NAME}. Put it in .env (see .env.example) or set it in the environment.")
        return 1
    try:
        return asyncio.run(record(cfg, key, args.minutes, area_dir(cfg)))
    except KeyboardInterrupt:
        print("Stopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
