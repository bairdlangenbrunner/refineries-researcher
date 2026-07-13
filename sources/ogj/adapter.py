"""OGJ Worldwide Refining Survey adapter — the WW Refining PDF (worldwide, ~577 rows).

This is the AUTHORITATIVE OGJ artifact: every refinery carries a country, plus Crude
distillation capacity (b/cd = kbpd) and a full downstream-unit breakdown. It supersedes
the Europe-only map-JSON export (preserved as adapter_mapjson.py) — the map JSON had
coordinates but no country, which left 55 rows country-less. Trade-off: the PDF has NO
coordinates. (Coordinate enrichment / a country+name blocking path in match.py is the
follow-up so these rows can dedup — see docs/PROJECT_SETUP_AND_CONTEXT.md A4.)

PDF structure (2022 survey):
  - Country section headers are ALL-CAPS and match the country table EXACTLY (exact match
    rejects wrapped company fragments like 'PJSC'/'ANK'). OGJ appends a stray ' 0' to some
    (e.g. 'CHINA (TAIWAN) 0') and labels Taiwan 'CHINA (TAIWAN)'.
  - Within UNITED STATES / CANADA, states/provinces are Title-Case subregion headers.
  - Each refinery: company/operator/name/location text (wraps 1-4 lines) then a data line
    ending in ~33 numeric columns; the FIRST number is Crude b/cd. Name segments are
    em/en-dash separated ('Company—Operator—Refinery—Location'); the last segment is the
    location (city), the first is the owner/parent company.
  - 'Total' / 'Total:' rows summarize each section (skipped).

Validation: parsed Crude sums reconcile with the PDF's per-section Total lines for every
section except three documented PDF-internal quirks (China ZPC Zhoushan lists two real
phases OGJ totals as one; South Africa excludes Natref/Sasolburg CTL; India off by 1 bpd).
"""

from __future__ import annotations
import re

try:
    import pdfplumber
    import pycountry
except ImportError:  # pragma: no cover
    raise SystemExit("ogj adapter needs pdfplumber + pycountry (pip install -r requirements.txt)")


# --- country header table (EXACT match; fuzzy would map company fragments to countries) --
def _country_lookup() -> dict:
    d = {}
    for c in pycountry.countries:
        for attr in ("name", "official_name", "common_name"):
            v = getattr(c, attr, None)
            if v:
                d[v.upper()] = c.alpha_3
    d.update({
        "TURKEY": "TUR", "SERBIA & MONTENEGRO": "SRB", "IVORY COAST": "CIV",
        "NETHERLANDS ANTILLES": "ANT", "SOUTH KOREA": "KOR", "NORTH KOREA": "PRK",
        "RUSSIA": "RUS", "TAIWAN": "TWN", "VENEZUELA": "VEN", "BOLIVIA": "BOL",
        "TANZANIA": "TZA", "SYRIA": "SYR", "UNITED STATES": "USA", "LAOS": "LAO",
        "BRUNEI": "BRN", "MOLDOVA": "MDA", "CZECH REPUBLIC": "CZE", "MARTINIQUE": "MTQ",
        "CHINA (TAIWAN)": "TWN",
    })
    return d


COUNTRY = _country_lookup()


def _iso_name(iso: str) -> str:
    c = pycountry.countries.get(alpha_3=iso)
    return getattr(c, "common_name", None) or (c.name if c else iso)


NAME_BY_ISO = {v: _iso_name(v) for v in set(COUNTRY.values())}
US_STATES = {s.name for s in pycountry.subdivisions.get(country_code="US")}
CA_PROV = {s.name for s in pycountry.subdivisions.get(country_code="CA")}

BANNER = re.compile(r"WORLDWIDE REFINING SURVEY|Thermal Processes|Catalytic|"
                    r"Company, operator|Country refinery|Oil & Gas Journal|"
                    r"desulfurization|Fluid coking|road oil|b/cd b/cd")
NUMTOK = re.compile(r"^\(?-?[\d,]+\.?\d*\)?$")
DASH = re.compile(r"[–—]")   # en/em dash — NOT hyphen (kept inside place names)


def _header_iso(line: str):
    """ISO3 if `line` is a country header (strip a trailing stray ' 0'), else None."""
    return COUNTRY.get(re.sub(r"\s+0$", "", line).strip())


def _num(tok: str):
    try:
        return float(tok.replace(",", "").strip("()"))
    except ValueError:
        return None


def _split_data(line: str):
    """If `line` ends in >=10 numeric tokens, return (name_tail, crude_bcd); else None.
    The >=10 threshold ignores stray numerics inside names (e.g. 'Phillips 66')."""
    toks = line.split()
    i = len(toks)
    while i > 0 and NUMTOK.match(toks[i - 1]):
        i -= 1
    if len(toks) - i < 10:
        return None
    return " ".join(toks[:i]), _num(toks[i])


def parse(manifest: dict, raw_path: str) -> list[dict]:
    with pdfplumber.open(raw_path) as pdf:
        raw = "\n".join((p.extract_text() or "") for p in pdf.pages)

    country = iso = subnat = None
    buf: list[str] = []
    rows: list[dict] = []
    seq: dict = {}
    for line in (l.strip() for l in raw.splitlines()):
        if not line or len(line) == 1 or BANNER.search(line):
            continue  # len==1 drops stray combining chars (Turkish 'Ş'/'ş' orphans)
        if re.match(r"Total[:\s]", line):        # section total (also 'Total:' / 'Total Ş ')
            buf = []
            continue
        hiso = _header_iso(line)
        if hiso:
            country, iso, subnat, buf = NAME_BY_ISO.get(hiso, hiso), hiso, None, []
            continue
        if country in ("United States", "Canada") and (line in US_STATES or line in CA_PROV):
            subnat, buf = line, []
            continue
        data = _split_data(line)
        if data is None:
            buf.append(line)                     # text continuation of a wrapping name
            continue
        name_tail, crude = data
        full = " ".join(buf + ([name_tail] if name_tail else [])).strip()
        buf = []
        if not full or country is None:
            continue
        segs = [s.strip() for s in DASH.split(full) if s.strip()]
        city = segs[-1] if segs else None
        owner = segs[0] if len(segs) > 1 else None
        seq[iso] = seq.get(iso, 0) + 1
        rows.append({
            "source_id": f"{iso}-{seq[iso]:02d}",   # deterministic, stable per PDF vintage
            "name": full,
            "owner": owner,
            "country": country,
            "iso3": iso,
            "subnational": subnat,
            "city": city,
            "capacity_value": crude,
            "capacity_units": "bpd",
            "latitude": None,
            "longitude": None,
            "status": None,
            "configuration": None,
            "start_year": None,
            "source_url": None,
        })
    return rows
