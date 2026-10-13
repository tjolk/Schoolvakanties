"""Coordinator: haalt vakanties op, bewaart ze lokaal en ververst om middernacht."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import SchoolvakantiesApiError, async_haal_vakanties
from .const import (
    CONF_FEESTDAGEN,
    CONF_OPTIONELE_DAGEN,
    CONF_REGION,
    CONF_WEEKEND,
    DEFAULT_FEESTDAGEN,
    DEFAULT_WEEKEND,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
    UPDATE_INTERVAL,
)
from .kalender import Schoolkalender, Vakantie, filter_regio, relevante_schooljaren

_LOGGER = logging.getLogger(__name__)

type SchoolvakantiesConfigEntry = ConfigEntry[SchoolvakantiesCoordinator]


def instellingen(entry: ConfigEntry) -> dict[str, Any]:
    """Opties overschrijven de oorspronkelijke configuratie."""
    return {**entry.data, **entry.options}


class SchoolvakantiesCoordinator(DataUpdateCoordinator[Schoolkalender]):
    """Houdt de schoolkalender voor één regio bij."""

    config_entry: SchoolvakantiesConfigEntry

    def __init__(self, hass: HomeAssistant, entry: SchoolvakantiesConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        conf = instellingen(entry)
        self.regio: str = conf[CONF_REGION]
        self._feestdagen: bool = conf.get(CONF_FEESTDAGEN, DEFAULT_FEESTDAGEN)
        self._optioneel: tuple[str, ...] = tuple(conf.get(CONF_OPTIONELE_DAGEN, []))
        self._weekend: bool = conf.get(CONF_WEEKEND, DEFAULT_WEEKEND)
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._cache: list[Vakantie] | None = None
        self._unsub_middernacht: Any = None

    @property
    def vandaag(self) -> date:
        return dt_util.now().date()

    async def _async_setup(self) -> None:
        """Laad de laatst bekende vakanties, zodat alles werkt als de API even plat ligt."""
        opgeslagen = await self._store.async_load()
        if opgeslagen:
            try:
                self._cache = [Vakantie.uit_dict(v) for v in opgeslagen.get("vakanties", [])]
            except (KeyError, TypeError, ValueError):
                _LOGGER.warning("Opgeslagen vakanties zijn ongeldig en worden genegeerd")
        # Om middernacht opnieuw rekenen, want 'vandaag' en 'morgen' veranderen.
        self._unsub_middernacht = async_track_time_change(
            self.hass, self._middernacht, hour=0, minute=0, second=5
        )
        self.config_entry.async_on_unload(self._stop_middernacht)

    @callback
    def _stop_middernacht(self) -> None:
        if self._unsub_middernacht:
            self._unsub_middernacht()
            self._unsub_middernacht = None

    @callback
    def _middernacht(self, _now: Any) -> None:
        if self.data is not None:
            self.async_update_listeners()

    async def _async_update_data(self) -> Schoolkalender:
        session = async_get_clientsession(self.hass)
        try:
            alle = await async_haal_vakanties(session, relevante_schooljaren(self.vandaag))
        except SchoolvakantiesApiError as err:
            if self._cache is None:
                raise UpdateFailed(f"Schoolvakanties niet op te halen: {err}") from err
            _LOGGER.warning("API niet bereikbaar, laatst bekende vakanties worden gebruikt: %s", err)
            alle = self._cache
        else:
            if alle:
                self._cache = alle
                await self._store.async_save({"vakanties": [v.als_dict() for v in alle]})
            elif self._cache is not None:
                alle = self._cache

        return Schoolkalender(
            vakanties=filter_regio(alle, self.regio),
            feestdagen=self._feestdagen,
            optionele_dagen=self._optioneel,
            weekend_vrij=self._weekend,
        )
