"""Instalează dependențele și activează hook-urile git ale repo-ului.

Rulare:  python -m devtools.bootstrap            (echivalent: make setup)
         python -m devtools.bootstrap --hooks-only
Nu modifică user.name / user.email.
"""

from __future__ import annotations

import argparse
import os
import stat
import subprocess
import sys

from contracts.runtime import REPO_ROOT, utf8_stdout

HOOKS_DIR = ".githooks"


def install_requirements() -> None:
    subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-r",
                    str(REPO_ROOT / "requirements.txt")], check=True)


def activate_hooks() -> None:
    subprocess.run(["git", "config", "core.hooksPath", HOOKS_DIR], cwd=REPO_ROOT, check=True)
    if os.name != "nt":
        for hook in (REPO_ROOT / HOOKS_DIR).iterdir():
            hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Hook-uri git active: core.hooksPath = {HOOKS_DIR}")


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hooks-only", action="store_true")
    args = ap.parse_args(argv)
    if sys.prefix == sys.base_prefix:
        print("Atenție: nu rulați într-un mediu virtual. Recomandat: python -m venv .venv și activare.")
    if not args.hooks_only:
        install_requirements()
    activate_hooks()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
