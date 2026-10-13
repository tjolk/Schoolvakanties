"""Basis-entiteit voor Schoolvakanties Nederland."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BRON_PAGINA, DOMAIN
from .coordinator import SchoolvakantiesCoordinator


class SchoolvakantiesEntity(CoordinatorEntity[SchoolvakantiesCoordinator]):
    """Gemeenschappelijke basis: één apparaat per config entry."""

    _attr_has_entity_name = True
    _attr_attribution = "Schoolvakanties: Rijksoverheid (open data, CC0)"

    def __init__(self, coordinator: SchoolvakantiesCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            # Korte apparaatnaam geeft entity-id's als binary_sensor.schoolvakanties_vandaag
            name="Schoolvakanties",
            manufacturer="Rijksoverheid open data",
            model=f"Regio {coordinator.regio.capitalize()}",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=BRON_PAGINA,
        )
