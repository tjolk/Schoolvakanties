"""Sensors: huidige en volgende vakantie, aftellen en regio."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SchoolvakantiesConfigEntry, SchoolvakantiesCoordinator
from .entity import SchoolvakantiesEntity
from .kalender import Vakantie


def _vakantie_attrs(vakantie: Vakantie | None, vandaag: date) -> dict[str, Any]:
    if vakantie is None:
        return {}
    return {
        "naam": vakantie.naam,
        "begin": vakantie.begin.isoformat(),
        "eind": vakantie.eind.isoformat(),
        "dagen": (vakantie.eind - vakantie.begin).days + 1,
        "dagen_tot_begin": max((vakantie.begin - vandaag).days, 0),
        "schooljaar": vakantie.schooljaar,
    }


@dataclass(frozen=True, kw_only=True)
class SchoolvakantiesSensorDescription(SensorEntityDescription):
    """Beschrijving met functies voor waarde en attributen."""

    waarde: Callable[[SchoolvakantiesCoordinator], Any]
    attributen: Callable[[SchoolvakantiesCoordinator], dict[str, Any]] = lambda _c: {}


def _huidige(c: SchoolvakantiesCoordinator) -> Vakantie | None:
    return c.data.vakantie_op(c.vandaag)


def _volgende(c: SchoolvakantiesCoordinator) -> Vakantie | None:
    return c.data.volgende_vakantie(c.vandaag)


SENSOREN: tuple[SchoolvakantiesSensorDescription, ...] = (
    SchoolvakantiesSensorDescription(
        key="huidige_vakantie",
        translation_key="huidige_vakantie",
        waarde=lambda c: v.naam if (v := _huidige(c)) else "Geen",
        attributen=lambda c: _vakantie_attrs(_huidige(c), c.vandaag),
    ),
    SchoolvakantiesSensorDescription(
        key="volgende_vakantie",
        translation_key="volgende_vakantie",
        waarde=lambda c: v.naam if (v := _volgende(c)) else None,
        attributen=lambda c: _vakantie_attrs(_volgende(c), c.vandaag),
    ),
    SchoolvakantiesSensorDescription(
        key="volgende_vakantie_begin",
        translation_key="volgende_vakantie_begin",
        device_class=SensorDeviceClass.DATE,
        waarde=lambda c: v.begin if (v := _volgende(c)) else None,
    ),
    SchoolvakantiesSensorDescription(
        key="dagen_tot_vakantie",
        translation_key="dagen_tot_vakantie",
        native_unit_of_measurement=UnitOfTime.DAYS,
        waarde=lambda c: (
            0 if _huidige(c) else ((v.begin - c.vandaag).days if (v := _volgende(c)) else None)
        ),
    ),
    SchoolvakantiesSensorDescription(
        key="regio",
        translation_key="regio",
        device_class=SensorDeviceClass.ENUM,
        options=["noord", "midden", "zuid"],
        entity_category=EntityCategory.DIAGNOSTIC,
        waarde=lambda c: c.regio,
        attributen=lambda c: {
            "laatste_bekende_vakantiedag": (
                d.isoformat() if (d := c.data.laatste_bekende_dag) else None
            )
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SchoolvakantiesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(SchoolvakantiesSensor(coordinator, d) for d in SENSOREN)


class SchoolvakantiesSensor(SchoolvakantiesEntity, SensorEntity):
    """Sensor op basis van een beschrijving."""

    entity_description: SchoolvakantiesSensorDescription

    def __init__(
        self, coordinator: SchoolvakantiesCoordinator, description: SchoolvakantiesSensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.waarde(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.entity_description.attributen(self.coordinator)
