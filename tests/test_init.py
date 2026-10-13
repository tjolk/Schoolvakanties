"""Integratie opzetten en entiteiten controleren."""

from __future__ import annotations

from typing import Any

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.schoolvakanties_nl.const import CONF_REGION, DOMAIN, SCHOOLVAKANTIES_URL


def _mock_api(aioclient_mock: AiohttpClientMocker, antwoord: dict[str, Any]) -> None:
    for jaar in ("2025-2026", "2027-2028"):
        aioclient_mock.get(SCHOOLVAKANTIES_URL.format(schooljaar=jaar), status=404)
    aioclient_mock.get(SCHOOLVAKANTIES_URL.format(schooljaar="2026-2027"), json=antwoord)


@pytest.fixture
async def opgezet(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    api_antwoord: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> MockConfigEntry:
    await hass.config.async_set_time_zone("Europe/Amsterdam")
    hass.config.language = "nl"  # entity-id's volgen de systeemtaal
    freezer.move_to("2026-10-16 10:00:00+02:00")  # vrijdag voor de herfstvakantie (midden)
    _mock_api(aioclient_mock, api_antwoord)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_REGION: "midden"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_entiteiten(hass: HomeAssistant, opgezet: MockConfigEntry) -> None:
    assert opgezet.state is ConfigEntryState.LOADED

    vandaag = hass.states.get("binary_sensor.schoolvakanties_vandaag")
    assert vandaag.state == "off"
    assert vandaag.attributes["volgende_schooldag"] == "2026-10-26"

    morgen = hass.states.get("binary_sensor.schoolvakanties_morgen")
    assert morgen.state == "on"
    assert morgen.attributes["redenen"] == ["Herfstvakantie", "Weekend"]

    assert hass.states.get("binary_sensor.schoolvakanties_schoolvakantie").state == "off"
    assert hass.states.get("sensor.schoolvakanties_volgende_vakantie").state == "Herfstvakantie"
    assert hass.states.get("sensor.schoolvakanties_begin_volgende_vakantie").state == "2026-10-17"
    assert hass.states.get("sensor.schoolvakanties_dagen_tot_vakantie").state == "1"
    assert hass.states.get("sensor.schoolvakanties_huidige_vakantie").state == "Geen"
    assert hass.states.get("sensor.schoolvakanties_regio").state == "midden"

    kalender = hass.states.get("calendar.schoolvakanties_kalender")
    assert kalender.attributes["message"] == "Herfstvakantie"


async def test_middernacht_wisselt_dag(
    hass: HomeAssistant, opgezet: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    freezer.move_to("2026-10-17 00:00:06+02:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.schoolvakanties_vandaag").state == "on"
    assert hass.states.get("binary_sensor.schoolvakanties_schoolvakantie").state == "on"
    assert hass.states.get("sensor.schoolvakanties_huidige_vakantie").state == "Herfstvakantie"
    assert hass.states.get("sensor.schoolvakanties_dagen_tot_vakantie").state == "0"


async def test_kalender_events(hass: HomeAssistant, opgezet: MockConfigEntry) -> None:
    result = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": "calendar.schoolvakanties_kalender", "start_date_time": "2026-12-01 00:00:00",
         "end_date_time": "2027-01-31 00:00:00"},
        blocking=True,
        return_response=True,
    )
    events = result["calendar.schoolvakanties_kalender"]["events"]
    assert [e["summary"] for e in events] == [
        "Kerstvakantie", "Eerste Kerstdag", "Tweede Kerstdag", "Nieuwjaarsdag"
    ]
    assert events[0]["start"] == "2026-12-19" and events[0]["end"] == "2027-01-04"


async def test_api_plat_zonder_cache(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(SCHOOLVAKANTIES_URL.format(schooljaar="2025-2026"), status=500)
    aioclient_mock.get(SCHOOLVAKANTIES_URL.format(schooljaar="2026-2027"), status=500)
    aioclient_mock.get(SCHOOLVAKANTIES_URL.format(schooljaar="2027-2028"), status=500)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_REGION: "noord"})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload(hass: HomeAssistant, opgezet: MockConfigEntry) -> None:
    assert await hass.config_entries.async_unload(opgezet.entry_id)
    assert opgezet.state is ConfigEntryState.NOT_LOADED
