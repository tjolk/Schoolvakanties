"""Regio bepalen uit provincie, gemeente en woonplaats (zoals PDOK ze teruggeeft)."""

import pytest

from custom_components.schoolvakanties_nl.regios import bepaal_regio


@pytest.mark.parametrize(
    ("provincie", "gemeente", "woonplaats", "regio"),
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
def test_bepaal_regio(provincie: str, gemeente: str, woonplaats: str, regio: str) -> None:
    assert bepaal_regio(provincie=provincie, gemeente=gemeente, woonplaats=woonplaats) == regio


def test_onbekende_gelderse_gemeente_geeft_none() -> None:
    assert bepaal_regio(provincie="Gelderland", gemeente="Bestaat Niet") is None


def test_niets_bekend() -> None:
    assert bepaal_regio() is None
