"""Parser and school calendar."""

from datetime import date
from typing import Any

from custom_components.schoolvakanties_nl.school_calendar import (
    SchoolCalendar,
    filter_region,
    parse_holidays,
    relevant_school_years,
    school_year,
)


def test_school_year() -> None:
    assert school_year(date(2026, 7, 31)) == "2025-2026"
    assert school_year(date(2026, 8, 1)) == "2026-2027"
    assert relevant_school_years(date(2026, 10, 13)) == ["2025-2026", "2026-2027", "2027-2028"]


def test_parse(api_response: dict[str, Any]) -> None:
    holidays = parse_holidays(api_response)
    assert len(holidays) == 7
    autumn_central = next(h for h in holidays if h.region == "midden" and h.name == "Herfstvakantie")
    # 22:00 UTC is midnight in the Netherlands: the day must not shift
    assert (autumn_central.start, autumn_central.end) == (date(2026, 10, 17), date(2026, 10, 25))
    assert autumn_central.school_year == "2026-2027"
    christmas = next(h for h in holidays if h.name == "Kerstvakantie")
    assert christmas.region == "heel nederland"
    assert christmas.compulsory is True


def test_parse_list_and_garbage(api_response: dict[str, Any]) -> None:
    assert parse_holidays([api_response, "garbage", {}]) == parse_holidays(api_response)
    assert parse_holidays(None) == []


def test_filter_region_includes_whole_country(api_response: dict[str, Any]) -> None:
    south = filter_region(parse_holidays(api_response), "zuid")
    assert [h.name for h in south] == ["Herfstvakantie", "Kerstvakantie", "Voorjaarsvakantie"]


def _calendar(api_response: dict[str, Any], **kwargs: Any) -> SchoolCalendar:
    return SchoolCalendar(filter_region(parse_holidays(api_response), "midden"), **kwargs)


def test_is_day_off(api_response: dict[str, Any]) -> None:
    cal = _calendar(api_response)
    assert cal.is_day_off(date(2026, 10, 14)) is False  # Wednesday, school day
    assert cal.reasons(date(2026, 10, 19)) == ["Herfstvakantie"]
    assert cal.reasons(date(2026, 10, 17)) == ["Herfstvakantie", "Weekend"]
    assert cal.reasons(date(2026, 12, 25)) == ["Kerstvakantie", "Eerste Kerstdag"]
    assert cal.reasons(date(2027, 5, 6)) == ["Hemelvaartsdag"]
    assert cal.next_school_day(date(2026, 10, 16)) == date(2026, 10, 26)


def test_weekend_off_disabled(api_response: dict[str, Any]) -> None:
    cal = _calendar(api_response, weekend_off=False)
    assert cal.is_day_off(date(2026, 10, 10)) is False


def test_next_holiday(api_response: dict[str, Any]) -> None:
    cal = _calendar(api_response)
    assert cal.next_holiday(date(2026, 10, 13)).name == "Herfstvakantie"
    assert cal.next_holiday(date(2026, 10, 20)).name == "Kerstvakantie"


def test_days_off_for_calendar(api_response: dict[str, Any]) -> None:
    cal = _calendar(api_response)
    names = [d.name for d in cal.days_off(date(2026, 12, 1), date(2027, 1, 31))]
    assert names == ["Kerstvakantie", "Eerste Kerstdag", "Tweede Kerstdag", "Nieuwjaarsdag"]
