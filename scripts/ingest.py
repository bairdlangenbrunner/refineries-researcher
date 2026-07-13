"""Normalize a registered background source into the canonical record schema.

    python scripts/ingest.py --source rmi [--out sources/rmi/canonical.parquet]

Reads sources/<name>/manifest.yml, loads the raw data (generic loader for xlsx/csv/
geojson, or the source's adapter.py for custom formats), renames columns to canonical
fields, applies status_map/configuration_map, normalizes capacity to kbpd, and writes:
  - sources/<name>/canonical.parquet    (gitignored — the rows)
  - sources/<name>/canonical_summary.json (committed — counts + per-column fill rate)

Greenfield step 1. See docs/sops/ingest.md and sources/_schema/canonical_record.md.
"""

from __future__ import annotations
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # runnable from repo root
from paths import SOURCES
from capacity_normalize import to_kbpd, UnknownUnit

try:
    import pandas as pd
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("ingest.py needs pandas + pyyaml (pip install -r requirements.txt)")

CANONICAL_FIELDS = [
    "source", "source_id", "name", "country", "iso3", "subnational", "city",
    "latitude", "longitude", "capacity_value", "capacity_units", "capacity_kbpd",
    "status", "owner", "configuration", "start_year", "source_url", "source_tier",
]


def load_manifest(name: str) -> dict:
    path = SOURCES / name / "manifest.yml"
    if not path.exists():
        sys.exit(f"No manifest at {path}")
    return yaml.safe_load(path.read_text())


def resolve_raw_path(manifest: dict) -> Path:
    loc = manifest.get("location", {})
    p = None
    if loc.get("file_path"):
        p = Path(loc["file_path"])
        p = p if p.is_absolute() else (SOURCES.parent / p)
    elif loc.get("sibling_path"):
        p = (SOURCES.parent / loc["sibling_path"]).resolve()
    if p and p.exists():
        return p
    where = loc.get("drive_file_id") or loc.get("url") or p
    sys.exit(
        f"Raw data not found ({p}). Download it first ({where}) into the manifest's "
        "file_path, then re-run. Downloads are gitignored."
    )


def load_adapter(name: str):
    path = SOURCES / name / "adapter.py"
    spec = importlib.util.spec_from_file_location(f"{name}_adapter", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def generic_load(manifest: dict, raw: Path) -> list[dict]:
    """xlsx/csv/geojson → canonical-keyed rows via manifest.column_map."""
    fmt = manifest["format"]
    loc = manifest.get("location", {})
    if fmt == "xlsx":
        df = pd.read_excel(raw, sheet_name=loc.get("sheet", 0), header=loc.get("header_row", 0))
    elif fmt == "csv":
        df = pd.read_csv(raw, header=loc.get("header_row", 0), low_memory=False)
    elif fmt in ("geojson", "gpkg"):
        import geopandas as gpd  # optional dep
        df = gpd.read_file(raw, layer=loc.get("layer"))
    else:
        sys.exit(f"format {fmt!r} needs an adapter (set `adapter:` in the manifest).")

    rows = []
    for _, r in df.iterrows():
        row = {}
        for canon, src_col in manifest["column_map"].items():
            row[canon] = r.get(src_col) if src_col in df.columns else None
        rows.append(row)
    return rows


def _to_year(value, sentinels: set[int]):
    """Extract a 4-digit start year from a date string / number; drop sentinel years
    (e.g. OGIM's 1900-01-01 unknown-date placeholder — 680/692 rows)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    m = re.search(r"(1[89]\d{2}|20\d{2})", str(value))
    if not m:
        return None
    year = int(m.group(1))
    return None if year in sentinels else year


def finalize(rows: list[dict], manifest: dict) -> "pd.DataFrame":
    name = manifest["name"]
    tier = manifest.get("source_tier")
    status_map = {k.lower(): v for k, v in (manifest.get("status_map") or {}).items()}
    config_map = {str(k): v for k, v in (manifest.get("configuration_map") or {}).items()}
    default_units = manifest.get("capacity_units")
    year_sentinels = {int(y) for y in (manifest.get("start_year_sentinels") or [1900])}
    # Constant fills for a scoped source (e.g. a China-only tracker with no Country column):
    # any canonical field named here is set when the row leaves it null.
    defaults = manifest.get("defaults") or {}

    out = []
    for row in rows:
        rec = {f: row.get(f) for f in CANONICAL_FIELDS}
        rec["source"] = name
        rec["source_tier"] = tier
        for f, v in defaults.items():
            if rec.get(f) is None or (isinstance(rec.get(f), float) and pd.isna(rec.get(f))):
                rec[f] = v
        # status / configuration vocab mapping
        if rec.get("status") is not None:
            rec["status"] = status_map.get(str(rec["status"]).strip().lower(), rec["status"])
        if rec.get("configuration") is not None:
            rec["configuration"] = config_map.get(str(rec["configuration"]).strip(), rec["configuration"])
        # start_year -> integer year, sentinel-nulled
        rec["start_year"] = _to_year(rec.get("start_year"), year_sentinels)
        # capacity normalization
        units = rec.get("capacity_units") or default_units
        rec["capacity_units"] = units
        try:
            rec["capacity_kbpd"] = to_kbpd(rec.get("capacity_value"), units) if units else None
        except UnknownUnit as e:
            rec["capacity_kbpd"] = None
            print(f"  ! {e} (source_id={rec.get('source_id')})", file=sys.stderr)
        out.append(rec)
    return pd.DataFrame(out, columns=CANONICAL_FIELDS)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()

    manifest = load_manifest(args.source)
    raw = resolve_raw_path(manifest)
    print(f"ingest {args.source}: {raw}")

    excluded = []
    if manifest.get("adapter"):
        parse = load_adapter(args.source).parse
        rows = parse(manifest, str(raw))
        excluded = list(getattr(parse, "excluded", []) or [])   # scope-dropped rows to surface
    else:
        rows = generic_load(manifest, raw)

    df = finalize(rows, manifest)
    out = Path(args.out) if args.out else (SOURCES / args.source / "canonical.parquet")
    df.to_parquet(out, index=False)

    summary = {
        "source": args.source,
        "rows": len(df),
        "with_coords": int(df[["latitude", "longitude"]].notna().all(axis=1).sum()),
        "with_capacity_kbpd": int(df["capacity_kbpd"].notna().sum()),
        "fill_rate": {c: round(float(df[c].notna().mean()), 3) for c in CANONICAL_FIELDS},
    }
    if excluded:
        summary["excluded_out_of_scope"] = excluded
    (SOURCES / args.source / "canonical_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"  -> {out}  ({len(df)} rows)")
    print(f"  -> canonical_summary.json")
    if excluded:
        print(f"  ! excluded {len(excluded)} out-of-scope site(s) (no crude distillation):")
        for e in excluded:
            print(f"      - {e.get('company')} | {e.get('site')}, {e.get('state')}")


if __name__ == "__main__":
    main()
