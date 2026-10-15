"""Base entity for Schoolvakanties Nederland."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SOURCE_PAGE
from .coordinator import SchoolvakantiesCoordinator


class SchoolvakantiesEntity(CoordinatorEntity[SchoolvakantiesCoordinator]):
    """Common base: one device per config entry."""

    _attr_has_entity_name = True
    _attr_attribution = "School holidays: Rijksoverheid (open data, CC0)"

    def __init__(self, coordinator: SchoolvakantiesCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        # The key is also used in unique IDs; do not change existing keys.
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            # A short device name gives entity IDs like binary_sensor.schoolvakanties_vandaag
            name="Schoolvakanties",
            manufacturer="Rijksoverheid open data",
            model=f"Regio {coordinator.region.capitalize()}",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=SOURCE_PAGE,
        )
