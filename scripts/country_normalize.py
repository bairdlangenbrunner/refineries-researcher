"""Canonicalize country names + ISO3 codes across sources.

Sources spell countries differently — RMI uses short title-case ("Russia", "United
States"), OGIM uses UPPERCASE official names ("RUSSIAN FEDERATION", "UNITED STATES OF
AMERICA"), china_rmi_tracker carries none (implied China), OGJ carries none (Europe).
This fragments the geography and breaks per-country workflows, so the main stores ONE
canonical country name + ISO3.

`canonical_country(name)` -> (canonical_name, iso3) using pycountry with a small overrides
map for the common political/spelling variants pycountry's fuzzy search gets wrong or slow.
`iso3_to_name(iso3)` backfills a name when only the code is known (RMI has ISO3).
"""

from __future__ import annotations

try:
    import pycountry
except ImportError:  # pragma: no cover
    pycountry = None

# Variants pycountry misses or resolves wrong. Key is upper-cased, stripped input.
_OVERRIDES = {
    "RUSSIA": "RUS", "RUSSIAN FEDERATION": "RUS",
    "SOUTH KOREA": "KOR", "KOREA, SOUTH": "KOR", "REPUBLIC OF KOREA": "KOR",
    "NORTH KOREA": "PRK", "KOREA, NORTH": "PRK",
    "IRAN": "IRN", "SYRIA": "SYR", "VENEZUELA": "VEN", "BOLIVIA": "BOL",
    "TANZANIA": "TZA", "TAIWAN": "TWN", "VIETNAM": "VNM", "LAOS": "LAO",
    "MOLDOVA": "MDA", "BRUNEI": "BRN", "CZECH REPUBLIC": "CZE", "CZECHIA": "CZE",
    "TURKEY": "TUR", "TURKIYE": "TUR", "IVORY COAST": "CIV", "COTE D'IVOIRE": "CIV",
    "DEMOCRATIC REPUBLIC OF THE CONGO": "COD", "DR CONGO": "COD", "CONGO, DEM. REP.": "COD",
    "REPUBLIC OF THE CONGO": "COG", "CONGO": "COG",
    "UNITED STATES": "USA", "UNITED STATES OF AMERICA": "USA", "USA": "USA",
    "UNITED KINGDOM": "GBR", "UK": "GBR", "GREAT BRITAIN": "GBR",
    "TRINIDAD AND TOBAGO": "TTO", "TRINIDAD & TOBAGO": "TTO",
    "CURACAO": "CUW", "CURAÇAO": "CUW",
    "US VIRGIN ISLANDS": "VIR", "U.S. VIRGIN ISLANDS": "VIR",
}

_CACHE: dict = {}


def _iso3_name(iso3: str) -> str:
    if pycountry is None:
        return iso3
    c = pycountry.countries.get(alpha_3=iso3)
    if not c:
        return iso3
    return getattr(c, "common_name", None) or c.name


def iso3_to_name(iso3):
    if not iso3 or not str(iso3).strip():
        return None
    return _iso3_name(str(iso3).strip().upper())


def canonical_country(name):
    """Return (canonical_name, iso3) or (original, None) if unresolved."""
    if name is None or not str(name).strip():
        return None, None
    key = str(name).strip()
    if key in _CACHE:
        return _CACHE[key]
    up = key.upper()
    iso3 = _OVERRIDES.get(up)
    if iso3 is None and pycountry is not None:
        c = pycountry.countries.get(name=key) or pycountry.countries.get(name=key.title())
        if c is None:
            try:
                hits = pycountry.countries.search_fuzzy(key)
                c = hits[0] if hits else None
            except LookupError:
                c = None
        iso3 = c.alpha_3 if c else None
    result = (_iso3_name(iso3), iso3) if iso3 else (key, None)
    _CACHE[key] = result
    return result
