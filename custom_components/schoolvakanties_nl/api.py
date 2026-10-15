"""Clients for the school holiday API (Rijksoverheid) and the PDOK Locatieserver."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp

from .const import PDOK_LOOKUP_URL, PDOK_REVERSE_URL, REQUEST_TIMEOUT, SCHOOL_HOLIDAYS_URL
from .school_calendar import SchoolHoliday, parse_holidays

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)


class SchoolHolidayApiError(Exception):
    """The school holiday API is unreachable or returned unusable data."""


async def async_fetch_holidays(
    session: aiohttp.ClientSession, school_years: list[str]
) -> list[SchoolHoliday]:
    """Fetch holidays (all regions) for the given school years.

    A school year that has not been published yet (404 or empty) is skipped.
    If every school year fails, SchoolHolidayApiError is raised.
    """
    results = await asyncio.gather(
        *(_fetch_school_year(session, year) for year in school_years), return_exceptions=True
    )
    holidays: set[SchoolHoliday] = set()
    errors: list[BaseException] = []
    for year, result in zip(school_years, results, strict=True):
        if isinstance(result, BaseException):
            _LOGGER.debug("Could not fetch school year %s: %s", year, result)
            errors.append(result)
            continue
        holidays.update(result)
    if errors and len(errors) == len(school_years):
        raise SchoolHolidayApiError(f"No school year could be fetched: {errors[0]}") from errors[0]
    return sorted(holidays)


async def _fetch_school_year(session: aiohttp.ClientSession, year: str) -> list[SchoolHoliday]:
    url = SCHOOL_HOLIDAYS_URL.format(school_year=year)
    async with session.get(url, params={"output": "json"}, timeout=_TIMEOUT) as resp:
        if resp.status == 404:
            return []
        resp.raise_for_status()
        data: Any = await resp.json(content_type=None)
    return parse_holidays(data)


@dataclass(frozen=True)
class Location:
    """Result of reverse geocoding via PDOK."""

    town: str | None
    municipality: str | None
    province: str | None

    @property
    def description(self) -> str:
        parts = [self.town]
        if self.municipality and self.municipality != self.town:
            parts.append(self.municipality)
        parts.append(self.province)
        return ", ".join(p for p in parts if p)


async def async_reverse_geocode(
    session: aiohttp.ClientSession, latitude: float, longitude: float
) -> Location | None:
    """Look up town, municipality and province for coordinates. None if that fails."""
    try:
        doc = await _pdok_reverse(session, latitude, longitude)
        if doc and not doc.get("gemeentenaam") and doc.get("id"):
            doc = await _pdok_lookup(session, doc["id"]) or doc
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        _LOGGER.debug("PDOK reverse geocoding failed: %s", err)
        return None
    if not doc or not (doc.get("gemeentenaam") or doc.get("provincienaam")):
        return None
    return Location(
        town=doc.get("woonplaatsnaam"),
        municipality=doc.get("gemeentenaam"),
        province=doc.get("provincienaam"),
    )


async def _pdok_reverse(
    session: aiohttp.ClientSession, latitude: float, longitude: float
) -> dict[str, Any] | None:
    # First the nearest address; if the home location is far from any address,
    # fall back to the town (which also has municipality and province).
    for object_type in ("adres", "woonplaats"):
        params = {"lat": latitude, "lon": longitude, "type": object_type, "rows": 1, "fl": "*"}
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
