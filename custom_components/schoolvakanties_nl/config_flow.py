"""Config flow: regio wordt voorgesteld op basis van de thuislocatie, gebruiker kan wijzigen."""

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

from .api import Locatie, async_reverse_geocode
from .const import (
    CONF_FEESTDAGEN,
    CONF_OPTIONELE_DAGEN,
    CONF_REGION,
    CONF_WEEKEND,
    DEFAULT_FEESTDAGEN,
    DEFAULT_WEEKEND,
    DOMAIN,
    NAME,
    REGIONS,
)
from .feestdagen import OPTIONELE_KEYS
from .regios import bepaal_regio

_LOGGER = logging.getLogger(__name__)


async def async_detecteer_regio(hass: HomeAssistant) -> tuple[str | None, Locatie | None]:
    """Bepaal de regio uit de thuislocatie van Home Assistant (alleen in Nederland)."""
    if hass.config.country not in (None, "NL"):
        return None, None
    lat, lon = hass.config.latitude, hass.config.longitude
    if lat is None or lon is None:
        return None, None
    locatie = await async_reverse_geocode(async_get_clientsession(hass), lat, lon)
    if locatie is None:
        return None, None
    # regios.json wordt van schijf gelezen: niet in de event loop.
    regio = await hass.async_add_executor_job(
        lambda: bepaal_regio(
            provincie=locatie.provincie, gemeente=locatie.gemeente, woonplaats=locatie.woonplaats
        )
    )
    return regio, locatie


def _schema(standaard: dict[str, Any]) -> vol.Schema:
    regio = standaard.get(CONF_REGION)
    return vol.Schema(
        {
            vol.Required(
                CONF_REGION, **({"default": regio} if regio else {})
            ): SelectSelector(
                SelectSelectorConfig(
                    options=REGIONS,
                    mode=SelectSelectorMode.LIST,
                    translation_key=CONF_REGION,
                )
            ),
            vol.Required(
                CONF_FEESTDAGEN, default=standaard.get(CONF_FEESTDAGEN, DEFAULT_FEESTDAGEN)
            ): BooleanSelector(),
            vol.Optional(
                CONF_OPTIONELE_DAGEN, default=list(standaard.get(CONF_OPTIONELE_DAGEN, []))
            ): SelectSelector(
                SelectSelectorConfig(
                    options=list(OPTIONELE_KEYS),
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                    translation_key=CONF_OPTIONELE_DAGEN,
                )
            ),
            vol.Required(
                CONF_WEEKEND, default=standaard.get(CONF_WEEKEND, DEFAULT_WEEKEND)
            ): BooleanSelector(),
        }
    )


class SchoolvakantiesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Instellen via de UI."""

    VERSION = 1

    def __init__(self) -> None:
        self._regio: str | None = None
        self._locatie: Locatie | None = None
        self._gedetecteerd = False

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title=NAME, data=user_input)

        if not self._gedetecteerd:
            self._regio, self._locatie = await async_detecteer_regio(self.hass)
            self._gedetecteerd = True
            _LOGGER.debug("Gedetecteerd: %s -> %s", self._locatie, self._regio)

        if self._regio and self._locatie:
            uitleg = f"{self._locatie.omschrijving} → regio {self._regio.capitalize()}"
        elif self._locatie:
            uitleg = f"{self._locatie.omschrijving} → regio niet automatisch te bepalen"
        else:
            uitleg = "Thuislocatie niet in Nederland of niet te bepalen"

        return self.async_show_form(
            step_id="user",
            data_schema=_schema({CONF_REGION: self._regio}),
            description_placeholders={"detectie": uitleg},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SchoolvakantiesOptionsFlow:
        return SchoolvakantiesOptionsFlow()


class SchoolvakantiesOptionsFlow(OptionsFlow):
    """Regio en vrije dagen achteraf wijzigen."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        huidig = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(huidig))
