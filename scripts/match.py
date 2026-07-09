"""Match refinery records across canonical sources (or a source vs the master).

    python scripts/match.py --source ogj --against master --out batches/staging/match_ogj/
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
source vs the master). See docs/sops/build.md and docs/sops/reconciliation.md.

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
from paths import SOURCES, latest_master

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
    """match / possible / no from name (0-1), distance (km|None), cap_ratio (0-1|None).
    Coordinate proximity is the strongest signal; capacity upgrades a borderline pair but
    a capacity disagreement never rejects (sources disagree on capacity constantly)."""
    if dist_km is not None:
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
    # coordless fallback (rare — ~all rows have coords)
    if name >= 0.93:
        return "match"
    if name >= 0.80:
        return "possible"
    return "no"


# --- blocking + pairwise match ------------------------------------------------------- #
def _project(df: "pd.DataFrame"):
    """Equirectangular projection (per-point cos(lat)) to degrees for cKDTree blocking."""
    lat = pd.to_numeric(df["latitude"], errors="coerce")
    lon = pd.to_numeric(df["longitude"], errors="coerce")
    x = lon * lat.map(lambda v: cos(radians(v)) if pd.notna(v) else 0.0)
    y = lat
    ok = lat.notna() & lon.notna()
    return x, y, ok


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

    if bok.any() and aok.any():
        b_pts = list(zip(bx[bok], by[bok]))
        b_idx_map = b.index[bok].to_list()
        tree = cKDTree(b_pts)
        for ai in a.index[aok]:
            neigh = tree.query_ball_point((ax[ai], ay[ai]), radius_deg)
            for nj in neigh:
                bi = b_idx_map[nj]
                la, lo = _num(a.at[ai, "latitude"]), _num(a.at[ai, "longitude"])
                lb, ob = _num(b.at[bi, "latitude"]), _num(b.at[bi, "longitude"])
                dist = haversine_km(la, lo, lb, ob) if None not in (la, lo, lb, ob) else None
                nm = name_score(a_names[ai], b_names[bi])
                cr = capacity_ratio(a_cap[ai] if a_cap is not None else None,
                                    b_cap[bi] if b_cap is not None else None)
                label = classify(nm, dist, cr)
                if label != "no":
                    pairs.append(dict(
                        a_idx=int(ai), b_idx=int(bi),
                        a_id=a.at[ai, "source_id"], b_id=b.at[bi, "source_id"],
                        a_name=a.at[ai, "name"], b_name=b.at[bi, "name"],
                        name=nm, dist_km=round(dist, 3) if dist is not None else None,
                        cap_ratio=cr, label=label,
                    ))
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
    ap.add_argument("--against", default="master", help="'master' or another source name")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--block-km", type=float, default=25.0)
    args = ap.parse_args()

    src = load_canonical(args.source)
    if args.against == "master":
        mp = latest_master()
        if mp is None:
            sys.exit("No master yet (data/master_*.parquet). Build it first with merge.py.")
        against = pd.read_parquet(mp).rename(
            columns={"RefineryID": "source_id", "RefineryName": "name",
                     "CapacityInKbpd": "capacity_kbpd", "Latitude": "latitude",
                     "Longitude": "longitude"})
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
