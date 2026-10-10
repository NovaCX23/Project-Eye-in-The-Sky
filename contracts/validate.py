"""Validează un fișier JSON contra JSON Schema exportată (și contra modelului pydantic).

Rulare:  python -m contracts.validate out/timeline.json --model Timeline
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import jsonschema

from contracts.export_schema import schema_path
from contracts.models import ALL_MODELS
from contracts.runtime import read_json, utf8_stdout


def validate_data(data: object, model: str) -> list[str]:
    schema = json.loads(schema_path(model).read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = [f"{'/'.join(map(str, e.absolute_path))}: {e.message}" for e in validator.iter_errors(data)]
    if not errors:
        ALL_MODELS[model].model_validate(data)
    return errors


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path)
    ap.add_argument("--model", default="Timeline", choices=sorted(ALL_MODELS))
    args = ap.parse_args(argv)
    errors = validate_data(read_json(args.path), args.model)
    if errors:
        print(f"INVALID {args.path} ({args.model}):")
        for e in errors[:20]:
            print("  -", e)
        return 1
    print(f"OK {args.path} respectă schema {args.model}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
