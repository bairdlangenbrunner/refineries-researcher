# batches/

xlsx deliverables and memos. One file per run; **never overwrite** — each build gets a fresh
timestamp; Baird prunes old ones. Conventions: `docs/reference/workbook_conventions.md`.

Workbook types produced here:
- `refineries_batch_<stamp>_[scope_]<mode>.xlsx` — review batch (Update/Discovery); memos
  `triage_<stamp>_ET.md`, `qc_<stamp>_ET.md`.
- `refineries_main_<stamp>_worldwide_export.xlsx` — full main export (`export_main.py`).
- `refineries_possible_review_<stamp>.xlsx` — `possible` match pairs (`export_possible_review.py`).
- `refineries_<src>_reconciliation_<stamp>.xlsx` — per-source reconciliation review
  (`build_reconciliation_review.py`; also the `irs_rcn` overlay).

`staging/` holds per-run working inputs: agent-authored staging JSON (**committed** — audit
trail) and derived artifacts (gitignored). See `staging/README.md`.
