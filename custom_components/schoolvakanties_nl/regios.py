"""Bepaal de schoolvakantieregio op basis van provincie, gemeente en woonplaats.

De indeling staat in data/regios.json, zodat je hem kunt bijwerken zonder code
te wijzigen. Dit bestand gebruikt geen Home Assistant-imports.
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import cache
from pathlib import Path
from typing import Any

REGIOS_BESTAND = Path(__file__).parent / "data" / "regios.json"


def normaliseer(naam: str | None) -> str:
    """Maak namen vergelijkbaar: 'Fryslân' -> 'fryslan', 'Oost-Gelre' -> 'oostgelre'."""
    if not naam:
        return ""
    zonder_accenten = (
        unicodedata.normalize("NFKD", naam).encode("ascii", "ignore").decode("ascii")
    )
    return re.sub(r"[^a-z0-9]", "", zonder_accenten.lower())


@cache
def _laad_indeling() -> tuple[dict[str, str | None], dict[str, Any]]:
    data = json.loads(REGIOS_BESTAND.read_text(encoding="utf-8"))
    provincies = {normaliseer(k): v for k, v in data["provincies"].items()}
    gemeenten: dict[str, Any] = {}
    for naam, waarde in data["gemeenten"].items():
        if isinstance(waarde, dict):
            waarde = {
                "regio": waarde["regio"],
                "woonplaatsen": {
                    normaliseer(w): r for w, r in waarde.get("woonplaatsen", {}).items()
                },
            }
        gemeenten[normaliseer(naam)] = waarde
    return provincies, gemeenten


def bepaal_regio(
    *,
    provincie: str | None = None,
    gemeente: str | None = None,
    woonplaats: str | None = None,
) -> str | None:
    """Geef 'noord', 'midden' of 'zuid', of None als het niet te bepalen is."""
    provincies, gemeenten = _laad_indeling()

    regel = gemeenten.get(normaliseer(gemeente))
    if isinstance(regel, dict):
        return regel["woonplaatsen"].get(normaliseer(woonplaats), regel["regio"])
    if isinstance(regel, str):
        return regel

    return provincies.get(normaliseer(provincie))
