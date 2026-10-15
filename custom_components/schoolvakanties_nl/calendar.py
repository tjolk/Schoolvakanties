"""Calendar with all school holidays and school-free public holidays."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SchoolvakantiesConfigEntry, SchoolvakantiesCoordinator
from .entity import SchoolvakantiesEntity
from .school_calendar import DayOff

# Event descriptions shown to users (Dutch on purpose).
DESCRIPTIONS = {"holiday": "Schoolvakantie", "public_holiday": "Schoolvrije feestdag"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SchoolvakantiesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([SchoolvakantiesCalendar(entry.runtime_data)])


def _to_event(day_off: DayOff) -> CalendarEvent:
    return CalendarEvent(
        start=day_off.start,
        end=day_off.end + timedelta(days=1),  # the end of an all-day event is exclusive
        summary=day_off.name,
        description=DESCRIPTIONS[day_off.kind],
        uid=f"{day_off.kind}-{day_off.start.isoformat()}-{day_off.name}",
    )


class SchoolvakantiesCalendar(SchoolvakantiesEntity, CalendarEntity):
    """Calendar entity (weekends are deliberately left out)."""

    def __init__(self, coordinator: SchoolvakantiesCoordinator) -> None:
        super().__init__(coordinator, "kalender")

    @property
    def event(self) -> CalendarEvent | None:
        """Current or next day off."""
        today = self.coordinator.today
        upcoming = sorted(
            self.coordinator.data.days_off(today, today + timedelta(days=400)),
            key=lambda d: d.start,
        )
        return _to_event(upcoming[0]) if upcoming else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        start: date = start_date.date()
        end: date = end_date.date()
        return [
            _to_event(d)
            for d in sorted(self.coordinator.data.days_off(start, end), key=lambda d: d.start)
        ]
