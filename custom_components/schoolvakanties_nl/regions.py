"""Determine the school holiday region from province, municipality and town.

The mapping lives in data/regions.json, so it can be updated without changing
code. This module has no Home Assistant imports.
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import cache
from pathlib import Path
from typing import Any

REGIONS_FILE = Path(__file__).parent / "data" / "regions.json"


def normalize(name: str | None) -> str:
    """Make names comparable: 'Fryslân' -> 'fryslan', 'Oost-Gelre' -> 'oostgelre'."""
    if not name:
        return ""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", ascii_name.lower())


@cache
def _load_mapping() -> tuple[dict[str, str | None], dict[str, Any]]:
    data = json.loads(REGIONS_FILE.read_text(encoding="utf-8"))
    provinces = {normalize(k): v for k, v in data["provinces"].items()}
    municipalities: dict[str, Any] = {}
    for name, value in data["municipalities"].items():
        if isinstance(value, dict):
            value = {
                "region": value["region"],
                "towns": {normalize(t): r for t, r in value.get("towns", {}).items()},
            }
        municipalities[normalize(name)] = value
    return provinces, municipalities


def resolve_region(
    *,
    province: str | None = None,
    municipality: str | None = None,
    town: str | None = None,
) -> str | None:
    """Return 'noord', 'midden' or 'zuid', or None if it cannot be determined.

    Note: this reads the JSON file on first use; call it from an executor in
    Home Assistant to avoid blocking the event loop.
    """
    provinces, municipalities = _load_mapping()

    rule = municipalities.get(normalize(municipality))
    if isinstance(rule, dict):
        return rule["towns"].get(normalize(town), rule["region"])
    if isinstance(rule, str):
        return rule

    return provinces.get(normalize(province))
