"""Match refinery records across canonical sources (or a source vs the main).

    python scripts/match.py --source ogj --against main --out batches/staging/match_ogj/
    python scripts/match.py --source ogj --against rmi     --out batches/staging/match_ogj_rmi/

Hybrid point-feature matcher. Refineries are points, so geometry is a haversine
distance (not route overlap). Blocking is COORDINATE-based (scipy cKDTree) because the
sources have uneven country fields (ogj/china carry none) but ~100% coordinates. Each
candidate pair is scored on:
  - name similarity  (rapidfuzz token_set_ratio, after stripping refinery/owner boilerplate)
  - coordinate distance (haversine km)
  - capacity_kbpd ratio (min/max) — corroboration + conflict flag, NOT a hard gate
and labelled match / possible / no.

Reused by BOTH build (merge.py clusters across all sources) and reconciliation (one
source vs the main). See docs/sops/build.md and docs/sops/reconciliation.md.

Coordinate note: WKT is lon-first `POINT(lon lat)`; OGJ position is `[lat, lon]` — both
are already resolved to canonical latitude/longitude columns at ingest, so this module
always reads plain `latitude`/`longitude`.
"""

from __future__ import annotations
import argparse
import json
import re
import sys
import unicodedata
from math import radians, sin, cos, asin, sqrt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # runnable from repo root
from paths import SOURCES, latest_main

try:
    import pandas as pd
    from rapidfuzz import fuzz
    from scipy.spatial import cKDTree
except ImportError:  # pragma: no cover
    sys.exit("match.py needs pandas + rapidfuzz + scipy (pip install -r requirements.txt)")


# --- distance ------------------------------------------------------------------------ #
def haversine_km(lat1, lon1, lat2, lon2) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


# --- name normalization -------------------------------------------------------------- #
# Generic tokens stripped before fuzzy comparison so the distinctive part dominates.
_BOILERPLATE = {
    "refinery", "refineries", "refining", "refinaria", "refineria", "raffinerie",
    "petrochemical", "petrochemicals", "petrochem", "petroleum", "petroleo", "oil",
    "company", "co", "ltd", "limited", "llc", "plc", "inc", "corporation", "corp",
    "group", "grp", "holdings", "holding", "sa", "spa", "sarl", "gmbh", "ag", "bv",
    "nv", "as", "pjsc", "jsc", "ojsc", "pt", "tbk", "sdn", "bhd", "the", "and",
    "complex", "plant", "works", "industries", "industrial", "energy", "energie",
}


def normalize_name(name) -> str:
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c))   # drop diacritics
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)                          # keep alnum + space
    toks = [t for t in s.split() if t and t not in _BOILERPLATE]
    return " ".join(toks).strip()


def _num(v):
    try:
        f = float(v)
        return f if f == f else None   # drop NaN
    except (TypeError, ValueError):
        return None


# --- scoring ------------------------------------------------------------------------- #
def name_score(a_norm: str, b_norm: str) -> float:
    if not a_norm or not b_norm:
        return 0.0
    return round(fuzz.token_set_ratio(a_norm, b_norm) / 100.0, 3)


def capacity_ratio(a_kbpd, b_kbpd):
    a, b = _num(a_kbpd), _num(b_kbpd)
    if not a or not b:
        return None
    lo, hi = min(a, b), max(a, b)
    return round(lo / hi, 3) if hi > 0 else None


def classify(name: float, dist_km, cap_ratio) -> str:
    """match / possible / no for a COORDINATE-blocked pair, from name (0-1), distance (km),
    cap_ratio (0-1|None). Coordinate proximity is the strongest signal; capacity upgrades a
    borderline pair but a capacity disagreement never rejects (sources disagree constantly).

    The coordless (country-blocked) path does NOT use this — it goes through
    `_country_labels` + greedy 1:1 assignment in match_sources (name alone can't separate
    two refineries in one city; see docs A4)."""
    if dist_km is None:
        return "no"
    if dist_km > 25.0:
        return "no"
    if dist_km <= 1.0 and name >= 0.55:
        return "match"
    if dist_km <= 5.0 and name >= 0.80:
        return "match"
    if dist_km <= 2.0 and name >= 0.85:   # near-identical name, ~coincident point
        return "match"
    # capacity can lift a borderline spatial+name pair
    if dist_km <= 5.0 and name >= 0.55 and (cap_ratio or 0) >= 0.9:
        return "match"
    if dist_km <= 10.0 and name >= 0.45:
        return "possible"
    if dist_km <= 2.0:                     # coincident but weak name — flag for review
        return "possible"
    return "no"


def _country_labels(name: float, cap_ratio) -> "tuple[bool, bool]":
    """(match_ok, possible_ok) for a COUNTRY-blocked pair — no distance signal.

    Within a country, name alone can't tell two refineries apart: after boilerplate strip,
    a short source name ('CORPUS CHRISTI') is a token-subset of OGJ's long
    'owner—operator—city' string, so token_set_ratio pins to 1.0 for every same-city row.
    Capacity is therefore REQUIRED to confirm a match; name alone only earns `possible`
    (review). These booleans feed the greedy 1:1 assignment in match_sources."""
    cr = cap_ratio or 0
    match_ok = (name >= 0.85 and cr >= 0.90) or (name >= 0.72 and cr >= 0.95)
    possible_ok = (name >= 0.85) or (name >= 0.72 and cr >= 0.80)
    return match_ok, possible_ok


# --- blocking + pairwise match ------------------------------------------------------- #
def _project(df: "pd.DataFrame"):
    """Equirectangular projection (per-point cos(lat)) to degrees for cKDTree blocking."""
    lat = pd.to_numeric(df["latitude"], errors="coerce")
    lon = pd.to_numeric(df["longitude"], errors="coerce")
    x = lon * lat.map(lambda v: cos(radians(v)) if pd.notna(v) else 0.0)
    y = lat
    ok = lat.notna() & lon.notna()
    return x, y, ok


def _country_key(df: "pd.DataFrame") -> "pd.Series":
    """One ISO3 blocking key per row for the coordless path. Sources spell countries
    incompatibly (OGJ has ISO3 'ARG'; OGIM has UPPERCASE names 'ARGENTINA' and no ISO3),
    so resolve BOTH to ISO3 via country_normalize. Falls back to a normalized name only if
    the country can't be resolved. Tolerates canonical (`iso3`/`country`) and main-renamed
    (`ISO3`/`Country`) frames. Rows with no country get None (never block-matched)."""
    from country_normalize import canonical_country
    iso = df.get("iso3", df.get("ISO3"))
    ctry = df.get("country", df.get("Country"))

    def key(i):
        v = iso.iloc[i] if iso is not None else None
        if v is not None and not (isinstance(v, float) and pd.isna(v)) and str(v).strip():
            return str(v).strip().upper()
        c = ctry.iloc[i] if ctry is not None else None
        if c is not None and not (isinstance(c, float) and pd.isna(c)) and str(c).strip():
            _, i3 = canonical_country(c)
            return i3 or (re.sub(r"[^A-Z0-9]", "", str(c).upper()) or None)
        return None

    return pd.Series([key(i) for i in range(len(df))], index=df.index)


def match_sources(df_a: "pd.DataFrame", df_b: "pd.DataFrame", *, block_km: float = 25.0):
    """Return a DataFrame of candidate pairs (label match/possible) between df_a and df_b.

    Columns: a_idx, b_idx, a_id, b_id, a_name, b_name, name, dist_km, cap_ratio, label.
    Blocking radius `block_km` in degrees ≈ block_km/111. Only match/possible rows are kept.
    """
    a = df_a.reset_index(drop=True)
    b = df_b.reset_index(drop=True)
    ax, ay, aok = _project(a)
    bx, by, bok = _project(b)

    a_names = a["name"].map(normalize_name)
    b_names = b["name"].map(normalize_name)
    a_cap = a.get("capacity_kbpd")
    b_cap = b.get("capacity_kbpd")

    radius_deg = block_km / 111.0
    pairs = []

    def _cap(ai, bi):
        return capacity_ratio(a_cap[ai] if a_cap is not None else None,
                              b_cap[bi] if b_cap is not None else None)

    def _emit(ai, bi, dist, nm, cr, label):
        pairs.append(dict(
            a_idx=int(ai), b_idx=int(bi),
            a_id=a.at[ai, "source_id"], b_id=b.at[bi, "source_id"],
            a_name=a.at[ai, "name"], b_name=b.at[bi, "name"],
            name=nm, dist_km=round(dist, 3) if dist is not None else None,
            cap_ratio=cr, label=label,
        ))

    # (1) COORDINATE blocking — both sides have coords (cKDTree within block_km).
    if bok.any() and aok.any():
        b_pts = list(zip(bx[bok], by[bok]))
        b_idx_map = b.index[bok].to_list()
        tree = cKDTree(b_pts)
        for ai in a.index[aok]:
            for nj in tree.query_ball_point((ax[ai], ay[ai]), radius_deg):
                bi = b_idx_map[nj]
                la, lo = _num(a.at[ai, "latitude"]), _num(a.at[ai, "longitude"])
                lb, ob = _num(b.at[bi, "latitude"]), _num(b.at[bi, "longitude"])
                dist = haversine_km(la, lo, lb, ob) if None not in (la, lo, lb, ob) else None
                nm = name_score(a_names[ai], b_names[bi])
                cr = _cap(ai, bi)
                label = classify(nm, dist, cr)
                if label != "no":
                    _emit(ai, bi, dist, nm, cr, label)

    # (2) COUNTRY blocking — for pairs the coord pass can't reach because >=1 side has no
    # coords (e.g. the OGJ WW PDF). Name alone over-matches within a country (every same-city
    # row scores ~1.0), so instead of independent pairwise labels we run a GREEDY 1:1
    # ASSIGNMENT on a name+capacity composite: each row on both sides gets at most one match.
    # Unmatched a-rows keep their surviving candidates as `possible` (a focused review queue).
    if (~aok).any() or (~bok).any():
        a_key, b_key = _country_key(a), _country_key(b)
        b_by_country: dict = {}
        for bi in b.index:
            k = b_key[bi]
            if k is not None:
                b_by_country.setdefault(k, []).append(bi)

        cand = []  # (score, ai, bi, nm, cr, match_ok)
        for ai in a.index:
            k = a_key[ai]
            if k is None:
                continue
            for bi in b_by_country.get(k, ()):
                if aok[ai] and bok[bi]:
                    continue          # both have coords -> handled by the coord pass
                nm = name_score(a_names[ai], b_names[bi])
                cr = _cap(ai, bi)
                match_ok, possible_ok = _country_labels(nm, cr)
                if not possible_ok:
                    continue
                # capacity breaks name ties: 0.6*name + 0.4*capacity (missing cap = 0)
                score = 0.6 * nm + 0.4 * (cr or 0)
                cand.append((score, int(ai), int(bi), nm, cr, match_ok))

        cand.sort(key=lambda t: -t[0])
        used_a, used_b, matched_a = set(), set(), set()
        for score, ai, bi, nm, cr, match_ok in cand:           # phase 1: greedy 1:1 matches
            if match_ok and ai not in used_a and bi not in used_b:
                _emit(ai, bi, None, nm, cr, "match")
                used_a.add(ai); used_b.add(bi); matched_a.add(ai)
        for score, ai, bi, nm, cr, match_ok in cand:           # phase 2: possibles, unmatched a
            if ai not in matched_a:
                _emit(ai, bi, None, nm, cr, "possible")

    cols = ["a_idx", "b_idx", "a_id", "b_id", "a_name", "b_name",
            "name", "dist_km", "cap_ratio", "label"]
    return pd.DataFrame(pairs, columns=cols)


def load_canonical(name: str) -> "pd.DataFrame":
    p = SOURCES / name / "canonical.parquet"
    if not p.exists():
        sys.exit(f"No canonical parquet for {name!r} — run scripts/ingest.py --source {name}")
    return pd.read_parquet(p)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--against", default="main", help="'main' or another source name")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--block-km", type=float, default=25.0)
    args = ap.parse_args()

    src = load_canonical(args.source)
    if args.against == "main":
        mp = latest_main()
        if mp is None:
            sys.exit("No main yet (data/main_*.parquet). Build it first with merge.py.")
        against = pd.read_parquet(mp).rename(
            columns={"RefineryID": "source_id", "RefineryName": "name",
                     "CapacityInKbpd": "capacity_kbpd", "Latitude": "latitude",
                     "Longitude": "longitude", "Country": "country", "ISO3": "iso3"})
    else:
        against = load_canonical(args.against)

    m = match_sources(src, against, block_km=args.block_km)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    m.to_parquet(out / "matches.parquet", index=False)
    summary = {
        "source": args.source, "against": args.against,
        "source_rows": len(src), "against_rows": len(against),
        "match": int((m["label"] == "match").sum()),
        "possible": int((m["label"] == "possible").sum()),
        "source_unmatched": int(len(src) - m.loc[m["label"] == "match", "a_idx"].nunique()),
    }
    (out / "match_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"match {args.source} vs {args.against}: "
          f"{summary['match']} match, {summary['possible']} possible, "
          f"{summary['source_unmatched']} source-unmatched -> {out}")


if __name__ == "__main__":
    main()
