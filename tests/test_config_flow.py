"""Config flow: suggest the region from the home location."""

from __future__ import annotations

from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.schoolvakanties_nl.const import (
    CONF_EXTRA_DAYS_OFF,
    CONF_PUBLIC_HOLIDAYS,
    CONF_REGION,
    CONF_WEEKEND,
    DOMAIN,
    PDOK_REVERSE_URL,
)
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

PDOK_DIDAM = {
    "response": {
        "numFound": 1,
        "docs": [
            {
                "type": "adres",
                "woonplaatsnaam": "Didam",
                "gemeentenaam": "Montferland",
                "provincienaam": "Gelderland",
            }
        ],
    }
}


def _default_region(result) -> str | None:
    for key in result["data_schema"].schema:
        if key == CONF_REGION:
            default = key.default
            return default() if callable(default) else None
    return None


async def test_region_from_location(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    hass.config.country = "NL"
    hass.config.latitude, hass.config.longitude = 51.94, 6.13
    aioclient_mock.get(PDOK_REVERSE_URL, json=PDOK_DIDAM)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert _default_region(result) == "zuid"
    assert "Didam" in result["description_placeholders"]["detected"]

    # The user overrides the suggested region
    with patch("custom_components.schoolvakanties_nl.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_REGION: "midden", CONF_PUBLIC_HOLIDAYS: True, CONF_EXTRA_DAYS_OFF: [], CONF_WEEKEND: True},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_REGION] == "midden"


async def test_outside_netherlands_no_suggestion(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    hass.config.country = "BE"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert _default_region(result) is None
    assert aioclient_mock.call_count == 0


async def test_pdok_unreachable(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    hass.config.country = "NL"
    aioclient_mock.get(PDOK_REVERSE_URL, status=500)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert _default_region(result) is None


async def test_single_instance(hass: HomeAssistant) -> None:
    MockConfigEntry(domain=DOMAIN, data={CONF_REGION: "noord"}).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_options_flow(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_REGION: "noord"})
    entry.add_to_hass(hass)
    with patch("custom_components.schoolvakanties_nl.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_REGION: "zuid", CONF_PUBLIC_HOLIDAYS: True, CONF_EXTRA_DAYS_OFF: ["goede_vrijdag"], CONF_WEEKEND: False},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_REGION] == "zuid"
