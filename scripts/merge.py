"""Build/refresh the union master from the canonical sources (greenfield step 2).

    python scripts/merge.py --sources rmi,ogj,ogim,china_rmi_tracker \
        --out data/master_<stamp>.parquet

Superset-first: UNION every source row, cluster the ones that are the same physical
refinery, and emit ONE master record per cluster on the GEM schema (paths.SCHEMA). We
never scope-filter here — every input row survives into exactly one master row; scope is
a separate reversible pass (InScope defaults to 'unknown').

Clustering (match.py supplies the edges):
  - Only strong `match` edges cluster rows; `possible` edges are written to a review file,
    never auto-merged.
  - Edges are applied best-first (name desc, distance asc) through a union-find with a
    SAME-SOURCE GUARD: two clusters never merge if they already share a source. This stops
    two distinct nearby refineries (e.g. RMI's Skikda main + Skikda condensate, which both
    match OGIM's single "SKIKDA") from collapsing into one record.

Per field, the value is picked from the highest-priority source that has it (all sources
are Tier 2, so priority is a per-field source order, not blind adoption). DISAGREEMENTS are
NOT silently resolved — they go to a conflicts report; the kept value is the priority one.
No `[ref]` columns are filled at build (background URLs are unverified; citable:false
sources contribute no URL) — the Update workflow researches and fills refs later.

Outputs (under the master's directory):
  data/master_<stamp>.parquet         the union master
  data/master_<stamp>.build.json      cluster/singleton/conflict counts
  data/master_<stamp>.conflicts.parquet   per-cluster field disagreements
  data/master_<stamp>.possible.parquet    possible (non-clustered) pairs for review
  data/id_crosswalk.json              anchor-id -> RefineryID, for stable ids across rebuilds

See docs/sops/build.md.
"""

from __future__ import annotations
import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # runnable from repo root
from paths import SOURCES, DATA, SCHEMA, SOURCE_ID_COLUMN, ordered_columns
from match import match_sources, haversine_km, load_canonical, _num
from country_normalize import canonical_country, iso3_to_name

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    sys.exit("merge.py needs pandas (pip install -r requirements.txt)")


# Per-field source priority: first source in the list that has a non-null value wins.
# Rationale: RMI = global design-capacity backbone; OGIM = location; china/ogj = status +
# proper-case names; OGIM names are UPPERCASE so they lose name/case ties.
FIELD_PRIORITY = {
    "name":           ["rmi", "china_rmi_tracker", "ogj", "ogim"],
    "country":        ["rmi", "ogim", "china_rmi_tracker", "ogj"],
    "iso3":           ["rmi", "ogim"],
    "subnational":    ["china_rmi_tracker", "rmi", "ogim"],
    "city":           ["china_rmi_tracker", "ogim", "rmi"],
    "status":         ["china_rmi_tracker", "ogj", "ogim", "rmi"],
    "owner":          ["rmi", "china_rmi_tracker", "ogj", "ogim"],
    "configuration":  ["rmi", "china_rmi_tracker"],
    "start_year":     ["china_rmi_tracker", "ogim", "ogj", "rmi"],
    "capacity":       ["rmi", "china_rmi_tracker", "ogj", "ogim"],   # design capacity preferred
    "coords":         ["ogim", "rmi", "china_rmi_tracker", "ogj"],   # OGIM is the location source
}
# Country implied by a source when its rows carry none.
IMPLIED_COUNTRY = {"china_rmi_tracker": "China"}


# --- union-find with same-source guard ---------------------------------------------- #
class DSU:
    def __init__(self):
        self.parent, self.sources = {}, {}

    def add(self, node, source):
        if node not in self.parent:
            self.parent[node] = node
            self.sources[node] = {source}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b) -> bool:
        """Merge iff the two clusters share no source. Returns True if merged."""
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return True
        if self.sources[ra] & self.sources[rb]:
            return False                      # same-source collision — keep separate
        self.parent[rb] = ra
        self.sources[ra] |= self.sources[rb]
        return True


def build_clusters(frames: dict) -> tuple[list, "pd.DataFrame", int]:
    """frames: {source: canonical_df}. Returns (clusters, possible_pairs_df, blocked_count).
    Each cluster is a list of (source, local_idx)."""
    dsu = DSU()
    for src, df in frames.items():
        for i in range(len(df)):
            dsu.add((src, i), src)

    match_edges, possible_rows = [], []
    for sa, sb in combinations(frames, 2):
        m = match_sources(frames[sa], frames[sb])
        for _, r in m.iterrows():
            if r["label"] == "match":
                match_edges.append((r["name"], -(r["dist_km"] if r["dist_km"] is not None else 99),
                                    (sa, int(r["a_idx"])), (sb, int(r["b_idx"]))))
            else:
                possible_rows.append({"source_a": sa, "source_b": sb, **r.to_dict()})

    match_edges.sort(key=lambda e: (e[0], e[1]), reverse=True)   # best first
    blocked = 0
    for _, _, na, nb in match_edges:
        if not dsu.union(na, nb):
            blocked += 1

    groups: dict = {}
    for node in dsu.parent:
        groups.setdefault(dsu.find(node), []).append(node)
    clusters = list(groups.values())
    possible_df = pd.DataFrame(possible_rows)
    return clusters, possible_df, blocked


# --- value selection ----------------------------------------------------------------- #
def _first(rows_by_src: dict, field: str, priority) -> object:
    for src in priority:
        r = rows_by_src.get(src)
        if r is not None:
            v = r.get(field)
            if v is not None and not (isinstance(v, float) and pd.isna(v)) and str(v).strip() != "":
                return v
    return None


def _emit_record(cluster, frames, refid) -> dict:
    rows_by_src = {src: frames[src].iloc[idx].to_dict() for src, idx in cluster}
    rec = {c: None for c in ordered_columns()}
    rec["RefineryID"] = refid

    name = _first(rows_by_src, "name", FIELD_PRIORITY["name"])
    rec["RefineryName"] = name
    others = []
    for src, r in rows_by_src.items():
        n = r.get("name")
        if n and str(n).strip() and str(n).strip().lower() != str(name).strip().lower() and n not in others:
            others.append(str(n).strip())
    rec["OtherNames"] = "; ".join(others) or None

    country = _first(rows_by_src, "country", FIELD_PRIORITY["country"])
    if country is None:
        for src in rows_by_src:
            if src in IMPLIED_COUNTRY:
                country = IMPLIED_COUNTRY[src]
                break
    iso3 = _first(rows_by_src, "iso3", FIELD_PRIORITY["iso3"])
    # canonicalize: one country name + ISO3, regardless of which source's spelling won
    canon_name, canon_iso = canonical_country(country)
    if canon_iso is None and iso3:                 # fall back to a source-supplied ISO3
        canon_iso = str(iso3).strip().upper()
        canon_name = canon_name or iso3_to_name(canon_iso)
    rec["Country"] = canon_name or country
    rec["ISO3"] = canon_iso or (str(iso3).strip().upper() if iso3 else None)
    rec["Subnational"] = _first(rows_by_src, "subnational", FIELD_PRIORITY["subnational"])
    rec["City"] = _first(rows_by_src, "city", FIELD_PRIORITY["city"])
    rec["Status"] = _first(rows_by_src, "status", FIELD_PRIORITY["status"])
    rec["Owner"] = _first(rows_by_src, "owner", FIELD_PRIORITY["owner"])
    rec["Configuration"] = _first(rows_by_src, "configuration", FIELD_PRIORITY["configuration"])
    rec["StartYear"] = _first(rows_by_src, "start_year", FIELD_PRIORITY["start_year"])

    # capacity: take value+units+kbpd from ONE source (the priority one that has kbpd)
    for src in FIELD_PRIORITY["capacity"]:
        r = rows_by_src.get(src)
        if r is not None and _num(r.get("capacity_kbpd")) is not None:
            rec["Capacity"] = r.get("capacity_value")
            rec["CapacityUnits"] = r.get("capacity_units")
            rec["CapacityInKbpd"] = r.get("capacity_kbpd")
            break

    # coords: take lat+lon (+accuracy) from ONE source
    for src in FIELD_PRIORITY["coords"]:
        r = rows_by_src.get(src)
        if r is not None and _num(r.get("latitude")) is not None and _num(r.get("longitude")) is not None:
            rec["Latitude"] = r.get("latitude")
            rec["Longitude"] = r.get("longitude")
            rec["Accuracy"] = r.get("accuracy") if r.get("accuracy") else None
            break

    for src, r in rows_by_src.items():
        col = SOURCE_ID_COLUMN.get(src)
        if col:
            rec[col] = r.get("source_id")
    rec["SourcesPresent"] = ",".join(sorted(rows_by_src))
    rec["InScope"] = "unknown"
    rec["ScopeReason"] = None
    return rec


def _conflicts(cluster, frames, refid) -> list[dict]:
    rows = [frames[src].iloc[idx].to_dict() for src, idx in cluster]
    srcs = [src for src, _ in cluster]
    out = []

    def distinct(field):
        vals = [(s, r.get(field)) for s, r in zip(srcs, rows)
                if r.get(field) is not None and str(r.get(field)).strip()]
        return vals

    st = distinct("status")
    if len({str(v).lower() for _, v in st}) > 1:
        out.append({"RefineryID": refid, "field": "status",
                    "values": "; ".join(f"{s}={v}" for s, v in st)})
    cf = distinct("configuration")
    if len({str(v).lower() for _, v in cf}) > 1:
        out.append({"RefineryID": refid, "field": "configuration",
                    "values": "; ".join(f"{s}={v}" for s, v in cf)})
    caps = [(s, _num(r.get("capacity_kbpd"))) for s, r in zip(srcs, rows) if _num(r.get("capacity_kbpd"))]
    if len(caps) > 1:
        lo, hi = min(v for _, v in caps), max(v for _, v in caps)
        if hi > 0 and lo / hi < 0.85:
            out.append({"RefineryID": refid, "field": "capacity_kbpd",
                        "values": "; ".join(f"{s}={v:.1f}" for s, v in caps)})
    pts = [(s, _num(r.get("latitude")), _num(r.get("longitude"))) for s, r in zip(srcs, rows)
           if _num(r.get("latitude")) is not None and _num(r.get("longitude")) is not None]
    maxd = 0.0
    for (s1, la1, lo1), (s2, la2, lo2) in combinations(pts, 2):
        maxd = max(maxd, haversine_km(la1, lo1, la2, lo2))
    if maxd > 1.0:
        out.append({"RefineryID": refid, "field": "location",
                    "values": f"max pairwise {maxd:.2f} km across " + ",".join(s for s, *_ in pts)})
    return out


def _assign_ids(clusters, frames, crosswalk_path: Path):
    """Stable RefineryID via an anchor (highest-priority source id present in the cluster).
    Existing anchors keep their id across rebuilds; new anchors extend the sequence."""
    crosswalk = json.loads(crosswalk_path.read_text()) if crosswalk_path.exists() else {}
    anchor_pref = ["rmi", "ogj", "ogim", "china_rmi_tracker"]

    def anchor(cluster):
        by_src = {src: idx for src, idx in cluster}
        for src in anchor_pref:
            if src in by_src:
                return f"{src}:{frames[src].iloc[by_src[src]]['source_id']}"
        src, idx = cluster[0]
        return f"{src}:{frames[src].iloc[idx]['source_id']}"

    used = {v for v in crosswalk.values()}
    nextn = (max((int(v[1:]) for v in used), default=0)) + 1
    ids = []
    for cl in clusters:
        a = anchor(cl)
        if a not in crosswalk:
            crosswalk[a] = f"R{nextn:04d}"
            nextn += 1
        ids.append(crosswalk[a])
    crosswalk_path.write_text(json.dumps(crosswalk, indent=2, sort_keys=True))
    return ids


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", required=True, help="comma-separated source names")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    names = [s.strip() for s in args.sources.split(",") if s.strip()]
    frames = {n: load_canonical(n).reset_index(drop=True) for n in names}
    for df in frames.values():   # ids are cross-type (int vs str) — normalize to text
        df["source_id"] = df["source_id"].astype("string")
    total_in = sum(len(df) for df in frames.values())
    print(f"union input: {total_in} rows across {len(frames)} sources "
          + ", ".join(f"{n}={len(frames[n])}" for n in names))

    clusters, possible_df, blocked = build_clusters(frames)
    # order clusters for stable, human-friendly ids: by country then name
    def sort_key(cl):
        rbs = {s: frames[s].iloc[i].to_dict() for s, i in cl}
        c = _first(rbs, "country", FIELD_PRIORITY["country"]) or IMPLIED_COUNTRY.get(
            next((s for s in rbs if s in IMPLIED_COUNTRY), ""), "zzz")
        n = _first(rbs, "name", FIELD_PRIORITY["name"]) or ""
        return (str(c).lower(), str(n).lower())
    clusters.sort(key=sort_key)

    out = Path(args.out)
    ids = _assign_ids(clusters, frames, DATA / "id_crosswalk.json")

    records, conflicts = [], []
    multi = 0
    for cl, refid in zip(clusters, ids):
        records.append(_emit_record(cl, frames, refid))
        if len({s for s, _ in cl}) > 1:
            multi += 1
            conflicts.extend(_conflicts(cl, frames, refid))

    master = pd.DataFrame(records, columns=ordered_columns())
    out.parent.mkdir(parents=True, exist_ok=True)
    master.to_parquet(out, index=False)
    conflicts_df = pd.DataFrame(conflicts, columns=["RefineryID", "field", "values"])
    conflicts_df.to_parquet(out.with_suffix(".conflicts.parquet"), index=False)
    if not possible_df.empty:
        possible_df.to_parquet(out.with_suffix(".possible.parquet"), index=False)

    singletons = {n: 0 for n in names}
    for cl in clusters:
        if len(cl) == 1:
            singletons[cl[0][0]] += 1
    report = {
        "sources": names, "input_rows": total_in,
        "master_rows": len(master), "clusters": len(clusters),
        "multi_source_clusters": multi,
        "singletons_per_source": singletons,
        "same_source_collisions_blocked": blocked,
        "conflicts": len(conflicts),
        "possible_pairs": int(len(possible_df)),
        "dedup_collapsed": total_in - len(master),
    }
    out.with_suffix(".build.json").write_text(json.dumps(report, indent=2))
    print(f"master: {len(master)} rows ({report['dedup_collapsed']} collapsed by dedup), "
          f"{multi} multi-source, {len(conflicts)} field conflicts, "
          f"{blocked} same-source collisions blocked -> {out}")


if __name__ == "__main__":
    main()
