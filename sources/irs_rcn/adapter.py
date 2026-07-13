"""IRS "Active Fuel Refineries" registry adapter — the Refiner Control Number (RCN) PDF.

Source: IRS SB/SE list of facilities registered as refiners under IRC §4101 (Form 637
activity letter "S"), published at https://www.irs.gov/pub/irs-sbse/rcn-db.pdf. Snapshot
titled "Active Fuel Refineries @ <date>". US-only. A primary government registry — good
for corroborating a US facility's EXISTENCE, operator name, and street address, and for
DISCOVERING small/independent US refineries. It carries NO capacity, coordinates, status,
or configuration.

⚠ SCOPE: "fuel refinery" here is the TAX definition, far broader than a crude-oil refinery.
The list mixes gas plants, NGL fractionators, transmix processors, renewable-diesel/biodiesel
plants, an LNG liquefaction plant, and petrochemical units in with the genuine crude
refineries. This adapter does NOT scope-filter (superset-first, like every source); scope
triage happens downstream against docs' scope rules. It does emit a coarse `scope_hint`
in Notes-style form is NOT part of canonical — see reconciliation review instead.

PDF structure: a 6-column table (REFINERYNO, REFINERYNAME, REFINERYADDR, REFINERYCITY,
REFINERYST, REFINERYZIP), left-aligned. We segment by each column header's x0 rather than
by text order, because names/addresses wrap and run into neighbouring columns otherwise.
A row whose NO cell is not an RCN is a wrapped continuation of the row above (its addr/city
fold back up). The RCN itself encodes the state (R-00-<ST>-NNNN), so state is always known
even when the ST cell is blank.
"""

from __future__ import annotations
import re

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    raise SystemExit("irs_rcn adapter needs pdfplumber (pip install -r requirements.txt)")

RCN = re.compile(r"^R-\d\d-[A-Z]{2}-\d{4}$")
# Column left edges (x0) read from the header row; a word belongs to the last column
# whose left edge it clears. Left-aligned columns, so this is robust to wrapping.
BOUNDS = [(20.6, "no"), (95.5, "name"), (313.2, "addr"),
          (449.6, "city"), (546.7, "st"), (625.2, "zip")]
HEADERS = {"REFINERYNO", "REFINERYNAME", "REFINERYADDR", "REFINERYCITY", "REFINERYST", "REFINERYZIP"}

# USPS 2-letter -> state/territory name (for canonical `subnational`).
STATE = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
    "PR": "Puerto Rico", "VI": "U.S. Virgin Islands", "GU": "Guam",
}


def _col(x0: float) -> str:
    c = "no"
    for bx, name in BOUNDS:
        if x0 >= bx - 3:
            c = name
    return c


def parse(manifest: dict, raw_path: str) -> list[dict]:
    recs: list[dict] = []
    with pdfplumber.open(raw_path) as pdf:
        for page in pdf.pages:
            rows: dict = {}
            for w in page.extract_words():
                t = w["text"]
                if t.startswith("Active") or t in ("@",) or re.match(r"\d+/\d+/\d+", t) or t in HEADERS:
                    continue
                rows.setdefault(round(w["top"] / 3), []).append(w)
            for key in sorted(rows):
                cols = {"no": [], "name": [], "addr": [], "city": [], "st": [], "zip": []}
                for w in sorted(rows[key], key=lambda w: w["x0"]):
                    cols[_col(w["x0"])].append(w["text"])
                cell = {k: " ".join(v).strip() for k, v in cols.items()}
                if RCN.match(cell["no"]):
                    recs.append(cell)
                elif recs:                        # wrapped continuation -> fold into prior row
                    if cell["addr"]:
                        recs[-1]["addr"] = (recs[-1]["addr"] + " " + cell["addr"]).strip()
                    if cell["name"]:               # name that overflowed downward is really addr
                        recs[-1]["addr"] = (recs[-1]["addr"] + " " + cell["name"]).strip()
                    if cell["city"] and not recs[-1]["city"]:
                        recs[-1]["city"] = cell["city"]

    out = []
    for r in recs:
        st = r["st"] if len(r["st"]) == 2 else r["no"][5:7]   # fall back to the RCN's state
        out.append({
            "source_id": r["no"],
            "name": r["name"] or None,
            "owner": None,                          # facility name often IS the operator, but don't assert it
            "country": "United States",
            "iso3": "USA",
            "subnational": STATE.get(st, st) or None,
            "city": r["city"].title() if r["city"] else None,
            "capacity_value": None,
            "capacity_units": None,
            "latitude": None,
            "longitude": None,
            "status": None,                         # "active" = active TAX registration, not operating; don't fabricate
            "configuration": None,
            "start_year": None,
            "source_url": manifest.get("location", {}).get("url"),
        })
    return out
