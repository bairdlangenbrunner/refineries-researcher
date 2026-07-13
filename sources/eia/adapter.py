"""U.S. EIA Refinery Capacity Report adapter — Form EIA-820, per-refinery workbook.

Source: EIA "Refinery Capacity Report", the per-refinery workbook
`https://www.eia.gov/petroleum/refinerycapacity/refcap{YY}.xlsx` (data as of Jan 1 of the
edition year). U.S. federal public domain; EIA is NOT a GEM surface, so it is citable.
Authoritative for U.S. crude refineries' atmospheric-crude-distillation capacity, operator,
site, PADD/state, operable-vs-idle status, and the full downstream-unit slate.

Two-file join:
  1. refcap{YY}.xlsx  — capacity/operator/status (current vintage). LONG/tidy layout: one
     row per (refinery x PRODUCT x SUPPLY measure), single header row 0. There is NO
     latitude/longitude and NO facility name distinct from operator+site.
  2. Petroleum_Refineries_US_EIA.zip — the EIA US Energy Atlas GIS layer (shapefile,
     EPSG:4326), joined ONLY for Latitude/Longitude. It lags the workbook (2021 vintage),
     so some sites won't join → coords left null (never fabricated).

The workbook groups on (CORPORATION, COMPANY_NAME, STATE_NAME, SITE). A refinery's crude
capacity is the `PRODUCT == 'TOTAL OPERABLE CAPACITY'` row whose `SUPPLY` contains
'Atmospheric Crude Distillation ... barrels per calendar day' (whole barrels -> bpd).
Status is DERIVED from the OPERATING/IDLE/TOTAL-OPERABLE trio, not a status column.

⚠ SCOPE: the report includes a handful of downstream-only sites (petrochemical/lube/NGL
complexes) that report cracking/alkylation/desulf units but have NO atmospheric crude
distillation. Those are out of scope for a crude-refinery tracker, so this adapter EXCLUDES
sites with no crude-distillation capacity and records them in `parse.excluded` for review
(surfaced by ingest, not silently dropped). Coordinates use b/cd (calendar day).
"""

from __future__ import annotations
import re
from pathlib import Path

try:
    import pandas as pd
    import geopandas as gpd
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    raise SystemExit("eia adapter needs pandas + geopandas + rapidfuzz (pip install -r requirements.txt)")

KEYS = ["CORPORATION", "COMPANY_NAME", "STATE_NAME", "SITE"]
CRUDE_LABEL = "Atmospheric Crude Distillation"

# USPS abbrev per full state name, for readable deterministic source ids (EIA-TX-01, ...).
_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN",
    "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}


def _num(v):
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def _cd_capacity(rows: "pd.DataFrame", product: str):
    """First QUANTITY for a PRODUCT whose SUPPLY is the b/cd atmospheric-crude measure."""
    m = (rows["PRODUCT"] == product) & \
        rows["SUPPLY"].str.contains(CRUDE_LABEL, na=False) & \
        rows["SUPPLY"].str.contains("calendar day", na=False)
    for q in rows.loc[m, "QUANTITY"]:
        n = _num(q)
        if n is not None:
            return n
    return None


def _coord_index(gis_zip: str):
    """(site_upper, state_upper) -> list of {lat, lon, company, corp, ad_bcd} GIS candidates."""
    g = gpd.read_file(gis_zip)
    idx: dict = {}
    for _, r in g.iterrows():
        site = str(r.get("Site") or "").upper().strip()
        state = str(r.get("State") or "").upper().strip()
        ad = _num(r.get("AD_Mbpd"))
        idx.setdefault((site, state), []).append({
            "lat": _num(r.get("Latitude")), "lon": _num(r.get("Longitude")),
            "company": str(r.get("Company") or ""), "corp": str(r.get("Corp") or ""),
            "ad_bcd": ad * 1000 if ad is not None else None,   # Mbpd (thousand b/cd) -> b/cd
        })
    return idx


def _pick_coord(cands: list, company: str, corp: str, cap_bcd, used: set):
    """Choose the best unused GIS candidate for a workbook site within a (site,state) group.

    Co-located refineries differ in operator and size, so score = operator-name similarity
    (rapidfuzz) + capacity closeness (2021 GIS vs current workbook, so a soft signal)."""
    best, best_score = None, -1.0
    for i, c in enumerate(cands):
        if i in used or c["lat"] is None or c["lon"] is None:
            continue
        nm = max(fuzz.token_set_ratio(company, c["company"]),
                 fuzz.token_set_ratio(corp, c["corp"])) / 100.0
        if cap_bcd and c["ad_bcd"]:
            lo, hi = sorted((cap_bcd, c["ad_bcd"]))
            cap = lo / hi if hi else 0
        else:
            cap = 0.0
        score = 0.6 * nm + 0.4 * cap
        if score > best_score:
            best, best_score = i, score
    if best is not None:
        used.add(best)
        return cands[best]["lat"], cands[best]["lon"]
    return None, None


def parse(manifest: dict, raw_path: str) -> list[dict]:
    df = pd.read_excel(raw_path, sheet_name=0)

    # coordinate side-file: manifest.location.coords_path (repo-root relative), optional
    coords_rel = (manifest.get("location") or {}).get("coords_path")
    gidx = {}
    if coords_rel:
        gzip = Path(coords_rel)
        gzip = gzip if gzip.is_absolute() else (Path(__file__).resolve().parents[2] / gzip)
        if gzip.exists():
            gidx = _coord_index(str(gzip))

    edition = int(df["PERIOD"].iloc[0]) if "PERIOD" in df.columns and len(df) else None
    src_url = (manifest.get("location") or {}).get("url")

    out, excluded = [], []
    used_coords: dict = {}   # (site,state) -> set of GIS-candidate indices already claimed
    seq: dict = {}           # state abbrev -> running counter for source ids

    for key, rows in df.groupby(KEYS, sort=True):
        corp, company, state, site = key
        total = _cd_capacity(rows, "TOTAL OPERABLE CAPACITY")
        operating = _cd_capacity(rows, "OPERATING CAPACITY")
        idle = _cd_capacity(rows, "IDLE CAPACITY")

        if total is None and operating is None and idle is None:
            excluded.append({"company": company, "site": site, "state": state,
                             "reason": "no atmospheric crude distillation capacity",
                             "units": sorted(rows["PRODUCT"].unique())})
            continue

        cap_bcd = total if total is not None else operating
        # status: fully idle when there's operable/idle capacity but no operating capacity
        if operating and operating > 0:
            status = "operating"
        elif (idle and idle > 0) or (total and total > 0):
            status = "idle"
        else:
            status = None

        site_t = str(site).title()
        state_t = str(state).strip()
        abbr = _ABBR.get(state_t, re.sub(r"[^A-Z]", "", str(state).upper())[:2] or "US")
        seq[abbr] = seq.get(abbr, 0) + 1
        source_id = f"EIA-{abbr}-{seq[abbr]:02d}"

        lat = lon = None
        if gidx:
            gk = (str(site).upper().strip(), str(state).upper().strip())
            lat, lon = _pick_coord(gidx.get(gk, []), str(company), str(corp),
                                   cap_bcd, used_coords.setdefault(gk, set()))

        out.append({
            "source_id": source_id,
            "name": site_t,                 # EIA has no facility name; site is the discriminator
            "owner": str(company).strip() or None,
            "country": "United States",
            "iso3": "USA",
            "subnational": state_t or None,
            "city": site_t or None,
            "latitude": lat,
            "longitude": lon,
            "capacity_value": cap_bcd,      # atmospheric crude distillation, b/cd, whole barrels
            "capacity_units": "bpd",
            "status": status,
            "configuration": None,          # derivable from downstream units later, not now
            "start_year": None,
            "source_url": src_url,
        })

    parse.excluded = excluded               # attach for ingest/summary to surface
    parse.edition = edition
    return out
