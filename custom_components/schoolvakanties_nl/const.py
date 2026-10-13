"""Constanten voor Schoolvakanties Nederland."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "schoolvakanties_nl"
NAME: Final = "Schoolvakanties Nederland"

# Configuratie
CONF_REGION: Final = "region"
CONF_FEESTDAGEN: Final = "feestdagen"
CONF_OPTIONELE_DAGEN: Final = "optionele_dagen"
CONF_WEEKEND: Final = "weekend_vrij"

REGIONS: Final = ["noord", "midden", "zuid"]
REGIO_HEEL_NEDERLAND: Final = "heel nederland"

DEFAULT_FEESTDAGEN: Final = True
DEFAULT_WEEKEND: Final = True

# Bronnen
SCHOOLVAKANTIES_URL: Final = (
    "https://opendata.rijksoverheid.nl/v1/infotypes/schoolholidays/schoolyear/{schooljaar}"
)
PDOK_REVERSE_URL: Final = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/reverse"
PDOK_LOOKUP_URL: Final = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/lookup"
BRON_PAGINA: Final = (
    "https://www.rijksoverheid.nl/themas/onderwijs/schoolvakanties/"
    "overzicht-schoolvakanties-per-schooljaar"
)

TIJDZONE: Final = "Europe/Amsterdam"
UPDATE_INTERVAL: Final = timedelta(hours=12)
REQUEST_TIMEOUT: Final = 20

STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = f"{DOMAIN}.vakanties"
