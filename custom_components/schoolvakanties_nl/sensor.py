"""Sensors: current and next holiday, countdown and region.

Attribute names are Dutch on purpose: the users are parents of children at
Dutch schools.
"""

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

from .const import REGIONS
from .coordinator import SchoolvakantiesConfigEntry, SchoolvakantiesCoordinator
from .entity import SchoolvakantiesEntity
from .school_calendar import SchoolHoliday

# State of the 'current holiday' sensor outside a holiday.
NO_HOLIDAY = "Geen"


def _holiday_attributes(holiday: SchoolHoliday | None, today: date) -> dict[str, Any]:
    if holiday is None:
        return {}
    return {
        "naam": holiday.name,
        "begin": holiday.start.isoformat(),
        "eind": holiday.end.isoformat(),
        "dagen": (holiday.end - holiday.start).days + 1,
        "dagen_tot_begin": max((holiday.start - today).days, 0),
        "schooljaar": holiday.school_year,
    }


@dataclass(frozen=True, kw_only=True)
class SchoolvakantiesSensorDescription(SensorEntityDescription):
    """Description with functions for the value and the attributes."""

    value_fn: Callable[[SchoolvakantiesCoordinator], Any]
    attributes_fn: Callable[[SchoolvakantiesCoordinator], dict[str, Any]] = lambda _c: {}


def _current(c: SchoolvakantiesCoordinator) -> SchoolHoliday | None:
    return c.data.holiday_on(c.today)


def _next(c: SchoolvakantiesCoordinator) -> SchoolHoliday | None:
    return c.data.next_holiday(c.today)


def _days_until_holiday(c: SchoolvakantiesCoordinator) -> int | None:
    if _current(c):
        return 0
    upcoming = _next(c)
    return (upcoming.start - c.today).days if upcoming else None


# The keys are also used in unique IDs and translations; do not change them.
SENSORS: tuple[SchoolvakantiesSensorDescription, ...] = (
    SchoolvakantiesSensorDescription(
        key="huidige_vakantie",
        translation_key="huidige_vakantie",
        value_fn=lambda c: h.name if (h := _current(c)) else NO_HOLIDAY,
        attributes_fn=lambda c: _holiday_attributes(_current(c), c.today),
    ),
    SchoolvakantiesSensorDescription(
        key="volgende_vakantie",
        translation_key="volgende_vakantie",
        value_fn=lambda c: h.name if (h := _next(c)) else None,
        attributes_fn=lambda c: _holiday_attributes(_next(c), c.today),
    ),
    SchoolvakantiesSensorDescription(
        key="volgende_vakantie_begin",
        translation_key="volgende_vakantie_begin",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda c: h.start if (h := _next(c)) else None,
    ),
    SchoolvakantiesSensorDescription(
        key="dagen_tot_vakantie",
        translation_key="dagen_tot_vakantie",
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=_days_until_holiday,
    ),
    SchoolvakantiesSensorDescription(
        key="regio",
        translation_key="regio",
        device_class=SensorDeviceClass.ENUM,
        options=list(REGIONS),
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.region,
        attributes_fn=lambda c: {
            "laatste_bekende_vakantiedag": (
                d.isoformat() if (d := c.data.last_known_day) else None
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
    async_add_entities(SchoolvakantiesSensor(coordinator, d) for d in SENSORS)


class SchoolvakantiesSensor(SchoolvakantiesEntity, SensorEntity):
    """Sensor driven by a description."""

    entity_description: SchoolvakantiesSensorDescription

    def __init__(
        self, coordinator: SchoolvakantiesCoordinator, description: SchoolvakantiesSensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.entity_description.attributes_fn(self.coordinator)
