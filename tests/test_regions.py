"""Resolve the region from province, municipality and town (as returned by PDOK)."""

import pytest

from custom_components.schoolvakanties_nl.regions import resolve_region


@pytest.mark.parametrize(
    ("province", "municipality", "town", "region"),
    [
        ("Noord-Holland", "Amsterdam", "Amsterdam", "noord"),
        ("Fryslân", "Leeuwarden", "Leeuwarden", "noord"),
        ("Flevoland", "Almere", "Almere", "noord"),
        ("Flevoland", "Zeewolde", "Zeewolde", "midden"),
        ("Utrecht", "Utrecht", "Utrecht", "midden"),
        ("Utrecht", "Eemnes", "Eemnes", "noord"),
        ("Utrecht", "De Ronde Venen", "Abcoude", "noord"),
        ("Utrecht", "De Ronde Venen", "Mijdrecht", "midden"),
        ("Zuid-Holland", "'s-Gravenhage", "'s-Gravenhage", "midden"),
        ("Gelderland", "Hattem", "Hattem", "noord"),
        ("Gelderland", "Apeldoorn", "Apeldoorn", "midden"),
        ("Gelderland", "Oost Gelre", "Groenlo", "midden"),
        ("Gelderland", "Oost-Gelre", "Groenlo", "midden"),
        ("Gelderland", "Nijmegen", "Nijmegen", "zuid"),
        ("Gelderland", "Montferland", "Didam", "zuid"),
        ("Gelderland", "Montferland", "'s-Heerenberg", "midden"),
        ("Gelderland", "Neder-Betuwe", "Dodewaard", "zuid"),
        ("Gelderland", "Neder-Betuwe", "Kesteren", "midden"),
        ("Noord-Brabant", "Eindhoven", "Eindhoven", "zuid"),
        ("Noord-Brabant", "Altena", "Werkendam", "midden"),
        ("Noord-Brabant", "Altena", "Dussen", "zuid"),
        ("Limburg", "Maastricht", "Maastricht", "zuid"),
        ("Zeeland", "Middelburg", "Middelburg", "zuid"),
    ],
)
def test_resolve_region(province: str, municipality: str, town: str, region: str) -> None:
    assert resolve_region(province=province, municipality=municipality, town=town) == region


def test_unknown_municipality_in_split_province_returns_none() -> None:
    assert resolve_region(province="Gelderland", municipality="Does Not Exist") is None


def test_nothing_known() -> None:
    assert resolve_region() is None
