"""Build the China under-merge review workbook (resolves a tracked open item).

    python scripts/build_china_undermerge_review.py
    python scripts/build_china_undermerge_review.py --out batches/refineries_china_undermerge_<stamp>.xlsx

The problem: the GEM China Independent (teapot) tracker seeds 101 China rows into the
master, but 91 of them sit as UNMERGED SINGLETONS while RMI / OGJ / OGIM / Climate TRACE
describe many of the same plants under different names. The generic matcher can't bridge
them because the tracker keys refineries by COMPANY name (e.g. "Shandong Dongming
Petrochemical Group Co Ltd") while RMI keys by PLANT name ("Dongming Heze Shandong
Refinery") — token overlap is low, so build's match drops the pair to `possible` or misses
it. The tracker's own `RMIFacilityName` column names the RMI plant explicitly; this script
uses that as a deterministic bridge on top of the geo/capacity matcher.

Reconciles the china_rmi_tracker source rows against the NON-tracker China master rows
(SourcesPresent without `china_rmi_tracker`) — i.e. the potential duplicate entities —
and emits per-teapot merge candidates for Baird to confirm and collapse by hand. This is a
REVIEW deliverable, never an applied edit; per standing rule internal RefineryIDs are NOT
emitted (rows identified by name + city + capacity + sources). See
docs/sops/reconciliation.md and the "China under-merge" item in PROJECT_SETUP_AND_CONTEXT.md.
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import latest_master, SOURCES, BATCHES, REPO
from match import match_sources, name_score, normalize_name

try:
    import pandas as pd
    import openpyxl  # noqa: F401  (ExcelWriter engine)
except ImportError:  # pragma: no cover
    sys.exit("needs pandas + rapidfuzz + scipy + openpyxl (pip install -r requirements.txt)")

SRC = "china_rmi_tracker"
RMI_HINT_MIN = 0.72   # RMIFacilityName vs candidate name/othernames: token_set floor to surface


def _f(v):
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def _sid(v):
    """Normalize a source id to its bare integer string ('01' -> '1') for joining."""
    s = str(v).strip()
    try:
        return str(int(float(s)))
    except (TypeError, ValueError):
        return s


# The registered "...for RMI" export DROPS the RMIFacilityName column; only GEM's live
# "...- main" sheet carries it, and it is the deterministic teapot->RMI bridge. Prefer main
# when present (data-identical to the export on shared columns; see manifest note), else fall
# back to the registered export (bridge unavailable -> Pass B is skipped).
MAIN_XLSX = REPO / "data" / "china_gem_main_tracker.xlsx"


def load_tracker_extras() -> dict:
    """Pull ChineseName / Is_In_RMI_20230508 / RMIFacilityName from the source xlsx —
    ingest drops them, but RMIFacilityName is the strongest merge signal we have."""
    import openpyxl
    if MAIN_XLSX.exists():
        path = MAIN_XLSX
    else:
        mani = SOURCES / SRC / "manifest.yml"
        fp = None
        for line in mani.read_text().splitlines():
            s = line.strip()
            if s.startswith("file_path:"):
                fp = s.split(":", 1)[1].split("#", 1)[0].strip().strip('"').strip("'")
                break
        path = REPO / fp
    if not path.exists():
        sys.exit(f"tracker xlsx not at {path} — export it (see manifest) before running")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Refineries"]
    rows = list(ws.iter_rows(values_only=True))
    hdr = [str(c).strip() if c is not None else "" for c in rows[0]]
    idx = {h: i for i, h in enumerate(hdr)}
    out = {}
    for r in rows[1:]:
        if not any(c not in (None, "") for c in r):
            continue
        def col(h):
            return r[idx[h]] if h in idx else None
        rid = _sid(col("RefineryID"))
        out[rid] = {
            "chinese": col("ChineseName"),
            "is_in_rmi": col("Is_In_RMI_20230508"),
            "rmi_facility_name": col("RMIFacilityName"),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    args = ap.parse_args()

    mp = latest_master()
    if mp is None:
        sys.exit("No master yet (data/master_*.parquet).")
    stamp = mp.stem[len("master_"):]

    src = pd.read_parquet(SOURCES / SRC / "canonical.parquet").copy()
    src["source_id"] = src["source_id"].map(_sid)
    extras = load_tracker_extras()

    mst = pd.read_parquet(mp)
    cn = mst[mst["ISO3"].astype(str) == "CHN"].copy()

    # invert the crosswalk: RefineryID -> which teapot source_id (if any) landed in it
    xwalk = json.loads((REPO / "data" / "id_crosswalk.json").read_text())
    teapot_master_ids = {rid for k, rid in xwalk.items() if k.startswith(f"{SRC}:")}

    # candidate pool = China master rows WITHOUT the china tracker = potential dup entities
    has_tracker = cn["SourcesPresent"].astype(str).str.contains(SRC)
    cand = cn[~has_tracker].copy().reset_index(drop=True)
    cand_frame = pd.DataFrame({
        "source_id": cand["RefineryID"],
        "name": cand["RefineryName"],
        "capacity_kbpd": cand["CapacityInKbpd"],
        "latitude": cand["Latitude"],
        "longitude": cand["Longitude"],
        "iso3": "CHN", "country": "China",
    })
    cand_by_id = cand.set_index("RefineryID")

    # teapot solo-vs-merged status in the current master (only solos are true dups to fix).
    # Look up in the FULL master, not just the China subset — a teapot that merged with a
    # coordless/ISO3-blank row can land outside the CHN slice.
    mst_by_id = mst.set_index("RefineryID")

    def teapot_master_state(rid_master):
        if rid_master is None or rid_master not in mst_by_id.index:
            return None
        srcs = str(mst_by_id.loc[rid_master, "SourcesPresent"])
        return "merged" if "," in srcs else "solo"

    # --- Pass A: geo / capacity / name via the shared matcher ---
    pairs = match_sources(src, cand_frame, block_km=25.0)
    # {teapot_source_id: {cand_refid: evidence}}
    candidates: dict[str, dict[str, dict]] = {}
    for _, r in pairs.iterrows():
        tid, cid = _sid(r["a_id"]), r["b_id"]
        ev = candidates.setdefault(tid, {}).setdefault(cid, {})
        ev["geo_label"] = r["label"]
        ev["name_score"] = _f(r["name"])
        ev["dist_km"] = _f(r["dist_km"])
        ev["cap_ratio"] = _f(r["cap_ratio"])

    # --- Pass B: RMIFacilityName -> candidate name/othernames (deterministic bridge) ---
    cand_norm = [(cid, normalize_name(nm), normalize_name(on))
                 for cid, nm, on in zip(cand["RefineryID"], cand["RefineryName"],
                                        cand.get("OtherNames", pd.Series([None] * len(cand))))]
    for tid in src["source_id"]:
        rmi_name = extras.get(tid, {}).get("rmi_facility_name")
        if not rmi_name or str(rmi_name).strip() in ("", "None"):
            continue
        rn = normalize_name(rmi_name)
        for cid, cnm, con in cand_norm:
            sc = max(name_score(rn, cnm), name_score(rn, con))
            if sc >= RMI_HINT_MIN:
                ev = candidates.setdefault(tid, {}).setdefault(cid, {})
                ev["rmi_hint_score"] = round(sc, 3)

    def confidence(ev: dict) -> str:
        """Only the RMIFacilityName bridge (or a strong name+geo agreement) earns `high`.
        Bare coordinate proximity is deliberately NOT high: dense Shandong/Dongying parks pack
        many distinct teapots within a few km, so proximity alone yields false matches (see the
        China under-merge note). Proximity-only pairs are `low` — surfaced, but flagged verify."""
        rmi = ev.get("rmi_hint_score") or 0
        nm = ev.get("name_score") or 0
        dist = ev.get("dist_km")
        cap = ev.get("cap_ratio") or 0
        if rmi >= 0.85:
            return "high"                                  # deterministic RMIname bridge
        if dist is not None and dist <= 5 and nm >= 0.72:
            return "high"                                  # real name agreement + coincident
        if rmi >= RMI_HINT_MIN:
            return "medium"                                # partial RMIname bridge
        if ev.get("geo_label") == "match" and (nm >= 0.55 or cap >= 0.9):
            return "medium"
        return "low"                                       # proximity-/possible-only: verify

    _rank = {"high": 0, "medium": 1, "low": 2}
    src_idx = src.set_index("source_id")

    merge_rows, no_cand_rows = [], []
    for tid in src["source_id"]:
        s = src_idx.loc[tid]
        ex = extras.get(tid, {})
        rid_master = xwalk.get(f"{SRC}:{tid}")
        base = {
            "teapot_name": s.get("name"),
            "teapot_chinese": ex.get("chinese"),
            "teapot_city": s.get("city"),
            "teapot_province": s.get("subnational"),
            "teapot_cap_kbpd": _f(s.get("capacity_kbpd")),
            "teapot_status": s.get("status"),
            "teapot_owner": s.get("owner"),
            "in_master_as": teapot_master_state(rid_master),
            "is_in_rmi_flag": ex.get("is_in_rmi"),
            "rmi_facility_name": ex.get("rmi_facility_name"),
        }
        cds = candidates.get(tid, {})
        if not cds:
            no_cand_rows.append({**base, "Decision": None, "Notes": None})
            continue
        for cid, ev in cds.items():
            b = cand_by_id.loc[cid]
            conf = confidence(ev)
            merge_rows.append({
                **base,
                "_conf_rank": _rank[conf], "confidence": conf,
                "ambiguous": "yes" if len(cds) > 1 else None,
                "match_via": "+".join(
                    ([f"rmi_name({ev['rmi_hint_score']})"] if ev.get("rmi_hint_score") else [])
                    + ([f"geo/{ev['geo_label']}"] if ev.get("geo_label") else [])),
                "cand_name": b.get("RefineryName"),
                "cand_othernames": b.get("OtherNames"),
                "cand_sources": b.get("SourcesPresent"),
                "cand_city": b.get("City"),
                "cand_state": b.get("Subnational"),
                "cand_cap_kbpd": _f(b.get("CapacityInKbpd")),
                "cand_status": b.get("Status"),
                "name_score": ev.get("name_score"),
                "rmi_hint_score": ev.get("rmi_hint_score"),
                "dist_km": ev.get("dist_km"),
                "cap_ratio": ev.get("cap_ratio"),
                "Decision": None, "Notes": None,
            })

    merge = pd.DataFrame(merge_rows)
    if len(merge):
        merge = merge.sort_values(
            ["_conf_rank", "teapot_province", "teapot_name", "confidence"],
        ).drop(columns="_conf_rank").reset_index(drop=True)
    nocand = pd.DataFrame(no_cand_rows)
    if len(nocand):
        # teapots flagged as RMI dups but with no found twin bubble to the top (investigate)
        nocand["_flag"] = nocand["is_in_rmi_flag"].astype(str).str.strip().str.lower().eq("yes")
        nocand = nocand.sort_values(["_flag", "teapot_province", "teapot_name"],
                                    ascending=[False, True, True]).drop(columns="_flag").reset_index(drop=True)

    teapots_with_cand = merge["teapot_name"].nunique() if len(merge) else 0
    high = merge[merge["confidence"] == "high"]["teapot_name"].nunique() if len(merge) else 0
    solo = (nocand["in_master_as"] == "solo").sum() if len(nocand) else 0
    rmi_flag_no_twin = 0
    if len(nocand):
        rmi_flag_no_twin = int(nocand["is_in_rmi_flag"].astype(str).str.strip().str.lower().eq("yes").sum())

    summary = pd.DataFrame([
        ("source", SRC),
        ("master", mp.name),
        ("teapot rows (china tracker)", len(src)),
        ("China master rows total", len(cn)),
        ("  of which include the tracker", int(has_tracker.sum())),
        ("  candidate pool (non-tracker China rows)", len(cand)),
        ("teapots with >=1 merge candidate", teapots_with_cand),
        ("  high-confidence (RMIname or tight geo)", high),
        ("teapots with NO candidate", len(nocand)),
        ("  of those, currently solo in master", int(solo)),
        ("  RMI-flagged (Is_In_RMI=Yes) but no twin found -> investigate", rmi_flag_no_twin),
    ], columns=["metric", "value"])

    readme = pd.DataFrame([
        ("What this is", "Per-teapot merge candidates linking the GEM China Independent tracker "
                         "rows to their duplicate RMI/OGJ/OGIM/Climate-TRACE entities in the master."),
        ("Why", "91 of 101 teapot rows sit unmerged; the tracker uses company names, RMI uses "
                "plant names, so build's matcher can't bridge them automatically."),
        ("match_via = rmi_name(score)", "The teapot's own RMIFacilityName column matched this "
                                        "candidate's name/OtherNames. Strongest signal."),
        ("match_via = geo/label", "The generic matcher paired them by coordinate/capacity/name."),
        ("confidence", "high = confident same plant; medium = likely; low = weak, verify."),
        ("How to use", "For each high/medium row, confirm the teapot row and the candidate are the "
                       "same refinery, then COLLAPSE them in the master by hand (fold the teapot "
                       "name into the candidate's OtherNames, keep one record). Agent never merges."),
        ("Merge_candidates", "teapots that have >=1 candidate (one row per teapot x candidate)."),
        ("Teapot_no_candidate", "teapots with no found twin; RMI-flagged ones without a twin are "
                                "listed first as anomalies to investigate."),
        ("Standing rule", "Internal RefineryIDs are not emitted; identify rows by name/city/"
                          "capacity/sources. GEM tracker is seed only, never a [ref]."),
    ], columns=["field", "meaning"])

    out = Path(args.out) if args.out else BATCHES / f"refineries_china_undermerge_{stamp}.xlsx"
    with pd.ExcelWriter(out, engine="openpyxl") as xw:
        readme.to_excel(xw, sheet_name="README", index=False)
        summary.to_excel(xw, sheet_name="Summary", index=False)
        if len(merge):
            merge.to_excel(xw, sheet_name="Merge_candidates", index=False)
        if len(nocand):
            nocand.to_excel(xw, sheet_name="Teapot_no_candidate", index=False)

    print(f"wrote {out}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
