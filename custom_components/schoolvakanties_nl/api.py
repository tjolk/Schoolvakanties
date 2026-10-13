"""Clients voor de schoolvakantie-API (Rijksoverheid) en de PDOK Locatieserver."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp

from .const import PDOK_LOOKUP_URL, PDOK_REVERSE_URL, REQUEST_TIMEOUT, SCHOOLVAKANTIES_URL
from .kalender import Vakantie, parse_vakanties

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)


class SchoolvakantiesApiError(Exception):
    """De schoolvakantie-API is niet bereikbaar of gaf onbruikbare data."""


async def async_haal_vakanties(
    session: aiohttp.ClientSession, schooljaren: list[str]
) -> list[Vakantie]:
    """Haal vakanties (alle regio's) op voor de opgegeven schooljaren.

    Een schooljaar dat nog niet gepubliceerd is (404 of leeg) wordt overgeslagen.
    Faalt elk schooljaar, dan volgt SchoolvakantiesApiError.
    """
    resultaten = await asyncio.gather(
        *(_haal_schooljaar(session, jaar) for jaar in schooljaren), return_exceptions=True
    )
    vakanties: set[Vakantie] = set()
    fouten: list[BaseException] = []
    for jaar, resultaat in zip(schooljaren, resultaten, strict=True):
        if isinstance(resultaat, BaseException):
            _LOGGER.debug("Schooljaar %s niet opgehaald: %s", jaar, resultaat)
            fouten.append(resultaat)
            continue
        vakanties.update(resultaat)
    if fouten and len(fouten) == len(schooljaren):
        raise SchoolvakantiesApiError(f"Geen enkel schooljaar opgehaald: {fouten[0]}") from fouten[0]
    return sorted(vakanties)


async def _haal_schooljaar(session: aiohttp.ClientSession, jaar: str) -> list[Vakantie]:
    url = SCHOOLVAKANTIES_URL.format(schooljaar=jaar)
    async with session.get(url, params={"output": "json"}, timeout=_TIMEOUT) as resp:
        if resp.status == 404:
            return []
        resp.raise_for_status()
        data: Any = await resp.json(content_type=None)
    return parse_vakanties(data)


@dataclass(frozen=True)
class Locatie:
    """Resultaat van reverse geocoding via PDOK."""

    woonplaats: str | None
    gemeente: str | None
    provincie: str | None

    @property
    def omschrijving(self) -> str:
        delen = [self.woonplaats]
        if self.gemeente and self.gemeente != self.woonplaats:
            delen.append(f"gemeente {self.gemeente}")
        if self.provincie:
            delen.append(self.provincie)
        return ", ".join(d for d in delen if d)


async def async_reverse_geocode(
    session: aiohttp.ClientSession, latitude: float, longitude: float
) -> Locatie | None:
    """Zoek woonplaats, gemeente en provincie bij coördinaten. None als het niet lukt."""
    try:
        doc = await _pdok_reverse(session, latitude, longitude)
        if doc and not doc.get("gemeentenaam") and doc.get("id"):
            doc = await _pdok_lookup(session, doc["id"]) or doc
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        _LOGGER.debug("PDOK reverse geocoding mislukt: %s", err)
        return None
    if not doc or not (doc.get("gemeentenaam") or doc.get("provincienaam")):
        return None
    return Locatie(
        woonplaats=doc.get("woonplaatsnaam"),
        gemeente=doc.get("gemeentenaam"),
        provincie=doc.get("provincienaam"),
    )


async def _pdok_reverse(
    session: aiohttp.ClientSession, latitude: float, longitude: float
) -> dict[str, Any] | None:
    # Eerst het dichtstbijzijnde adres; ligt de thuislocatie ver van een adres,
    # dan de woonplaats (die heeft ook gemeente en provincie).
    for soort in ("adres", "woonplaats"):
        params = {"lat": latitude, "lon": longitude, "type": soort, "rows": 1, "fl": "*"}
        async with session.get(PDOK_REVERSE_URL, params=params, timeout=_TIMEOUT) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
        docs = (data.get("response") or {}).get("docs") or []
        if docs:
            return docs[0]
    return None


async def _pdok_lookup(session: aiohttp.ClientSession, object_id: str) -> dict[str, Any] | None:
    async with session.get(PDOK_LOOKUP_URL, params={"id": object_id}, timeout=_TIMEOUT) as resp:
        resp.raise_for_status()
        data = await resp.json(content_type=None)
    docs = (data.get("response") or {}).get("docs") or []
    return docs[0] if docs else None
