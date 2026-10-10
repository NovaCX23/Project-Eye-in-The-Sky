"""Demo cap-coadă cu seed fix: generare trafic -> injectare scenariu -> acustic -> pipeline (replay).

Rulare:  python -m core.demo [--seed 42] [--out-dir out]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from contracts.runtime import OUT_DIR, load_config, utf8_stdout


def run(seed: int, out_dir: Path, quiet: bool = False) -> None:
    # Importuri locale: fiecare pas rămâne rulabil separat cu python -m <modul>.
    from acoustic import analyze
    from core import pipeline
    from data import generate, inject

    common = ["--out-dir", str(out_dir)]
    generate.main(["--seed", str(seed), *common])
    inject.main(["--seed", str(seed), *common])
    analyze.main(common)
    pipeline.main(["--in-dir", str(out_dir), *common, *(["--quiet"] if quiet else [])])


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    cfg = load_config()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=cfg["scenario"]["seeds"]["tuning"])
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args(argv)
    run(args.seed, args.out_dir)
    print("Gata. Porniți serverul: python -m http.server 8000  apoi deschideți http://localhost:8000/web/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
