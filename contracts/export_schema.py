"""Exportă JSON Schema pentru fiecare model în contracts/schema/.

Rulare:  python -m contracts.export_schema          (scrie fișierele)
         python -m contracts.export_schema --check  (eșuează dacă schema e depășită)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from contracts.models import ALL_MODELS

SCHEMA_DIR = Path(__file__).resolve().parent / "schema"
EXAMPLES_DIR = Path(__file__).resolve().parent / "examples"


def schema_text(name: str) -> str:
    schema = ALL_MODELS[name].model_json_schema(mode="serialization")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = f"seagrid/{name}.schema.json"
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def schema_path(name: str) -> Path:
    return SCHEMA_DIR / f"{name}.schema.json"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="doar verifică, nu scrie")
    args = ap.parse_args(argv)
    stale = []
    SCHEMA_DIR.mkdir(exist_ok=True)
    for name in ALL_MODELS:
        text = schema_text(name)
        p = schema_path(name)
        current = p.read_text(encoding="utf-8") if p.exists() else None
        if current != text:
            stale.append(p.name)
            if not args.check:
                p.write_text(text, encoding="utf-8", newline="\n")
    if args.check and stale:
        print("Schema depășită, rulați python -m contracts.export_schema:", ", ".join(stale))
        return 1
    print("Schema actualizată:" if stale else "Schema la zi.", ", ".join(stale))
    return 0


if __name__ == "__main__":
    sys.exit(main())
