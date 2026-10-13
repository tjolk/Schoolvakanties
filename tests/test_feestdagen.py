"""Feestdagen worden als regels berekend; controleer bekende jaren."""

from datetime import date

import pytest

from custom_components.schoolvakanties_nl.feestdagen import feestdagen_in_jaar, pasen


@pytest.mark.parametrize(
    ("jaar", "verwacht"),
    [(2024, date(2024, 3, 31)), (2025, date(2025, 4, 20)), (2026, date(2026, 4, 5)),
     (2027, date(2027, 3, 28)), (2028, date(2028, 4, 16)), (2038, date(2038, 4, 25))],
)
def test_pasen(jaar: int, verwacht: date) -> None:
    assert pasen(jaar) == verwacht


def test_feestdagen_2026() -> None:
    dagen = feestdagen_in_jaar(2026)
    assert dagen == {
        date(2026, 1, 1): "Nieuwjaarsdag",
        date(2026, 4, 6): "Tweede Paasdag",
        date(2026, 4, 27): "Koningsdag",
        date(2026, 5, 5): "Bevrijdingsdag",
        date(2026, 5, 14): "Hemelvaartsdag",
        date(2026, 5, 25): "Tweede Pinksterdag",
        date(2026, 12, 25): "Eerste Kerstdag",
        date(2026, 12, 26): "Tweede Kerstdag",
    }


def test_koningsdag_op_zondag_wordt_zaterdag() -> None:
    # 27 april 2025 en 2031 vallen op zondag
    assert date(2025, 4, 26) in feestdagen_in_jaar(2025)
    assert date(2025, 4, 27) not in feestdagen_in_jaar(2025)
    assert feestdagen_in_jaar(2031)[date(2031, 4, 26)] == "Koningsdag"


def test_optionele_dagen() -> None:
    dagen = feestdagen_in_jaar(2026, optioneel=["goede_vrijdag", "dag_na_hemelvaart"])
    assert dagen[date(2026, 4, 3)] == "Goede Vrijdag"
    assert dagen[date(2026, 5, 15)] == "Vrijdag na Hemelvaart"
    assert date(2026, 4, 3) not in feestdagen_in_jaar(2026)


def test_zonder_nationale_feestdagen() -> None:
    assert feestdagen_in_jaar(2026, nationaal=False) == {}
