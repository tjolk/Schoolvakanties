"""School calendar: holidays from the API plus public holidays and weekends.

Also contains the parser for the Dutch government's open data. This module has
no Home Assistant imports, so it can be tested on its own.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .const import REGION_WHOLE_COUNTRY, TIMEZONE
from .public_holidays import holidays_in_year

_TZ = ZoneInfo(TIMEZONE)

# Reason shown to users when a day is free because it is a weekend.
REASON_WEEKEND = "Weekend"


@dataclass(frozen=True, order=True)
class SchoolHoliday:
    """One school holiday for one region. Start and end are inclusive."""

    start: date
    end: date
    name: str
    region: str
    school_year: str = ""
    compulsory: bool = False

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "region": self.region,
            "school_year": self.school_year,
            "compulsory": self.compulsory,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SchoolHoliday:
        return cls(
            start=date.fromisoformat(data["start"]),
            end=date.fromisoformat(data["end"]),
            name=data["name"],
            region=data["region"],
            school_year=data.get("school_year", ""),
            compulsory=bool(data.get("compulsory", False)),
        )


@dataclass(frozen=True)
class DayOff:
    """A day (or period) without school."""

    start: date
    end: date
    name: str
    kind: str  # "holiday" or "public_holiday"


def school_year(day: date) -> str:
    """School year a date belongs to, e.g. '2026-2027' (the year turns on 1 August)."""
    start = day.year if day.month >= 8 else day.year - 1
    return f"{start}-{start + 1}"


def relevant_school_years(day: date) -> list[str]:
    """Previous, current and next school year, so the summer holiday is always covered."""
    start = int(school_year(day)[:4])
    return [f"{y}-{y + 1}" for y in (start - 1, start, start + 1)]


def _to_date(value: str) -> date:
    """Convert an API timestamp to a Dutch calendar date.

    The API returns UTC timestamps (e.g. '2026-10-17T00:00:00.000Z' or
    '2026-10-16T22:00:00.000Z'). Converting to Europe/Amsterdam gives the
    correct day in both cases.
    """
    moment = datetime.fromisoformat(value.strip())
    if moment.tzinfo is not None:
        moment = moment.astimezone(_TZ)
    return moment.date()


def _to_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


def parse_holidays(data: Any) -> list[SchoolHoliday]:
    """Parse a school holiday API response into SchoolHoliday objects (all regions).

    Structure: {content: [{schoolyear, vacations: [{type, compulsorydates,
    regions: [{region, startdate, enddate}]}]}]}. A list of such objects (the
    endpoint without a school year) is accepted as well.
    """
    documents = data if isinstance(data, list) else [data]
    result: set[SchoolHoliday] = set()
    for document in documents:
        if not isinstance(document, dict):
            continue
        for content in document.get("content") or []:
            year = str(content.get("schoolyear", "")).strip()
            for vacation in content.get("vacations") or []:
                name = " ".join(str(vacation.get("type", "")).split()) or "Schoolvakantie"
                compulsory = _to_bool(vacation.get("compulsorydates", False))
                for region in vacation.get("regions") or []:
                    try:
                        start = _to_date(region["startdate"])
                        end = _to_date(region["enddate"])
                    except (KeyError, TypeError, ValueError):
                        continue
                    result.add(
                        SchoolHoliday(
                            start=start,
                            end=end,
                            name=name,
                            region=" ".join(str(region.get("region", "")).lower().split()),
                            school_year=year,
                            compulsory=compulsory,
                        )
                    )
    return sorted(result)


def filter_region(holidays: Iterable[SchoolHoliday], region: str) -> list[SchoolHoliday]:
    """Keep the holidays for one region, including those for the whole country."""
    return sorted(h for h in holidays if h.region in (region, REGION_WHOLE_COUNTRY))


@dataclass
class SchoolCalendar:
    """Answers 'is there school today?' for one region."""

    holidays: list[SchoolHoliday]
    public_holidays: bool = True
    optional_days_off: tuple[str, ...] = ()
    weekend_off: bool = True
    _public_holiday_cache: dict[int, dict[date, str]] = field(default_factory=dict, repr=False)

    def public_holidays_in_year(self, year: int) -> dict[date, str]:
        if year not in self._public_holiday_cache:
            self._public_holiday_cache[year] = holidays_in_year(
                year, national=self.public_holidays, optional=self.optional_days_off
            )
        return self._public_holiday_cache[year]

    def holiday_on(self, day: date) -> SchoolHoliday | None:
        return next((h for h in self.holidays if h.contains(day)), None)

    def public_holiday_on(self, day: date) -> str | None:
        return self.public_holidays_in_year(day.year).get(day)

    def is_weekend(self, day: date) -> bool:
        return day.weekday() >= 5

    def reasons(self, day: date) -> list[str]:
        """All reasons why a day has no school (empty list = school day)."""
        reasons: list[str] = []
        if holiday := self.holiday_on(day):
            reasons.append(holiday.name)
        if public_holiday := self.public_holiday_on(day):
            reasons.append(public_holiday)
        if self.weekend_off and self.is_weekend(day):
            reasons.append(REASON_WEEKEND)
        return reasons

    def is_day_off(self, day: date) -> bool:
        return bool(self.reasons(day))

    def next_holiday(self, day: date) -> SchoolHoliday | None:
        """First holiday that starts after the given day."""
        return next((h for h in self.holidays if h.start > day), None)

    def next_school_day(self, day: date, max_days: int = 120) -> date | None:
        for offset in range(1, max_days + 1):
            candidate = day + timedelta(days=offset)
            if not self.is_day_off(candidate):
                return candidate
        return None

    def days_off(self, start: date, end: date) -> Iterator[DayOff]:
        """Holidays and public holidays that (partly) fall between start and end. No weekends."""
        for holiday in self.holidays:
            if holiday.end >= start and holiday.start <= end:
                yield DayOff(holiday.start, holiday.end, holiday.name, "holiday")
        for year in range(start.year, end.year + 1):
            for day, name in sorted(self.public_holidays_in_year(year).items()):
                if start <= day <= end:
                    yield DayOff(day, day, name, "public_holiday")

    @property
    def last_known_day(self) -> date | None:
        return max((h.end for h in self.holidays), default=None)
