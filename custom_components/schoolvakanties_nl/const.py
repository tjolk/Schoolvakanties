"""Constants for Schoolvakanties Nederland."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "schoolvakanties_nl"
NAME: Final = "Schoolvakanties Nederland"

# Configuration keys. The string values are stored in existing config entries,
# so they must not change (they are Dutch for historical reasons).
CONF_REGION: Final = "region"
CONF_PUBLIC_HOLIDAYS: Final = "feestdagen"
CONF_EXTRA_DAYS_OFF: Final = "optionele_dagen"
CONF_WEEKEND: Final = "weekend_vrij"

# Region identifiers as used by the government API.
REGIONS: Final = ["noord", "midden", "zuid"]
REGION_WHOLE_COUNTRY: Final = "heel nederland"

DEFAULT_PUBLIC_HOLIDAYS: Final = True
DEFAULT_WEEKEND: Final = True

# Data sources
SCHOOL_HOLIDAYS_URL: Final = (
    "https://opendata.rijksoverheid.nl/v1/infotypes/schoolholidays/schoolyear/{school_year}"
)
PDOK_REVERSE_URL: Final = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/reverse"
PDOK_LOOKUP_URL: Final = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/lookup"
SOURCE_PAGE: Final = (
    "https://www.rijksoverheid.nl/themas/onderwijs/schoolvakanties/"
    "overzicht-schoolvakanties-per-schooljaar"
)

TIMEZONE: Final = "Europe/Amsterdam"
UPDATE_INTERVAL: Final = timedelta(hours=12)
REQUEST_TIMEOUT: Final = 20

STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = f"{DOMAIN}.holidays"
