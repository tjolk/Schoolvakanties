"""Schoolkalender: vakanties uit de API plus feestdagen en weekenden.

Bevat ook de parser voor de open data van de Rijksoverheid. Dit bestand gebruikt
geen Home Assistant-imports, zodat het los te testen is.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .const import REGIO_HEEL_NEDERLAND, TIJDZONE
from .feestdagen import feestdagen_in_jaar

_TZ = ZoneInfo(TIJDZONE)


@dataclass(frozen=True, order=True)
class Vakantie:
    """Eén schoolvakantie voor één regio. Begin en eind zijn inclusief."""

    begin: date
    eind: date
    naam: str
    regio: str
    schooljaar: str = ""
    verplicht: bool = False

    def bevat(self, dag: date) -> bool:
        return self.begin <= dag <= self.eind

    def als_dict(self) -> dict[str, Any]:
        return {
            "naam": self.naam,
            "begin": self.begin.isoformat(),
            "eind": self.eind.isoformat(),
            "regio": self.regio,
            "schooljaar": self.schooljaar,
            "verplicht": self.verplicht,
        }

    @classmethod
    def uit_dict(cls, data: dict[str, Any]) -> Vakantie:
        return cls(
            begin=date.fromisoformat(data["begin"]),
            eind=date.fromisoformat(data["eind"]),
            naam=data["naam"],
            regio=data["regio"],
            schooljaar=data.get("schooljaar", ""),
            verplicht=bool(data.get("verplicht", False)),
        )


@dataclass(frozen=True)
class VrijeDag:
    """Een dag (of periode) waarop er geen school is."""

    begin: date
    eind: date
    naam: str
    soort: str  # "vakantie" of "feestdag"


def schooljaar(dag: date) -> str:
    """Schooljaar waar een datum bij hoort, bijv. '2026-2027' (wissel op 1 augustus)."""
    start = dag.year if dag.month >= 8 else dag.year - 1
    return f"{start}-{start + 1}"


def relevante_schooljaren(dag: date) -> list[str]:
    """Vorig, huidig en volgend schooljaar. Zo valt de zomervakantie nooit buiten beeld."""
    start = int(schooljaar(dag)[:4])
    return [f"{j}-{j + 1}" for j in (start - 1, start, start + 1)]


def _datum(waarde: str) -> date:
    """Zet een API-tijdstempel om naar een Nederlandse kalenderdatum.

    De API geeft tijdstempels in UTC (bijv. '2026-10-17T00:00:00.000Z' of
    '2026-10-16T22:00:00.000Z'). Omzetten naar Europe/Amsterdam geeft in beide
    gevallen de juiste dag.
    """
    tijd = datetime.fromisoformat(waarde.strip())
    if tijd.tzinfo is not None:
        tijd = tijd.astimezone(_TZ)
    return tijd.date()


def _naar_bool(waarde: Any) -> bool:
    if isinstance(waarde, str):
        return waarde.strip().lower() == "true"
    return bool(waarde)


def parse_vakanties(data: Any) -> list[Vakantie]:
    """Parse een antwoord van de schoolvakantie-API naar Vakantie-objecten (alle regio's).

    Structuur: {content: [{schoolyear, vacations: [{type, compulsorydates,
    regions: [{region, startdate, enddate}]}]}]}. Een lijst van zulke objecten
    (het endpoint zonder schooljaar) wordt ook geaccepteerd.
    """
    documenten = data if isinstance(data, list) else [data]
    resultaat: set[Vakantie] = set()
    for document in documenten:
        if not isinstance(document, dict):
            continue
        for inhoud in document.get("content") or []:
            jaar = str(inhoud.get("schoolyear", "")).strip()
            for vakantie in inhoud.get("vacations") or []:
                naam = " ".join(str(vakantie.get("type", "")).split()) or "Schoolvakantie"
                verplicht = _naar_bool(vakantie.get("compulsorydates", False))
                for regio in vakantie.get("regions") or []:
                    try:
                        begin = _datum(regio["startdate"])
                        eind = _datum(regio["enddate"])
                    except (KeyError, TypeError, ValueError):
                        continue
                    resultaat.add(
                        Vakantie(
                            begin=begin,
                            eind=eind,
                            naam=naam,
                            regio=" ".join(str(regio.get("region", "")).lower().split()),
                            schooljaar=jaar,
                            verplicht=verplicht,
                        )
                    )
    return sorted(resultaat)


def filter_regio(vakanties: Iterable[Vakantie], regio: str) -> list[Vakantie]:
    """Houd vakanties over voor één regio, inclusief die voor heel Nederland."""
    return sorted(v for v in vakanties if v.regio in (regio, REGIO_HEEL_NEDERLAND))


@dataclass
class Schoolkalender:
    """Beantwoordt 'is er vandaag school?' voor één regio."""

    vakanties: list[Vakantie]
    feestdagen: bool = True
    optionele_dagen: tuple[str, ...] = ()
    weekend_vrij: bool = True
    _feestdag_cache: dict[int, dict[date, str]] = field(default_factory=dict, repr=False)

    def feestdagen_in_jaar(self, jaar: int) -> dict[date, str]:
        if jaar not in self._feestdag_cache:
            self._feestdag_cache[jaar] = feestdagen_in_jaar(
                jaar, nationaal=self.feestdagen, optioneel=self.optionele_dagen
            )
        return self._feestdag_cache[jaar]

    def vakantie_op(self, dag: date) -> Vakantie | None:
        return next((v for v in self.vakanties if v.bevat(dag)), None)

    def feestdag_op(self, dag: date) -> str | None:
        return self.feestdagen_in_jaar(dag.year).get(dag)

    def is_weekend(self, dag: date) -> bool:
        return dag.weekday() >= 5

    def redenen(self, dag: date) -> list[str]:
        """Alle redenen waarom een dag schoolvrij is (leeg = schooldag)."""
        redenen: list[str] = []
        if vakantie := self.vakantie_op(dag):
            redenen.append(vakantie.naam)
        if feestdag := self.feestdag_op(dag):
            redenen.append(feestdag)
        if self.weekend_vrij and self.is_weekend(dag):
            redenen.append("Weekend")
        return redenen

    def is_vrij(self, dag: date) -> bool:
        return bool(self.redenen(dag))

    def volgende_vakantie(self, dag: date) -> Vakantie | None:
        """Eerstvolgende vakantie die ná vandaag begint."""
        return next((v for v in self.vakanties if v.begin > dag), None)

    def volgende_schooldag(self, dag: date, max_dagen: int = 120) -> date | None:
        for i in range(1, max_dagen + 1):
            kandidaat = dag + timedelta(days=i)
            if not self.is_vrij(kandidaat):
                return kandidaat
        return None

    def vrije_dagen(self, begin: date, eind: date) -> Iterator[VrijeDag]:
        """Vakanties en feestdagen die (deels) tussen begin en eind vallen. Geen weekenden."""
        for vakantie in self.vakanties:
            if vakantie.eind >= begin and vakantie.begin <= eind:
                yield VrijeDag(vakantie.begin, vakantie.eind, vakantie.naam, "vakantie")
        for jaar in range(begin.year, eind.year + 1):
            for dag, naam in sorted(self.feestdagen_in_jaar(jaar).items()):
                if begin <= dag <= eind:
                    yield VrijeDag(dag, dag, naam, "feestdag")

    @property
    def laatste_bekende_dag(self) -> date | None:
        return max((v.eind for v in self.vakanties), default=None)
