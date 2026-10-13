"""Feestdagen waarop scholen dicht zijn.

Bron: https://www.rijksoverheid.nl/themas/onderwijs/schoolvakanties/vrij-van-school-op-feestdagen

De Rijksoverheid heeft hier geen API voor. Daarom staan de feestdagen hier als
*regels* (geen losse datums), zodat ze voor elk jaar kloppen. Verandert de lijst
van de overheid, pas dan alleen NATIONALE_FEESTDAGEN of OPTIONELE_DAGEN aan.

Dit bestand gebruikt bewust geen Home Assistant-imports, zodat het los te testen is.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, timedelta


def pasen(jaar: int) -> date:
    """Eerste Paasdag (Gregoriaanse kalender, anonieme algoritme van Meeus/Jones/Butcher)."""
    a = jaar % 19
    b, c = divmod(jaar, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    maand, dag = divmod(h + l - 7 * m + 114, 31)
    return date(jaar, maand, dag + 1)


def _vast(maand: int, dag: int) -> Callable[[int], date]:
    return lambda jaar: date(jaar, maand, dag)


def _na_pasen(dagen: int) -> Callable[[int], date]:
    return lambda jaar: pasen(jaar) + timedelta(days=dagen)


def _koningsdag(jaar: int) -> date:
    """27 april, of 26 april als 27 april op zondag valt."""
    dag = date(jaar, 4, 27)
    return dag - timedelta(days=1) if dag.weekday() == 6 else dag


@dataclass(frozen=True)
class Feestdag:
    """Een feestdag als regel."""

    key: str
    naam: str
    datum: Callable[[int], date]


# Nationale feestdagen waarop scholen in principe dicht zijn.
NATIONALE_FEESTDAGEN: tuple[Feestdag, ...] = (
    Feestdag("nieuwjaarsdag", "Nieuwjaarsdag", _vast(1, 1)),
    Feestdag("tweede_paasdag", "Tweede Paasdag", _na_pasen(1)),
    Feestdag("koningsdag", "Koningsdag", _koningsdag),
    Feestdag("bevrijdingsdag", "Bevrijdingsdag", _vast(5, 5)),
    Feestdag("hemelvaartsdag", "Hemelvaartsdag", _na_pasen(39)),
    Feestdag("tweede_pinksterdag", "Tweede Pinksterdag", _na_pasen(50)),
    Feestdag("eerste_kerstdag", "Eerste Kerstdag", _vast(12, 25)),
    Feestdag("tweede_kerstdag", "Tweede Kerstdag", _vast(12, 26)),
)

# Dagen die scholen zelf mogen vrijgeven. De gebruiker zet ze aan in de opties.
OPTIONELE_DAGEN: tuple[Feestdag, ...] = (
    Feestdag("goede_vrijdag", "Goede Vrijdag", _na_pasen(-2)),
    Feestdag("dag_na_hemelvaart", "Vrijdag na Hemelvaart", _na_pasen(40)),
)

OPTIONELE_KEYS: tuple[str, ...] = tuple(f.key for f in OPTIONELE_DAGEN)


def feestdagen_in_jaar(
    jaar: int,
    *,
    nationaal: bool = True,
    optioneel: Iterable[str] = (),
) -> dict[date, str]:
    """Geef {datum: naam} voor alle schoolvrije feestdagen in een jaar."""
    gekozen = set(optioneel)
    regels = list(NATIONALE_FEESTDAGEN) if nationaal else []
    regels += [f for f in OPTIONELE_DAGEN if f.key in gekozen]
    resultaat: dict[date, str] = {}
    for regel in regels:
        resultaat.setdefault(regel.datum(jaar), regel.naam)
    return resultaat
