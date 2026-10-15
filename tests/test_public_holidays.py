"""Public holidays are calculated from rules; check known years."""

from datetime import date

import pytest

from custom_components.schoolvakanties_nl.public_holidays import easter, holidays_in_year


@pytest.mark.parametrize(
    ("year", "expected"),
    [
        (2024, date(2024, 3, 31)),
        (2025, date(2025, 4, 20)),
        (2026, date(2026, 4, 5)),
        (2027, date(2027, 3, 28)),
        (2028, date(2028, 4, 16)),
        (2038, date(2038, 4, 25)),
    ],
)
def test_easter(year: int, expected: date) -> None:
    assert easter(year) == expected


def test_holidays_2026() -> None:
    assert holidays_in_year(2026) == {
        date(2026, 1, 1): "Nieuwjaarsdag",
        date(2026, 4, 6): "Tweede Paasdag",
        date(2026, 4, 27): "Koningsdag",
        date(2026, 5, 5): "Bevrijdingsdag",
        date(2026, 5, 14): "Hemelvaartsdag",
        date(2026, 5, 25): "Tweede Pinksterdag",
        date(2026, 12, 25): "Eerste Kerstdag",
        date(2026, 12, 26): "Tweede Kerstdag",
    }


def test_kings_day_on_sunday_moves_to_saturday() -> None:
    # 27 April 2025 and 2031 are Sundays
    assert date(2025, 4, 26) in holidays_in_year(2025)
    assert date(2025, 4, 27) not in holidays_in_year(2025)
    assert holidays_in_year(2031)[date(2031, 4, 26)] == "Koningsdag"


def test_optional_days_off() -> None:
    days = holidays_in_year(2026, optional=["goede_vrijdag", "dag_na_hemelvaart"])
    assert days[date(2026, 4, 3)] == "Goede Vrijdag"
    assert days[date(2026, 5, 15)] == "Vrijdag na Hemelvaart"
    assert date(2026, 4, 3) not in holidays_in_year(2026)


def test_without_national_holidays() -> None:
    assert holidays_in_year(2026, national=False) == {}
