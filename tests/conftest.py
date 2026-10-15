"""Shared fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> None:
    """Let Home Assistant load custom_components/ in every test."""


@pytest.fixture
def api_response() -> dict[str, Any]:
    """A school holiday API response for school year 2026-2027 (sample data)."""
    return json.loads((FIXTURES / "schoolyear_2026_2027.json").read_text(encoding="utf-8"))
