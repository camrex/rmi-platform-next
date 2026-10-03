---
status: ruled
kind: architecture
date: 2026-10-02
refs:
  - approvals/architecture.md
  - docs/architecture/PROPOSAL.md §12
---

# Operator approval of architecture proposal, 2026-10-02

## Approval

From `approvals/architecture.md`:

> Approved: docs/architecture/PROPOSAL.md as revised by task 0.8.

## Rulings

The operator's rulings are recorded in `approvals/architecture.md` and the R-n table in
`docs/architecture/PROPOSAL.md` §12 (R-1 through R-14, R-13a):

- **R-1 through R-5, R-7a, R-9, R-10, R-11**: accepted as recommended.
- **R-6**: accepted. Measured from the 26-150 forms: 557 of 1,866 questions are numbered
  slots (Complex Turnout 268 of 512, 101 groups); one repeat group in all 12 forms.
- **R-7b**: accepted; keep pricing scope general / railroad / project.
- **R-12**: accepted, with additional detail on companion text field naming and escape code mapping.
  Existing `OTHER` maps to `OTH` and `UNK`/`UNKNOWN` to `TBD`; each field gets its own companion
  text, shown only when `OTH`/`TBD` is chosen (not one `notes_other` per form); Survey123's
  `or_other` is not used. Today 69 of 128 choice lists have an escape code, spelled four ways.
- **R-13**: accepted.
- **R-13a**: an empty `to_complex_type` is undecided (unassigned, blocks valuation).
- **R-14**: accepted; rmi-platform starts using the `rebuild:replay` label now.
- **R-8**: noted (overtaken by #1981, rmi-civ-viewer project).

## Additional direction

**Cost index selection**: decide in the pricing phase (a default index per catalog domain,
overridable per project with a reason).

**Survey123 inventory note**: docs/inventory/survey123.md is unreliable in places (guessed layer
names, hedged claims); use the measured figures in `approvals/architecture.md`; redo the form
inventory with a parser at the catalog phase.
