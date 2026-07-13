"""Turn a build's `possible` (non-clustered) pairs into a reviewable xlsx.

    python scripts/export_possible_review.py            # latest main's .possible.parquet
    python scripts/export_possible_review.py --main data/main_YYYYMMDD_HHMM_ET.parquet

`merge.py` writes candidate pairs it would NOT auto-cluster to main_<stamp>.possible.parquet
(name/capacity agree enough to flag, not enough to merge). This renders them side-by-side —
each side's name/country/city/capacity/coords — so a human can rule same-vs-different and
route confirmed merges back to the main by hand. It adds blank Decision/Notes columns and
never edits any data.

Decision vocab (put one per row): `merge` (same refinery), `separate` (distinct),
`unsure`. Sorted source_a, source_b, a_name, best candidate first — so all candidates for
one row sit together.
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # runnable from repo root
from paths import BATCHES, latest_main
from match import load_canonical

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    sys.exit("export_possible_review.py needs pandas + openpyxl (pip install -r requirements.txt)")


def _side(frames_by_id: dict, src: str, sid) -> dict:
    """Look up one canonical row by (source, source_id); return the review-relevant fields."""
    row = frames_by_id.get(src, {}).get(str(sid))
    if row is None:
        return {k: None for k in ("country", "city", "cap", "lat", "lon", "status", "owner")}
    return {
        "country": row.get("country"), "city": row.get("city"),
        "cap": row.get("capacity_kbpd"), "lat": row.get("latitude"),
        "lon": row.get("longitude"), "status": row.get("status"), "owner": row.get("owner"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", help="path to a main_*.parquet (default: latest)")
    ap.add_argument("--out", help="output xlsx (default: batches/refineries_possible_review_<stamp>.xlsx)")
    args = ap.parse_args()

    main = Path(args.main) if args.main else latest_main()
    if main is None or not main.exists():
        sys.exit("No main found — build one with scripts/merge.py first.")
    possible_path = main.with_suffix(".possible.parquet")
    if not possible_path.exists():
        sys.exit(f"No possible-pairs file next to the main ({possible_path.name}).")
    p = pd.read_parquet(possible_path)

    stamp = main.stem[len("main_"):]
    out = Path(args.out) if args.out else (BATCHES / f"refineries_possible_review_{stamp}.xlsx")
    out.parent.mkdir(parents=True, exist_ok=True)

    # index every referenced canonical source by source_id for side lookups
    sources = sorted(set(p["source_a"]) | set(p["source_b"]))
    frames_by_id: dict = {}
    for s in sources:
        df = load_canonical(s)
        df["source_id"] = df["source_id"].astype("string")
        frames_by_id[s] = {sid: row for sid, row in zip(df["source_id"], df.to_dict("records"))}

    rows = []
    for _, r in p.iterrows():
        a = _side(frames_by_id, r["source_a"], r["a_id"])
        b = _side(frames_by_id, r["source_b"], r["b_id"])
        rows.append({
            "source_a": r["source_a"], "source_b": r["source_b"],
            "a_name": r["a_name"], "b_name": r["b_name"],
            "a_country": a["country"], "b_country": b["country"],
            "a_city": a["city"], "b_city": b["city"],
            "a_cap_kbpd": a["cap"], "b_cap_kbpd": b["cap"],
            "name_score": r["name"], "dist_km": r["dist_km"], "cap_ratio": r["cap_ratio"],
            "a_coords": None if a["lat"] is None else f"{a['lat']},{a['lon']}",
            "b_coords": None if b["lat"] is None else f"{b['lat']},{b['lon']}",
            "a_id": r["a_id"], "b_id": r["b_id"],
            "Decision": None, "Notes": None,   # blank for the reviewer: merge / separate / unsure
        })
    review = pd.DataFrame(rows)
    # candidates for one a-row together, best first
    review = review.sort_values(
        ["source_a", "source_b", "a_name", "name_score", "cap_ratio"],
        ascending=[True, True, True, False, False]).reset_index(drop=True)

    with pd.ExcelWriter(out, engine="openpyxl") as xw:
        review.to_excel(xw, sheet_name="PossiblePairs", index=False)

    n_country = int(review["dist_km"].isna().sum())
    print(f"exported {len(review)} possible pairs "
          f"({n_country} country-blocked, {len(review) - n_country} coord-blocked) -> {out}")


if __name__ == "__main__":
    main()
