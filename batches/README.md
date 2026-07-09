# batches/

xlsx deliverables (`refineries_batch_<stamp>_[scope_]<mode>.xlsx`) and memos
(`triage_<stamp>_ET.md`, `qc_<stamp>_ET.md`). One file per batch; **never overwrite** — each
build gets a fresh timestamp; Baird prunes old ones. Conventions:
`docs/reference/workbook_conventions.md`.

`staging/` holds per-run working inputs: agent-authored staging JSON (**committed** — audit
trail) and derived artifacts (gitignored). See `staging/README.md`.
