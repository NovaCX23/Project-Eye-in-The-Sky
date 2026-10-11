"""AIS real: parsarea mesajelor aisstream, fișierele zilnice, încărcarea în formatul PositionMessage, hărțile învățate.

Fără rețea: mesajele sunt construite aici, în formatul documentat de aisstream.io.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from contracts.models import PositionMessage
from data.aisstream import POS_FIELDS, STATIC_FIELDS, DailyCsv, active_area, parse_message, secret
from data.recorded import anchorage_cells, coverage_cells, in_cells, load_recorded, recorded_range

T0 = datetime(2026, 10, 12, 4, 0, 0, tzinfo=timezone.utc)


def _pos_msg(mmsi: int, lat: float, lon: float, sog: float = 10.0, t: str = "2026-10-12 04:00:05.12 +0000 UTC",
             **extra) -> dict:
    body = {"UserID": mmsi, "Latitude": lat, "Longitude": lon, "Sog": sog, "Cog": 90.0, "TrueHeading": 511,
            "NavigationalStatus": 0, "Valid": True, **extra}
    return {"MessageType": "PositionReport", "MetaData": {"MMSI": mmsi, "time_utc": t},
            "Message": {"PositionReport": body}}


def test_parse_position_report_drops_not_available_values():
    kind, row = parse_message(_pos_msg(273000001, 43.2, 28.6, sog=102.3))
    assert kind == "pos"
    assert row["received_utc"] == "2026-10-12T04:00:05Z"
    assert row["sog_kn"] is None and row["heading_deg"] is None and row["cog_deg"] == 90.0


def test_parse_rejects_invalid_messages():
    assert parse_message(_pos_msg(1234, 43.2, 28.6)) is None                 # MMSI cu mai puțin de 9 cifre
    assert parse_message(_pos_msg(273000001, 95.0, 28.6)) is None            # latitudine imposibilă
    assert parse_message(_pos_msg(273000001, 43.2, 28.6, Valid=False)) is None
    assert parse_message({"MessageType": "Other", "MetaData": {}}) is None


def test_parse_static_report_sums_dimensions_and_cleans_text():
    msg = {"MessageType": "ShipStaticData",
           "MetaData": {"MMSI": 273000001, "time_utc": "2026-10-12 04:01:00 +0000 UTC"},
           "Message": {"ShipStaticData": {"Name": "SEA GULL@@@@", "Type": 70, "ImoNumber": 9000001,
                                          "CallSign": "LZAB@@", "Destination": "VARNA@@",
                                          "Dimension": {"A": 100, "B": 40, "C": 10, "D": 12}}}}
    kind, row = parse_message(msg)
    assert kind == "static"
    assert (row["name"], row["length_m"], row["width_m"], row["callsign"], row["destination"]) == \
        ("SEA GULL", 140, 22, "LZAB", "VARNA")


def _record(tmp_path, positions: list[dict], statics: list[dict]) -> None:
    pos, st = DailyCsv(tmp_path, "positions", POS_FIELDS), DailyCsv(tmp_path, "static", STATIC_FIELDS)
    for r in positions:
        pos.write(r)
    for r in statics:
        st.write(r)
    pos.close()
    st.close()


def _pos_row(mmsi: str, t: datetime, lat: float, lon: float, sog: float = 10.0) -> dict:
    return {"received_utc": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "mmsi": mmsi, "msg_type": "PositionReport",
            "lat": lat, "lon": lon, "sog_kn": sog, "cog_deg": 90.0, "heading_deg": None, "nav_status": 0}


def test_recorded_ais_loads_as_position_messages(tmp_path, cfg):
    # Două zile (fișierele se schimbă la miezul nopții UTC), o stație de bază (MMSI 00...) ignorată, un duplicat.
    late = datetime(2026, 10, 11, 23, 59, 0, tzinfo=timezone.utc)
    rows = [_pos_row("273000001", late + timedelta(minutes=m), 43.2, 28.6 + m * 0.001) for m in range(3)]
    rows += [rows[0], _pos_row("002730001", late, 43.0, 28.0)]
    static = [{"received_utc": "2026-10-11T20:00:00Z", "mmsi": "273000001", "msg_type": "ShipStaticData",
               "name": "SEA GULL", "ship_type_code": 80, "length_m": 140, "width_m": 22, "imo": None,
               "callsign": None, "destination": None}]
    _record(tmp_path, rows, static)
    assert sorted(p.name for p in tmp_path.glob("positions-*.csv")) == ["positions-20261011.csv",
                                                                        "positions-20261012.csv"]
    df = load_recorded(late - timedelta(hours=1), late + timedelta(hours=1), tmp_path,
                       cfg["live"]["static_days_before"])
    assert list(df["mmsi"].unique()) == ["273000001"] and len(df) == 3
    assert (df["vessel_name"] == "SEA GULL").all() and (df["ship_type"] == "tanker").all()
    assert not df["simulated"].any()
    for rec in df.to_dict("records"):
        PositionMessage.model_validate({k: (None if pd.isna(v) else v) for k, v in rec.items()})
    first, last = recorded_range(tmp_path)
    assert first == late and last == late + timedelta(minutes=2)


def test_recorded_range_is_none_without_recordings(tmp_path):
    assert recorded_range(tmp_path) is None


def test_coverage_needs_messages_from_several_vessels(cfg):
    c = cfg["live"]
    n = c["coverage_min_messages"]
    one = pd.DataFrame({"mmsi": ["273000001"] * n, "lat": [43.21] * n, "lon": [28.61] * n, "sog_kn": [9.0] * n})
    assert coverage_cells(one, cfg) == set()
    two = pd.concat([one, one.assign(mmsi="273000002")], ignore_index=True)
    cells = coverage_cells(two, cfg)
    assert in_cells(43.21, 28.61, cells, c["coverage_cell_deg"])
    assert not in_cells(43.5, 28.9, cells, c["coverage_cell_deg"])


def test_anchorage_needs_several_still_vessels(cfg):
    c = cfg["live"]
    k = c["anchorage_min_vessels"]
    still = pd.DataFrame({"mmsi": [f"27300000{i}" for i in range(k)], "lat": [43.19] * k, "lon": [27.95] * k,
                          "sog_kn": [0.1] * k})
    assert in_cells(43.19, 27.95, anchorage_cells(still, cfg), c["anchorage_cell_deg"])
    assert anchorage_cells(still.assign(sog_kn=8.0), cfg) == set()
    assert anchorage_cells(still.iloc[: k - 1], cfg) == set()


def test_area_override_and_secret_from_env_file(tmp_path, cfg, monkeypatch):
    monkeypatch.setenv("SEAGRID_AREA", "constanta")
    assert active_area(cfg) == "constanta"
    monkeypatch.delenv("AISSTREAM_TEST_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text("# comment\nAISSTREAM_TEST_KEY = \"abc123\"\n", encoding="utf-8")
    assert secret("AISSTREAM_TEST_KEY", env) == "abc123"
    assert secret("AISSTREAM_TEST_KEY", tmp_path / "missing.env") is None
