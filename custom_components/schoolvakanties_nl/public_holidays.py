"""Public holidays on which schools are closed.

Source: https://www.rijksoverheid.nl/themas/onderwijs/schoolvakanties/vrij-van-school-op-feestdagen

The Dutch government offers no API for this list. The holidays are therefore
defined as *rules* (not fixed dates), so they are correct for every year. If the
official list changes, only NATIONAL_HOLIDAYS or OPTIONAL_DAYS_OFF need editing.

Holiday names are Dutch on purpose: they are shown to users in Home Assistant.

This module has no Home Assistant imports, so it can be tested on its own.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, timedelta


def easter(year: int) -> date:
    """Easter Sunday (Gregorian calendar, anonymous Meeus/Jones/Butcher algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def _fixed(month: int, day: int) -> Callable[[int], date]:
    return lambda year: date(year, month, day)


def _after_easter(days: int) -> Callable[[int], date]:
    return lambda year: easter(year) + timedelta(days=days)


def _kings_day(year: int) -> date:
    """27 April, or 26 April when 27 April is a Sunday."""
    day = date(year, 4, 27)
    return day - timedelta(days=1) if day.weekday() == 6 else day


@dataclass(frozen=True)
class PublicHoliday:
    """A public holiday defined as a rule."""

    key: str
    name: str
    date_for_year: Callable[[int], date]


# National holidays on which schools are closed in principle.
NATIONAL_HOLIDAYS: tuple[PublicHoliday, ...] = (
    PublicHoliday("nieuwjaarsdag", "Nieuwjaarsdag", _fixed(1, 1)),
    PublicHoliday("tweede_paasdag", "Tweede Paasdag", _after_easter(1)),
    PublicHoliday("koningsdag", "Koningsdag", _kings_day),
    PublicHoliday("bevrijdingsdag", "Bevrijdingsdag", _fixed(5, 5)),
    PublicHoliday("hemelvaartsdag", "Hemelvaartsdag", _after_easter(39)),
    PublicHoliday("tweede_pinksterdag", "Tweede Pinksterdag", _after_easter(50)),
    PublicHoliday("eerste_kerstdag", "Eerste Kerstdag", _fixed(12, 25)),
    PublicHoliday("tweede_kerstdag", "Tweede Kerstdag", _fixed(12, 26)),
)

# Days that schools may give off at their own discretion. Users enable them in the options.
OPTIONAL_DAYS_OFF: tuple[PublicHoliday, ...] = (
    PublicHoliday("goede_vrijdag", "Goede Vrijdag", _after_easter(-2)),
    PublicHoliday("dag_na_hemelvaart", "Vrijdag na Hemelvaart", _after_easter(40)),
)

OPTIONAL_KEYS: tuple[str, ...] = tuple(h.key for h in OPTIONAL_DAYS_OFF)


def holidays_in_year(
    year: int,
    *,
    national: bool = True,
    optional: Iterable[str] = (),
) -> dict[date, str]:
    """Return {date: name} for all school-free public holidays in a year."""
    selected = set(optional)
    rules = list(NATIONAL_HOLIDAYS) if national else []
    rules += [h for h in OPTIONAL_DAYS_OFF if h.key in selected]
    result: dict[date, str] = {}
    for rule in rules:
        result.setdefault(rule.date_for_year(year), rule.name)
    return result
