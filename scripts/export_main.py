"""Export the union main to a review xlsx (a read-only snapshot, not a batch deliverable).

    python scripts/export_main.py                 # latest main -> batches/refineries_main_<stamp>_worldwide_export.xlsx
    python scripts/export_main.py --main data/main_YYYYMMDD_HHMM_ET.parquet

Four sheets: Summary (counts), ByCountry, BySources, and the full-schema Refineries table.
Per workbook_conventions.md the internal RefineryID is DROPPED from outputs; the source ID
columns (rmi_refine_id/ogj_id/ogim_id/china_id) and SourcesPresent are kept. This never
edits the main — it just renders it for review.
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # runnable from repo root
from paths import BATCHES, latest_main, ordered_columns

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    sys.exit("export_main.py needs pandas + openpyxl (pip install -r requirements.txt)")

DROP_COLS = ["RefineryID"]   # internal id — never emitted (workbook_conventions.md)


def _stamp_from(main: Path) -> str:
    # main_20260713_1008_ET.parquet -> 20260713_1008_ET
    return main.stem[len("main_"):]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", help="path to a main_*.parquet (default: latest)")
    ap.add_argument("--out", help="output xlsx (default: batches/refineries_main_<stamp>_worldwide_export.xlsx)")
    args = ap.parse_args()

    main = Path(args.main) if args.main else latest_main()
    if main is None or not main.exists():
        sys.exit("No main found — build one with scripts/merge.py first.")
    df = pd.read_parquet(main)

    stamp = _stamp_from(main)
    out = Path(args.out) if args.out else (BATCHES / f"refineries_main_{stamp}_worldwide_export.xlsx")
    out.parent.mkdir(parents=True, exist_ok=True)

    cols = [c for c in ordered_columns() if c not in DROP_COLS]
    refineries = df[[c for c in cols if c in df.columns]].copy()

    summary = pd.DataFrame({
        "Metric": ["Main", "Refineries", "Countries", "With capacity (kbpd)",
                   "With coordinates", "Multi-source rows", "Single-source rows"],
        "Value": [main.name, len(df), int(df["Country"].nunique()),
                  int(df["CapacityInKbpd"].notna().sum()),
                  int(df[["Latitude", "Longitude"]].notna().all(axis=1).sum()),
                  int(df["SourcesPresent"].str.contains(",", na=False).sum()),
                  int((~df["SourcesPresent"].str.contains(",", na=False)).sum())],
    })
    by_country = (df["Country"].value_counts().rename_axis("Country")
                  .reset_index(name="Refineries"))
    by_sources = (df["SourcesPresent"].value_counts().rename_axis("SourcesPresent")
                  .reset_index(name="Rows"))

    with pd.ExcelWriter(out, engine="openpyxl") as xw:
        summary.to_excel(xw, sheet_name="Summary", index=False)
        by_country.to_excel(xw, sheet_name="ByCountry", index=False)
        by_sources.to_excel(xw, sheet_name="BySources", index=False)
        refineries.to_excel(xw, sheet_name="Refineries", index=False)

    print(f"exported {len(df)} rows x {len(refineries.columns)} cols "
          f"({df['Country'].nunique()} countries) -> {out}")


if __name__ == "__main__":
    main()
