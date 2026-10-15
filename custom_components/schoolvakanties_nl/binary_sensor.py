"""Binary sensors: is there no school today/tomorrow, and is it a school holiday?

Entity names and attribute names are Dutch on purpose: the users are parents of
children at Dutch schools.
"""

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
            DayOffSensor(coordinator, "vandaag", 0),
            DayOffSensor(coordinator, "morgen", 1),
            SchoolHolidaySensor(coordinator),
        ]
    )


class DayOffSensor(SchoolvakantiesEntity, BinarySensorEntity):
    """On when there is no school on that day (holiday, public holiday or weekend)."""

    def __init__(self, coordinator: SchoolvakantiesCoordinator, key: str, offset_days: int) -> None:
        super().__init__(coordinator, key)
        self._offset_days = offset_days

    @property
    def _day(self) -> date:
        return self.coordinator.today + timedelta(days=self._offset_days)

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.is_day_off(self._day)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        calendar = self.coordinator.data
        holiday = calendar.holiday_on(self._day)
        next_school_day = calendar.next_school_day(self._day)
        return {
            "datum": self._day.isoformat(),
            "redenen": calendar.reasons(self._day),
            "vakantie": holiday.name if holiday else None,
            "feestdag": calendar.public_holiday_on(self._day),
            "weekend": calendar.is_weekend(self._day),
            "volgende_schooldag": next_school_day.isoformat() if next_school_day else None,
        }


class SchoolHolidaySensor(SchoolvakantiesEntity, BinarySensorEntity):
    """On during a school holiday (not on single public holidays or weekends)."""

    def __init__(self, coordinator: SchoolvakantiesCoordinator) -> None:
        super().__init__(coordinator, "vakantie")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.holiday_on(self.coordinator.today) is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        holiday = self.coordinator.data.holiday_on(self.coordinator.today)
        if holiday is None:
            return {"naam": None, "begin": None, "eind": None}
        return {
            "naam": holiday.name,
            "begin": holiday.start.isoformat(),
            "eind": holiday.end.isoformat(),
        }
