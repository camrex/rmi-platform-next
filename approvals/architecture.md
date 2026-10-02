# Architecture — approved, 2026-10-02

Approved: docs/architecture/PROPOSAL.md as revised by task 0.8.

Rulings:
- R-1 to R-5, R-7a, R-9, R-10, R-11: accepted as recommended. R-8: noted (overtaken).
- R-6: accepted. Measured from the 26-150 forms: 557 of 1,866 questions are numbered
  slots (Complex Turnout 268 of 512, 101 groups); one repeat group in all 12 forms.
- R-7b: accepted; keep pricing scope general / railroad / project.
- R-12: accepted, with: existing OTHER maps to OTH and UNK/UNKNOWN to TBD; each field
  gets its own companion text, shown only when OTH/TBD is chosen (not one notes_other
  per form); do not use Survey123's or_other. Today 69 of 128 choice lists have an
  escape code, spelled four ways.
- R-13: accepted. R-13a: an empty to_complex_type is undecided (unassigned, blocks valuation).
- R-14: accepted; rmi-platform starts using the rebuild:replay label now.
- Cost index selection: decide in the pricing phase (a default index per catalog domain,
  overridable per project with a reason).

Note: docs/inventory/survey123.md is unreliable in places (guessed layer names, hedged
claims; it calls wayside detectors non-valued, which contradicts the proposal). Use the
measured figures above; redo the form inventory with a parser at the catalog phase.
