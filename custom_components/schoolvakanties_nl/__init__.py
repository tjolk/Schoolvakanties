"""Schoolvakanties Nederland: schoolvakanties en schoolvrije feestdagen in Home Assistant."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import SchoolvakantiesConfigEntry, SchoolvakantiesCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: SchoolvakantiesConfigEntry) -> bool:
    """Zet de integratie op vanuit een config entry."""
    coordinator = SchoolvakantiesCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_herlaad))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SchoolvakantiesConfigEntry) -> bool:
    """Verwijder de integratie."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_herlaad(hass: HomeAssistant, entry: SchoolvakantiesConfigEntry) -> None:
    """Herlaad na het wijzigen van de opties."""
    await hass.config_entries.async_reload(entry.entry_id)
