"""Fixture-uri partajate de teste (rădăcina repo-ului)."""

from __future__ import annotations

from pathlib import Path

import pytest

from contracts.runtime import load_config


@pytest.fixture(scope="session")
def cfg() -> dict:
    return load_config()


@pytest.fixture(scope="session")
def demo_out(tmp_path_factory, cfg) -> Path:
    """Rulează o dată demo-ul complet (seed de tuning) într-un director temporar."""
    from core import demo

    out = tmp_path_factory.mktemp("demo_out")
    demo.run(cfg["scenario"]["seeds"]["tuning"], out, quiet=True)
    return out
