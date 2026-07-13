"""GEM Global Chemicals Inventory (GCI) adapter — the refinery-candidate overlay.

Source: Global Energy Monitor, Global Chemicals Inventory, November 2025 (V1) — the
plant-level `.xlsx` ("Plant data" tab), 868 operating chemical plants worldwide that make
any of 8 tracked chemicals (ethylene, propylene, butadiene, benzene, toluene, xylene,
methanol, ammonia). Each row has point coordinates, owner (+ GEM entity ID), feedstock,
and primary/secondary products.

⚠ GEM SURFACE -> Standing Rule #1: this is SEED/OVERLAY data, NEVER a citation. And it is a
CHEMICALS inventory, so the overwhelming majority of rows are standalone petrochemical
plants that are OUT OF SCOPE for a refinery tracker. This adapter therefore FILTERS the 868
plants down to plausible refinery candidates and drops the rest (recorded as an aggregate
count on parse.excluded_count, not a per-row list). A row is a candidate when either:
  (a) feedstock includes `crude oil` or `condensate`  — on-site crude distillation, i.e. a
      refinery or an integrated refinery-petrochemical complex; or
  (b) a secondary product is a genuine refined fuel (gasoline, diesel, jet fuel, kerosene,
      heating oil, gas oil, fuel oil, bitumen, asphalt, lubricant, marine fuel, petroleum
      coke, naphtha) — captures CTL/GTL/bio fuel plants and fuel-making complexes too.
Two false friends are neutralized before the fuel test: `diesel exhaust fluid` (DEF, a urea
product — not diesel) and `pyrolysis gasoline` (a steam-cracker byproduct — not refining).

Downstream: overlay-only (manifest merge is never), so this canonical parquet feeds
match.py + build_reconciliation_review.py, not merge.py. Matches confirm coverage; the
gem_gci_only sheet is the payload (refineries missing from the main). No capacity exists in
this dataset (capacity_kbpd stays null — corroborates existence/location, never capacity);
no status column (operating-only snapshot -> do not infer Status); no configuration.

Cell formats: the "Coordinates" cell is "latitude, longitude" (LAT FIRST, decimal degrees,
NOT WKT). "Owner (English)" may list several parties and "[NN%]" stakes -> keep the first
party, strip the bracketed stake. GEM plant ID (P10000014XXXX) is the source_id.
"""

from __future__ import annotations
import re

try:
    import openpyxl
except ImportError:  # pragma: no cover
    raise SystemExit("gem_gci adapter needs openpyxl (pip install -r requirements.txt)")

# Header -> column index is resolved by name (robust to column reordering between releases).
COLS = {
    "id": "GEM plant ID", "name": "Plant name (English)", "owner": "Owner (English)",
    "entity_id": "Owner GEM entity ID", "city": "Municipality", "subnational": "Subnational unit",
    "country": "Country/area", "iso3": "ISO3 code", "coords": "Coordinates",
    "accuracy": "Coordinate accuracy", "primary": "Primary products",
    "secondary": "Secondary products", "feedstock": "Feedstock",
}

CRUDE_FEEDSTOCKS = {"crude oil", "condensate"}
# Genuine refined-fuel products that mark a row as a refinery candidate (substring test).
REFINED_FUELS = (
    "gasoline", "diesel", "jet fuel", "kerosene", "heating oil", "gas oil", "fuel oil",
    "bitumen", "asphalt", "lubricant", "marine fuel", "petroleum coke", "naphtha",
)


def _feedstock_tokens(value) -> set:
    return {t.strip().lower() for t in re.split(r"[,;]", str(value or "")) if t.strip()}


def _refined_fuels(secondary) -> list:
    """Refined-fuel product tokens present, after removing two false friends: DEF (urea, not
    diesel) and pyrolysis gasoline (cracker byproduct, not refining)."""
    s = str(secondary or "").lower().replace("diesel exhaust fluid", "").replace("pyrolysis gasoline", "")
    return [f for f in REFINED_FUELS if f in s]


def _candidate_reason(feed_tokens: set, fuels: list) -> str | None:
    reasons = []
    crude = sorted(feed_tokens & CRUDE_FEEDSTOCKS)
    if crude:
        reasons.append(f"feedstock: {', '.join(crude)}")
    if fuels:
        reasons.append(f"refined-fuel product: {', '.join(fuels)}")
    return " | ".join(reasons) if reasons else None


def _coords(value):
    """'latitude, longitude' -> (lat, lon) floats; None on anything unparseable."""
    if value is None:
        return None, None
    m = re.findall(r"-?\d+\.?\d*", str(value))
    if len(m) < 2:
        return None, None
    try:
        return float(m[0]), float(m[1])
    except ValueError:
        return None, None


def _owner(value):
    """First listed party with its '[NN%]' stake stripped."""
    if not value:
        return None
    first = re.split(r"[;]", str(value))[0]
    first = re.sub(r"\[[^\]]*\]", "", first).strip()
    return first or None


def parse(manifest: dict, raw_path: str) -> list[dict]:
    loc = manifest.get("location", {})
    wb = openpyxl.load_workbook(raw_path, read_only=True, data_only=True)
    ws = wb[loc.get("sheet", "Plant data")]

    rows = ws.iter_rows(values_only=True)
    header = [str(c).strip() if c is not None else "" for c in next(rows)]
    idx = {key: header.index(col) for key, col in COLS.items() if col in header}
    missing = [col for key, col in COLS.items() if col not in header]
    if missing:
        raise SystemExit(f"gem_gci: expected columns missing from 'Plant data': {missing}")

    def cell(r, key):
        return r[idx[key]] if idx.get(key) is not None and idx[key] < len(r) else None

    out, excluded = [], 0
    for r in rows:
        if r is None or cell(r, "id") is None:
            continue
        feed_tokens = _feedstock_tokens(cell(r, "feedstock"))
        fuels = _refined_fuels(cell(r, "secondary"))
        reason = _candidate_reason(feed_tokens, fuels)
        if reason is None:                       # pure petrochemical -> out of scope, drop
            excluded += 1
            continue
        lat, lon = _coords(cell(r, "coords"))
        out.append({
            "source_id": str(cell(r, "id")).strip(),
            "name": (str(cell(r, "name")).strip() if cell(r, "name") else None),
            "owner": _owner(cell(r, "owner")),
            "country": (str(cell(r, "country")).strip() if cell(r, "country") else None),
            "iso3": (str(cell(r, "iso3")).strip() if cell(r, "iso3") else None),
            "subnational": (str(cell(r, "subnational")).strip() if cell(r, "subnational") else None),
            "city": (str(cell(r, "city")).strip() if cell(r, "city") else None),
            "latitude": lat,
            "longitude": lon,
            "capacity_value": None,              # GCI carries no capacity
            "capacity_units": None,
            "status": None,                      # operating-only snapshot; do not infer Status
            "configuration": None,
            "start_year": None,
            "source_url": None,                  # GEM surface -> never seed a [ref]; chase primary
        })

    parse.excluded_count = excluded              # aggregate only (surfaced in the summary/print)
    return out
