"""Build a reconciliation review workbook: one registered source vs the current main.

    python scripts/build_reconciliation_review.py --source eia
    python scripts/build_reconciliation_review.py --source eia --out batches/refineries_eia_reconciliation_<stamp>.xlsx

Reads the source->main match (batches/staging/match_<source>/matches.parquet — run
`scripts/match.py --source <source> --against main` first), the source canonical, and
the latest main. Reduces the coordinate-pass fan-out (one source refinery can match
several nearby main rows in dense clusters) to ONE best match per source row (nearest,
then highest capacity agreement), and surfaces:

  - <SRC>_to_main  — best match per source row, with a capacity-conflict flag
  - Main_dedup     — source rows that matched >1 main row = main under-merge clusters
  - <SRC>_only       — source rows with no match = discovery candidates
  - Possible         — `possible`-labelled pairs for manual review

This is a REVIEW deliverable — never an applied edit (the agent never overwrites the
main). Per standing rule the internal RefineryID is NOT emitted; main rows are
identified by name + city + state + capacity + SourcesPresent. See docs/sops/reconciliation.md.
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import latest_main, BATCHES

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    sys.exit("build_reconciliation_review.py needs pandas + openpyxl (pip install -r requirements.txt)")

CAP_CONFLICT = 0.85   # matched pair whose capacity ratio is below this = worth a look


def _f(v):
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()

    mp = latest_main()
    if mp is None:
        sys.exit("No main yet (data/main_*.parquet).")
    stamp = mp.stem[len("main_"):]

    match_path = Path(f"batches/staging/match_{args.source}/matches.parquet")
    if not match_path.exists():
        sys.exit(f"No matches at {match_path} — run scripts/match.py --source {args.source} --against main first")

    pairs = pd.read_parquet(match_path)
    src = pd.read_parquet(Path("sources") / args.source / "canonical.parquet").set_index("source_id")
    mst = pd.read_parquet(mp).set_index("RefineryID")

    def mrow(rid):
        return mst.loc[rid] if rid in mst.index else None

    def m_ident(rid) -> dict:
        b = mrow(rid)
        if b is None:
            return {}
        return {
            "main_name": b.get("RefineryName"), "main_city": b.get("City"),
            "main_state": b.get("Subnational"), "main_cap_kbpd": _f(b.get("CapacityInKbpd")),
            "main_status": b.get("Status"), "main_sources": b.get("SourcesPresent"),
        }

    def s_ident(sid) -> dict:
        o = src.loc[sid] if sid in src.index else None
        if o is None:
            return {}
        return {
            f"{args.source}_id": sid, f"{args.source}_owner": o.get("owner"),
            f"{args.source}_city": o.get("city"), f"{args.source}_state": o.get("subnational"),
            f"{args.source}_cap_kbpd": _f(o.get("capacity_kbpd")), f"{args.source}_status": o.get("status"),
        }

    matches = pairs[pairs.label == "match"].copy()
    possibles = pairs[pairs.label == "possible"].copy()

    # best main match per source row: nearest (NaN distance last), then highest cap agreement
    matches["_d"] = matches["dist_km"].map(lambda v: _f(v) if _f(v) is not None else 1e9)
    matches["_c"] = matches["cap_ratio"].map(lambda v: _f(v) or 0.0)
    matches = matches.sort_values(["a_id", "_d", "_c"], ascending=[True, True, False])
    best = matches.drop_duplicates("a_id", keep="first")
    n_main = matches.groupby("a_id")["b_id"].nunique()

    # --- <SRC>_to_main: one row per matched source refinery ---
    recon = []
    for _, r in best.iterrows():
        row = {**s_ident(r["a_id"]), "match_dist_km": _f(r["dist_km"]),
               "name_score": _f(r["name"]), "cap_ratio": _f(r["cap_ratio"]), **m_ident(r["b_id"])}
        cr = _f(r["cap_ratio"])
        row["cap_flag"] = "conflict" if (cr is not None and cr < CAP_CONFLICT) else ("ok" if cr else "no_main_cap")
        row["n_other_main_nearby"] = int(n_main.get(r["a_id"], 1) - 1)
        row["Decision"], row["Notes"] = None, None
        recon.append(row)
    recon = pd.DataFrame(recon)
    if len(recon):   # a capacity-gated source (e.g. irs_rcn) can yield 0 matches -> empty
        recon = recon.sort_values([f"{args.source}_state", f"{args.source}_city"]).reset_index(drop=True)

    # --- Main_dedup: source rows matching >1 main row (under-merge clusters) ---
    dedup = []
    multi_ids = [aid for aid, n in n_main.items() if n > 1]
    for aid in multi_ids:
        s = s_ident(aid)
        for _, r in matches[matches.a_id == aid].iterrows():
            dedup.append({**s, "match_dist_km": _f(r["dist_km"]), "cap_ratio": _f(r["cap_ratio"]),
                          **m_ident(r["b_id"])})
    dedup = pd.DataFrame(dedup)
    if len(dedup):
        dedup = dedup.sort_values([f"{args.source}_state", f"{args.source}_city",
                                   f"{args.source}_id", "match_dist_km"]).reset_index(drop=True)

    # --- <SRC>_only: no match anywhere (discovery candidates) ---
    matched_ids = set(matches["a_id"])
    only = [{**s_ident(sid), "Decision": None, "Notes": None}
            for sid in src.index if sid not in matched_ids]
    only = pd.DataFrame(only)

    # --- Possible: possible pairs for review ---
    prows = []
    for _, r in possibles.iterrows():
        prows.append({**s_ident(r["a_id"]), "name_score": _f(r["name"]),
                      "match_dist_km": _f(r["dist_km"]), "cap_ratio": _f(r["cap_ratio"]),
                      **m_ident(r["b_id"]), "Decision": None, "Notes": None})
    poss = pd.DataFrame(prows)
    if len(poss):
        poss = poss.sort_values([f"{args.source}_state", f"{args.source}_city",
                                 "name_score"], ascending=[True, True, False]).reset_index(drop=True)

    summary = pd.DataFrame([
        ("source", args.source),
        ("main", mp.name),
        (f"{args.source} rows (in scope)", len(src)),
        ("matched to main", len(best)),
        (f"{args.source}-only (discovery)", len(only)),
        ("capacity conflicts (matched, ratio<%.2f)" % CAP_CONFLICT,
         int((recon["cap_flag"] == "conflict").sum()) if len(recon) else 0),
        ("source rows hitting >1 main row (dedup clusters)", len(multi_ids)),
        ("main rows tangled in those clusters", dedup["main_name"].nunique() if len(dedup) else 0),
        ("possible pairs", len(poss)),
    ], columns=["metric", "value"])

    out = Path(args.out) if args.out else BATCHES / f"refineries_{args.source}_reconciliation_{stamp}.xlsx"
    with pd.ExcelWriter(out, engine="openpyxl") as xw:
        summary.to_excel(xw, sheet_name="Summary", index=False)
        recon.to_excel(xw, sheet_name=f"{args.source}_to_main", index=False)
        if len(dedup):
            dedup.to_excel(xw, sheet_name="Main_dedup", index=False)
        if len(only):
            only.to_excel(xw, sheet_name=f"{args.source}_only", index=False)
        if len(poss):
            poss.to_excel(xw, sheet_name="Possible", index=False)

    print(f"wrote {out}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
