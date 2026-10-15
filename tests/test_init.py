"""Set up the integration and check the entities."""

from __future__ import annotations

from typing import Any

import pytest
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.schoolvakanties_nl.const import CONF_REGION, DOMAIN, SCHOOL_HOLIDAYS_URL
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant


def _mock_api(aioclient_mock: AiohttpClientMocker, response: dict[str, Any]) -> None:
    for year in ("2025-2026", "2027-2028"):
        aioclient_mock.get(SCHOOL_HOLIDAYS_URL.format(school_year=year), status=404)
    aioclient_mock.get(SCHOOL_HOLIDAYS_URL.format(school_year="2026-2027"), json=response)


@pytest.fixture
async def set_up(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    api_response: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> MockConfigEntry:
    await hass.config.async_set_time_zone("Europe/Amsterdam")
    hass.config.language = "nl"  # entity IDs follow the system language
    freezer.move_to("2026-10-16 10:00:00+02:00")  # Friday before the autumn holiday (midden)
    _mock_api(aioclient_mock, api_response)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_REGION: "midden"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_entities(hass: HomeAssistant, set_up: MockConfigEntry) -> None:
    assert set_up.state is ConfigEntryState.LOADED

    today = hass.states.get("binary_sensor.schoolvakanties_vandaag")
    assert today.state == "off"
    assert today.attributes["volgende_schooldag"] == "2026-10-26"

    tomorrow = hass.states.get("binary_sensor.schoolvakanties_morgen")
    assert tomorrow.state == "on"
    assert tomorrow.attributes["redenen"] == ["Herfstvakantie", "Weekend"]

    assert hass.states.get("binary_sensor.schoolvakanties_schoolvakantie").state == "off"
    assert hass.states.get("sensor.schoolvakanties_volgende_vakantie").state == "Herfstvakantie"
    assert hass.states.get("sensor.schoolvakanties_begin_volgende_vakantie").state == "2026-10-17"
    assert hass.states.get("sensor.schoolvakanties_dagen_tot_vakantie").state == "1"
    assert hass.states.get("sensor.schoolvakanties_huidige_vakantie").state == "Geen"
    assert hass.states.get("sensor.schoolvakanties_regio").state == "midden"

    calendar = hass.states.get("calendar.schoolvakanties_kalender")
    assert calendar.attributes["message"] == "Herfstvakantie"


async def test_midnight_switches_day(
    hass: HomeAssistant, set_up: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    freezer.move_to("2026-10-17 00:00:06+02:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.schoolvakanties_vandaag").state == "on"
    assert hass.states.get("binary_sensor.schoolvakanties_schoolvakantie").state == "on"
    assert hass.states.get("sensor.schoolvakanties_huidige_vakantie").state == "Herfstvakantie"
    assert hass.states.get("sensor.schoolvakanties_dagen_tot_vakantie").state == "0"


async def test_calendar_events(hass: HomeAssistant, set_up: MockConfigEntry) -> None:
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


async def test_api_down_without_cache(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(SCHOOL_HOLIDAYS_URL.format(school_year="2025-2026"), status=500)
    aioclient_mock.get(SCHOOL_HOLIDAYS_URL.format(school_year="2026-2027"), status=500)
    aioclient_mock.get(SCHOOL_HOLIDAYS_URL.format(school_year="2027-2028"), status=500)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_REGION: "noord"})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload(hass: HomeAssistant, set_up: MockConfigEntry) -> None:
    assert await hass.config_entries.async_unload(set_up.entry_id)
    assert set_up.state is ConfigEntryState.NOT_LOADED
