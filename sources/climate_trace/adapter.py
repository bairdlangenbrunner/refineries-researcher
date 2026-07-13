"""Climate TRACE oil-and-gas-refining adapter — v6 REST API asset layer.

Source: Climate TRACE (https://climatetrace.org), an independent coalition producing a
worldwide facility-level greenhouse-gas inventory. This adapter reads the `oil-and-gas-
refining` subsector asset list from the v6 API (one JSON call returns all ~728 refining
assets across ~110 countries). Independent of GEM -> citable (CC BY 4.0), Tier 2 (modeled/
compiled, industry-standard but estimated — one corroborating source, never authoritative).

JSON shape (top-level dict with `bbox` + `assets`; each asset):
  Id (int, stable)         -> source_id (stringified)
  Name                     -> name
  Country (ISO3)           -> iso3 + country
  AssetType                -> configuration (prefix-mapped to the controlled vocab)
  Centroid.Geometry        -> [lon, lat] (SRID 4326 — LON FIRST; do not transpose)
  EmissionsSummary[0]      -> Capacity (BBL per day, "Maximum refining capacity"), CapacityUnits
  Owners[].CompanyName     -> owner (first distinct; list repeats one owner per period)

⚠ Capacity is NAMEPLATE maximum in bbl/day (units 'bpd', /1000 = kbpd) — no tonnes/volume
unit trap. Capacity 0 is a sentinel -> normalizes to null. NO status field and NO start/retire
year exist in this dataset (only operating assets are carried), so both are left null.
"""

from __future__ import annotations


def _config(asset_type):
    """Map Climate TRACE process type -> GORT Configuration vocab (prefix match handles the
    finer API suffixes like 'Deep conversion Coking-FCC-GO-HC-6', 'Hydroskimming-0')."""
    if not asset_type:
        return None
    s = str(asset_type).strip().lower()
    if s.startswith("deep conversion") or s.startswith("deep-conversion"):
        return "deep conversion"
    if s.startswith("medium conversion") or s.startswith("medium-conversion"):
        return "medium conversion"
    if s.startswith("hydroskimming"):
        return "hydroskimming"
    if s.startswith("topping"):
        return "topping"
    return None


def _owner(owners):
    """First distinct CompanyName (the list repeats one owner per emissions period; JV
    assets list several)."""
    if not owners:
        return None
    for o in owners:
        name = (o or {}).get("CompanyName")
        if name and str(name).strip():
            return str(name).strip()
    return None


def _capacity(asset):
    """Maximum refining capacity in bbl/day from the (single) EmissionsSummary entry."""
    for e in asset.get("EmissionsSummary") or []:
        cap = e.get("Capacity")
        if cap is not None:
            return cap
    return None


def parse(manifest: dict, raw_path: str) -> list[dict]:
    import json

    with open(raw_path, encoding="utf-8") as fh:
        payload = json.load(fh)
    assets = payload.get("assets") if isinstance(payload, dict) else payload
    src_url = (manifest.get("location") or {}).get("url")

    out = []
    for a in assets or []:
        aid = a.get("Id")
        if aid is None:
            continue

        lat = lon = None
        geom = ((a.get("Centroid") or {}).get("Geometry")) or None
        if geom and len(geom) >= 2:
            lon, lat = geom[0], geom[1]          # [lon, lat] — do NOT transpose

        iso3 = a.get("Country")                  # API gives ISO3 only, no full country name

        out.append({
            "source_id": str(aid),
            "name": a.get("Name"),
            "owner": _owner(a.get("Owners")),
            "country": iso3,                     # source spelling == ISO3 code here
            "iso3": iso3,
            "subnational": None,
            "city": None,
            "latitude": lat,
            "longitude": lon,
            "capacity_value": _capacity(a),      # bbl/day; 0 -> null via capacity_normalize
            "capacity_units": "bpd",
            "status": None,                      # dataset has no lifecycle status
            "configuration": _config(a.get("AssetType")),
            "start_year": None,                  # dataset has no commissioning year
            "source_url": src_url,               # API endpoint — provenance only, not a [ref]
        })
    return out
