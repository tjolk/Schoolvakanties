"""Coordinator: fetches holidays, stores them locally and refreshes at midnight."""

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

from .api import SchoolHolidayApiError, async_fetch_holidays
from .const import (
    CONF_EXTRA_DAYS_OFF,
    CONF_PUBLIC_HOLIDAYS,
    CONF_REGION,
    CONF_WEEKEND,
    DEFAULT_PUBLIC_HOLIDAYS,
    DEFAULT_WEEKEND,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
    UPDATE_INTERVAL,
)
from .school_calendar import SchoolCalendar, SchoolHoliday, filter_region, relevant_school_years

_LOGGER = logging.getLogger(__name__)

type SchoolvakantiesConfigEntry = ConfigEntry[SchoolvakantiesCoordinator]


def entry_settings(entry: ConfigEntry) -> dict[str, Any]:
    """Options override the original configuration."""
    return {**entry.data, **entry.options}


class SchoolvakantiesCoordinator(DataUpdateCoordinator[SchoolCalendar]):
    """Keeps the school calendar for one region up to date."""

    config_entry: SchoolvakantiesConfigEntry

    def __init__(self, hass: HomeAssistant, entry: SchoolvakantiesConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        settings = entry_settings(entry)
        self.region: str = settings[CONF_REGION]
        self._public_holidays: bool = settings.get(CONF_PUBLIC_HOLIDAYS, DEFAULT_PUBLIC_HOLIDAYS)
        self._optional_days_off: tuple[str, ...] = tuple(settings.get(CONF_EXTRA_DAYS_OFF, []))
        self._weekend_off: bool = settings.get(CONF_WEEKEND, DEFAULT_WEEKEND)
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._cache: list[SchoolHoliday] | None = None
        self._unsub_midnight: Any = None

    @property
    def today(self) -> date:
        return dt_util.now().date()

    async def _async_setup(self) -> None:
        """Load the last known holidays, so everything keeps working if the API is down."""
        stored = await self._store.async_load()
        if stored:
            try:
                self._cache = [SchoolHoliday.from_dict(h) for h in stored.get("holidays", [])]
            except (KeyError, TypeError, ValueError):
                _LOGGER.warning("Stored holidays are invalid and will be ignored")
        # Recalculate at midnight, because 'today' and 'tomorrow' change.
        self._unsub_midnight = async_track_time_change(
            self.hass, self._at_midnight, hour=0, minute=0, second=5
        )
        self.config_entry.async_on_unload(self._stop_midnight_listener)

    @callback
    def _stop_midnight_listener(self) -> None:
        if self._unsub_midnight:
            self._unsub_midnight()
            self._unsub_midnight = None

    @callback
    def _at_midnight(self, _now: Any) -> None:
        if self.data is not None:
            self.async_update_listeners()

    async def _async_update_data(self) -> SchoolCalendar:
        session = async_get_clientsession(self.hass)
        try:
            holidays = await async_fetch_holidays(session, relevant_school_years(self.today))
        except SchoolHolidayApiError as err:
            if self._cache is None:
                raise UpdateFailed(f"Could not fetch school holidays: {err}") from err
            _LOGGER.warning("API unavailable, using the last known holidays: %s", err)
            holidays = self._cache
        else:
            if holidays:
                self._cache = holidays
                await self._store.async_save({"holidays": [h.as_dict() for h in holidays]})
            elif self._cache is not None:
                holidays = self._cache

        return SchoolCalendar(
            holidays=filter_region(holidays, self.region),
            public_holidays=self._public_holidays,
            optional_days_off=self._optional_days_off,
            weekend_off=self._weekend_off,
        )
