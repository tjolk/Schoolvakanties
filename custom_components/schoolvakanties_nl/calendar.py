"""Kalender met alle schoolvakanties en schoolvrije feestdagen."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SchoolvakantiesConfigEntry, SchoolvakantiesCoordinator
from .entity import SchoolvakantiesEntity
from .kalender import VrijeDag


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SchoolvakantiesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([SchoolvakantiesKalender(entry.runtime_data)])


def _event(vrij: VrijeDag) -> CalendarEvent:
    return CalendarEvent(
        start=vrij.begin,
        end=vrij.eind + timedelta(days=1),  # eind is exclusief bij hele dagen
        summary=vrij.naam,
        description="Schoolvakantie" if vrij.soort == "vakantie" else "Schoolvrije feestdag",
        uid=f"{vrij.soort}-{vrij.begin.isoformat()}-{vrij.naam}",
    )


class SchoolvakantiesKalender(SchoolvakantiesEntity, CalendarEntity):
    """Kalender-entiteit (weekenden staan er bewust niet in)."""

    def __init__(self, coordinator: SchoolvakantiesCoordinator) -> None:
        super().__init__(coordinator, "kalender")

    @property
    def event(self) -> CalendarEvent | None:
        """Huidig of eerstvolgend vrij moment."""
        vandaag = self.coordinator.vandaag
        kandidaten = sorted(
            self.coordinator.data.vrije_dagen(vandaag, vandaag + timedelta(days=400)),
            key=lambda v: v.begin,
        )
        return _event(kandidaten[0]) if kandidaten else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        begin: date = start_date.date()
        eind: date = end_date.date()
        return [
            _event(v)
            for v in sorted(self.coordinator.data.vrije_dagen(begin, eind), key=lambda v: v.begin)
        ]
