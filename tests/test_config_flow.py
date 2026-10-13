"""Config flow: regio voorstellen op basis van de thuislocatie."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.schoolvakanties_nl.const import (
    CONF_FEESTDAGEN,
    CONF_OPTIONELE_DAGEN,
    CONF_REGION,
    CONF_WEEKEND,
    DOMAIN,
    PDOK_REVERSE_URL,
)

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


def _standaard_regio(result) -> str | None:
    for sleutel in result["data_schema"].schema:
        if sleutel == CONF_REGION:
            default = sleutel.default
            return default() if callable(default) else None
    return None


async def test_regio_uit_locatie(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    hass.config.country = "NL"
    hass.config.latitude, hass.config.longitude = 51.94, 6.13
    aioclient_mock.get(PDOK_REVERSE_URL, json=PDOK_DIDAM)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert _standaard_regio(result) == "zuid"
    assert "Didam" in result["description_placeholders"]["detectie"]

    # Gebruiker overrulet de voorgestelde regio
    with patch("custom_components.schoolvakanties_nl.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_REGION: "midden", CONF_FEESTDAGEN: True, CONF_OPTIONELE_DAGEN: [], CONF_WEEKEND: True},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_REGION] == "midden"


async def test_buiten_nederland_geen_voorstel(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    hass.config.country = "BE"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert _standaard_regio(result) is None
    assert aioclient_mock.call_count == 0


async def test_pdok_onbereikbaar(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    hass.config.country = "NL"
    aioclient_mock.get(PDOK_REVERSE_URL, status=500)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert _standaard_regio(result) is None


async def test_maar_een_keer(hass: HomeAssistant) -> None:
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
            {CONF_REGION: "zuid", CONF_FEESTDAGEN: True, CONF_OPTIONELE_DAGEN: ["goede_vrijdag"], CONF_WEEKEND: False},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_REGION] == "zuid"
