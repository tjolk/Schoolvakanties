"""Gedeelde fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> None:
    """Laat Home Assistant custom_components/ laden in elke test."""


@pytest.fixture
def api_antwoord() -> dict[str, Any]:
    return json.loads((FIXTURES / "schooljaar_2026_2027.json").read_text(encoding="utf-8"))
