"""Parser en schoolkalender."""

from datetime import date
from typing import Any

from custom_components.schoolvakanties_nl.kalender import (
    Schoolkalender,
    filter_regio,
    parse_vakanties,
    relevante_schooljaren,
    schooljaar,
)


def test_schooljaar() -> None:
    assert schooljaar(date(2026, 7, 31)) == "2025-2026"
    assert schooljaar(date(2026, 8, 1)) == "2026-2027"
    assert relevante_schooljaren(date(2026, 10, 13)) == ["2025-2026", "2026-2027", "2027-2028"]


def test_parse(api_antwoord: dict[str, Any]) -> None:
    vakanties = parse_vakanties(api_antwoord)
    assert len(vakanties) == 7
    herfst_midden = next(v for v in vakanties if v.regio == "midden" and v.naam == "Herfstvakantie")
    # 22:00 UTC is middernacht in Nederland: dag mag niet verschuiven
    assert (herfst_midden.begin, herfst_midden.eind) == (date(2026, 10, 17), date(2026, 10, 25))
    assert herfst_midden.schooljaar == "2026-2027"
    kerst = next(v for v in vakanties if v.naam == "Kerstvakantie")
    assert kerst.regio == "heel nederland"
    assert kerst.verplicht is True


def test_parse_lijst_en_rommel(api_antwoord: dict[str, Any]) -> None:
    assert parse_vakanties([api_antwoord, "rommel", {}]) == parse_vakanties(api_antwoord)
    assert parse_vakanties(None) == []


def test_filter_regio_neemt_heel_nederland_mee(api_antwoord: dict[str, Any]) -> None:
    zuid = filter_regio(parse_vakanties(api_antwoord), "zuid")
    assert [v.naam for v in zuid] == ["Herfstvakantie", "Kerstvakantie", "Voorjaarsvakantie"]


def _kalender(api_antwoord: dict[str, Any], **kwargs: Any) -> Schoolkalender:
    return Schoolkalender(filter_regio(parse_vakanties(api_antwoord), "midden"), **kwargs)


def test_is_vrij(api_antwoord: dict[str, Any]) -> None:
    k = _kalender(api_antwoord)
    assert k.is_vrij(date(2026, 10, 14)) is False  # woensdag, schooldag
    assert k.redenen(date(2026, 10, 19)) == ["Herfstvakantie"]
    assert k.redenen(date(2026, 10, 17)) == ["Herfstvakantie", "Weekend"]
    assert k.redenen(date(2026, 12, 25)) == ["Kerstvakantie", "Eerste Kerstdag"]
    assert k.redenen(date(2027, 5, 6)) == ["Hemelvaartsdag"]
    assert k.volgende_schooldag(date(2026, 10, 16)) == date(2026, 10, 26)


def test_weekend_uit(api_antwoord: dict[str, Any]) -> None:
    k = _kalender(api_antwoord, weekend_vrij=False)
    assert k.is_vrij(date(2026, 10, 10)) is False


def test_volgende_vakantie(api_antwoord: dict[str, Any]) -> None:
    k = _kalender(api_antwoord)
    assert k.volgende_vakantie(date(2026, 10, 13)).naam == "Herfstvakantie"
    assert k.volgende_vakantie(date(2026, 10, 20)).naam == "Kerstvakantie"


def test_vrije_dagen_voor_kalender(api_antwoord: dict[str, Any]) -> None:
    k = _kalender(api_antwoord)
    namen = [v.naam for v in k.vrije_dagen(date(2026, 12, 1), date(2027, 1, 31))]
    assert namen == ["Kerstvakantie", "Eerste Kerstdag", "Tweede Kerstdag", "Nieuwjaarsdag"]
