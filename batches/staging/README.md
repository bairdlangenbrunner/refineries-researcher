# batches/staging/

One subdirectory per run: `<mode>_<run>/` (e.g. `build_20260709/`, `update_algeria_20260709/`,
`recon_ogj_20260709/`).

- **Committed:** the agent-authored staging JSON (the edits/new-records/conflicts the
  workbook is built from) — the audit trail of what was proposed and why.
- **Gitignored:** derived artifacts (intermediate parquet, match outputs, caches).

`build_review_package.py --staging batches/staging/<run>/` turns the staged JSON into the
reviewable xlsx under `batches/`.
