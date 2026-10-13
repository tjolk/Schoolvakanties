"""Binary sensors: is het vandaag/morgen schoolvrij, en is het vakantie?"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SchoolvakantiesConfigEntry, SchoolvakantiesCoordinator
from .entity import SchoolvakantiesEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SchoolvakantiesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            SchoolvakantiesDagSensor(coordinator, "vandaag", 0),
            SchoolvakantiesDagSensor(coordinator, "morgen", 1),
            SchoolvakantieSensor(coordinator),
        ]
    )


class SchoolvakantiesDagSensor(SchoolvakantiesEntity, BinarySensorEntity):
    """Aan als er op die dag geen school is (vakantie, feestdag of weekend)."""

    def __init__(self, coordinator: SchoolvakantiesCoordinator, key: str, offset: int) -> None:
        super().__init__(coordinator, key)
        self._offset = offset

    @property
    def _dag(self) -> date:
        return self.coordinator.vandaag + timedelta(days=self._offset)

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.is_vrij(self._dag)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        kalender = self.coordinator.data
        vakantie = kalender.vakantie_op(self._dag)
        volgende = kalender.volgende_schooldag(self._dag)
        return {
            "datum": self._dag.isoformat(),
            "redenen": kalender.redenen(self._dag),
            "vakantie": vakantie.naam if vakantie else None,
            "feestdag": kalender.feestdag_op(self._dag),
            "weekend": kalender.is_weekend(self._dag),
            "volgende_schooldag": volgende.isoformat() if volgende else None,
        }


class SchoolvakantieSensor(SchoolvakantiesEntity, BinarySensorEntity):
    """Aan tijdens een schoolvakantie (zonder losse feestdagen en weekenden)."""

    def __init__(self, coordinator: SchoolvakantiesCoordinator) -> None:
        super().__init__(coordinator, "vakantie")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.vakantie_op(self.coordinator.vandaag) is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        vakantie = self.coordinator.data.vakantie_op(self.coordinator.vandaag)
        if vakantie is None:
            return {"naam": None, "begin": None, "eind": None}
        return {
            "naam": vakantie.naam,
            "begin": vakantie.begin.isoformat(),
            "eind": vakantie.eind.isoformat(),
        }
