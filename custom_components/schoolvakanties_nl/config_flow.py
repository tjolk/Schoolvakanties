"""Config flow: the region is suggested from the home location; the user can change it."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import Location, async_reverse_geocode
from .const import (
    CONF_EXTRA_DAYS_OFF,
    CONF_PUBLIC_HOLIDAYS,
    CONF_REGION,
    CONF_WEEKEND,
    DEFAULT_PUBLIC_HOLIDAYS,
    DEFAULT_WEEKEND,
    DOMAIN,
    NAME,
    REGIONS,
)
from .public_holidays import OPTIONAL_KEYS
from .regions import resolve_region

_LOGGER = logging.getLogger(__name__)


async def async_detect_region(hass: HomeAssistant) -> tuple[str | None, Location | None]:
    """Determine the region from the Home Assistant home location (Netherlands only)."""
    if hass.config.country not in (None, "NL"):
        return None, None
    latitude, longitude = hass.config.latitude, hass.config.longitude
    if latitude is None or longitude is None:
        return None, None
    location = await async_reverse_geocode(async_get_clientsession(hass), latitude, longitude)
    if location is None:
        return None, None
    # regions.json is read from disk: keep that out of the event loop.
    region = await hass.async_add_executor_job(
        lambda: resolve_region(
            province=location.province,
            municipality=location.municipality,
            town=location.town,
        )
    )
    return region, location


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    region = defaults.get(CONF_REGION)
    return vol.Schema(
        {
            vol.Required(CONF_REGION, **({"default": region} if region else {})): SelectSelector(
                SelectSelectorConfig(
                    options=REGIONS,
                    mode=SelectSelectorMode.LIST,
                    translation_key=CONF_REGION,
                )
            ),
            vol.Required(
                CONF_PUBLIC_HOLIDAYS,
                default=defaults.get(CONF_PUBLIC_HOLIDAYS, DEFAULT_PUBLIC_HOLIDAYS),
            ): BooleanSelector(),
            vol.Optional(
                CONF_EXTRA_DAYS_OFF, default=list(defaults.get(CONF_EXTRA_DAYS_OFF, []))
            ): SelectSelector(
                SelectSelectorConfig(
                    options=list(OPTIONAL_KEYS),
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                    translation_key=CONF_EXTRA_DAYS_OFF,
                )
            ),
            vol.Required(
                CONF_WEEKEND, default=defaults.get(CONF_WEEKEND, DEFAULT_WEEKEND)
            ): BooleanSelector(),
        }
    )


class SchoolvakantiesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up the integration from the UI."""

    VERSION = 1

    def __init__(self) -> None:
        self._region: str | None = None
        self._location: Location | None = None
        self._detected = False

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title=NAME, data=user_input)

        if not self._detected:
            self._region, self._location = await async_detect_region(self.hass)
            self._detected = True
            _LOGGER.debug("Detected: %s -> %s", self._location, self._region)

        # Place names are Dutch; the surrounding text comes from the translations.
        if self._location:
            region_label = self._region.capitalize() if self._region else "?"
            detected = f"{self._location.description} → {region_label}"
        else:
            detected = "—"

        return self.async_show_form(
            step_id="user",
            data_schema=_schema({CONF_REGION: self._region}),
            description_placeholders={"detected": detected},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SchoolvakantiesOptionsFlow:
        return SchoolvakantiesOptionsFlow()


class SchoolvakantiesOptionsFlow(OptionsFlow):
    """Change the region and days off afterwards."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(current))
