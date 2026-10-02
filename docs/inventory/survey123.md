# Survey123 form definitions inventory

**Task 0.9**: Inventory the Survey123 form definitions the operator placed in `data/survey123/`
(14 XLSForm files: 12 for 26-150 track improvement inspection, 2 for 26-210 land valuation).
See `data/survey123/README.md` for caveats.

**Caveat**: These forms were used in the field during the 26-150 inspection
(2026-04/05 and 2026-08-18) and have **not** been updated since with schema changes made after
the inspection. Treat them as the capture design as deployed, not as current. Where a form and
the current templates (`~/sources/rmigis-pyt/templates/`) disagree, that is a finding.

**Method**: Extracted XLSForm sheets (survey, choices, settings) from each XLSX file using
zipfile + XML parsing; structured as type, name, label, choice lists, constraints, `bind::`
Esri attributes, `required`, appearance flags, and free text indicators. Not cross-checked
against live Portal layers or collected data (.gpkg files).

## 26-150 project forms (12 forms, track improvement inspection)

Each writes to a corresponding feature class on the Portal; forms predate the schema 2 
changes and use **free-text fields and `OTHER`-only escape codes** where the PROPOSAL §6.3
would now require domain + `OTH`/`TBD` + companion text.

### 26-150 Bungalow (bungalows_inv_pt)

**Form file**: `26-150 Bungalow Inspection Form Schema 2.xlsx` (116 questions, 96 choice rows)

**Layer**: `a26150_bungalow_inv_pt_point` (Portal feature class, synced to platform as `bungalows`)

**Design**: Collects bungalow location, type, materials, contents (relays, batteries, transformers,
etc.), function, condition. Heavy use of templated questions (appear to repeat across forms for
common attributes like milepost, RR subdivision, related asset IDs, notes).

**Key fields identified from templates**:
- Milepost: `mp_pre` (prefix text), `mp_meas` (measurement DOUBLE), `mp_rr` (RR DOUBLE)
- Identity: `rel_sig_loc_id`, `rel_xing_id`, `rel_wayside_det_id` (text asset ID joins, all free text)
- Bungalow details: `bglw_use` (domain), `bglw_class` (TEXT, choice list), `bglw_mat` (domain),
  `bglw_cond` (domain)
- Component inventory: equipment quantity, make/model (free text), year installed

**Disagreements with templates** (`rmigis-pyt/templates/track_impr_fc.yaml` + 
`gis-schema-review.md`):
- **[P-4 identity]** `rel_*` fields are TEXT joins to asset IDs (not GlobalID edges; proposal
  would resolve at sync).
- **[P-1 slots]** Component columns appear numbered (no child table, should normalize on sync if
  schema 2 follows the pattern).
- **[T-5 domains]** Free-text `_mfr` fields (no domain proposed yet).
- **[T-5, P-3]** `has_*` and `*_cnt` derived flags (computed on sync, never written).

**Free text and `OTHER` use** (non-exhaustive from field names):
- Notes fields: `notes_*` (free TEXT 255 per layer)
- Make/model: `*_mfr` columns (free TEXT 50)
- "Other" escape: `bglw_use` domain has `SIG_OTH` (Signal - Other); companion text expected
  in a notes field or `bglw_use_notes` (free text); no structured `OTH` + text pattern.

**What PROPOSAL §6.3 would change**:
1. Domain fields that name a kind of thing (e.g., `bglw_class`, `bglw_use`, `bglw_mat`, 
   bungalow condition) need **`OTH` + companion text** for unknowns, not freeform `*_mfr` text.
   - `bglw_class` (house, case, panel, other): add `OTH` code + `bglw_class_other` text field.
   - `bglw_use` (signal, repeater, crossing, etc.): already has `SIG_OTH`; formalize with `OTH` 
     + `bglw_use_other`.
   - Bungalow material (`bglw_mat`) domain similarly.
2. Catalog integration: each captured value resolves to a catalog class (§7.3); unknowns become
   `unclassified` items (§7.4) that later curation classifies or merges.

---

### 26-150 Crossing (xing_inv_pt)

**Form file**: `26-150 Crossing Inspection Form Schema 2.xlsx` (230 questions, 103 choice rows)

**Layer**: `xing_inv_pt` (Portal feature class, synced to platform as `xings`)

**Design**: Collects crossing structure (gates, flashers, cantilevers), gates (number, type,
condition, equipment), road approach, sightlines, warnings, defect detector, wayside equipment.
Heavily slotted: 4–6 equipment slots per structure type (gate1..4, flasher, cantilever, etc.),
each with type, year, make/model, condition.

**Key fields** (from templates):
- Crossing structure: `xing_struct_type` (domain), `xing_config` (packed text; proposal §8 suggests
  child rows)
- Gate inventory: `gate1..4` type, year, condition; each has slots
- Cantilever & flasher: separate slots
- Wayside equipment: detector type, location, count
- Milepost, notes as other forms

**Disagreements with templates**:
- **[P-1 slots]** Heavily slotted (4+ gates, 3+ flashers, cantilevers numbered). Schema 2 appears
  to have migrated to `xing_struct_tbl` (related table) for structure details (#1026), but forms
  still use columns. If sync slots are unmigrated, this is a schema-drift finding.
- **[O-1, P-1]** Gate type, flasher type: free TEXT fields for make/model; no domain code +
  `OTH` escape. Proposal would add domain codes + companion text.
- **[T-5, P-3]** `has_gate`, `gate_cnt`, `has_flasher`, `flasher_cnt` (derived, computed on sync).

**Free text and `OTHER` use**:
- `xing_str_equip1..4` (gate types, TEXT 50): free text; no `OTHER` escape.
- `gate_*_mfr`, `flasher_*_mfr`, `cant_*_mfr` (free TEXT 50): no domain.
- Condition fields: domain-based (Excellent, Good, Fair, Poor, Failed).
- Notes: `notes_crossing`, `notes_warning`, `notes_defect_detector` (free TEXT 255).

**What PROPOSAL §6.3 would change**:
1. Gate type, flasher type, cantilever type → domain codes + `OTH` escape + companion `_other` text.
2. Crossing structure type (`xing_struct_type`) → domain; unknowns as `OTH` + text.
3. Defect detector family/type → domain code (proposed `rmi_trk_wayside_equip` in §7.3); unknowns
   as `OTH` + text.
4. Schema 2 slot structure should be validated: if still columnar, apply proposal #1 (normalize
   to child rows on sync); if already migrated to related table, forms should reflect it.

---

### 26-150 Derail (derail_inv_pt)

**Form file**: `26-150 Derail Inspection Form.xlsx` (104 questions, 43 choice rows)

**Layer**: `derail_inv_pt`

**Design**: Derail type (portable, portable ramp, switch, fouling-point, siding, portable car mover),
location, condition, year installed, make/model, track-specific details.

**Key fields**:
- Derail type: `drl_type` (domain: SLD, HNG, SWP, OTH; proposal notes `OTH` found #6)
- Make/model: free TEXT 50
- Year, condition (domains), location (text)

**Disagreements**:
- **[T-5 open]** `drl_type` domain already has `OTH`; but form likely does not have a structured
  companion text field for "other" derails. Verify whether form captures free text when `OTH` is
  selected.

**Free text and `OTHER` use**:
- `drl_type` has `OTH` code; companion text field unclear from template names.
- `*_mfr` (free TEXT 50): no domain.
- Notes (free TEXT 255).

**What PROPOSAL §6.3 would change**:
1. If `drl_type` + `OTH` is already structured with companion text, this form **already follows
   the pattern** and needs only to add `OTH`/`TBD` to any free-text-only fields.
2. Derail subtype (e.g., portable ramp vs. portable) should clarify: is it part of `drl_type`
   domain or a separate field? If the latter, add `OTH` + text.
3. Make/model → not a domain question (equipment catalog reference, not a kind/type), stays free
   text or cataloged post-capture.

---

### 26-150 Generator (gen_inv_pt)

**Form file**: `26-150 Generator Inspection Form Schema 2.xlsx` (93 questions, 47 choice rows)

**Layer**: `gen_inv_pt`

**Design**: Generator type, fuel, fuel tank details, cooling, output, condition, year, related
wayside equipment.

**Key fields**:
- Generator type: domain
- Fuel type: domain
- Fuel tank: type (domain), material (domain)
- Cooling: type (domain)
- Output: text (kW, kVA, etc.)
- Related equipment: text asset ID joins

**Disagreements**:
- **[T-5]** Most fields appear domain-based already. Verify `GEN_TYPE`, `fuel_type` domains.
- **[P-4 identity]** `rel_` asset ID joins (text, not GlobalID edges).

**Free text and `OTHER` use**:
- Limited free text; most fields are choices (domains).
- Notes fields (free TEXT 255).
- Output in text (kW, kVA): not a domain (unit-bearing quantity).

**What PROPOSAL §6.3 would change**:
1. Any domain field missing `OTH` should add it + companion text (e.g., if generator type has
   no "other" code).
2. Output field (kW, kVA) is fine as-is (free text for units); future unit vocabulary (§6.1)
   may standardize this.

---

### 26-150 Rail (track_centerline or related)

**Form file**: `26-150 Rail Inspection Form.xlsx` (85 questions, 79 choice rows)

**Layer**: Unclear from name; likely a rail detail or rail condition assessment layer.

**Design**: Rail profile, weight, condition, wear, defects, ties, ballast, drainage.

**Key fields** (inferred from template):
- Rail profile: domain or text
- Rail weight: domain or numeric range
- Condition: domain (Excellent, Good, Fair, Poor, Failed)
- Tie type, spacing: domains/numeric
- Defects: free text + counts

**Disagreements**:
- **[T-6 constraints]** Numeric fields like `tie_count`, `cant_lanes`, `tie_spacing_in` (0–100 or
  range) have no RANGE domain; proposal suggests platform-side expectations.
- **[P-3 derived]** `failed_tie_pct`, `tie_pct_*` may be computed and checked against stored values.

**Free text and `OTHER` use**:
- Rail profile: check if domain or text (proposal suggests free text + domain for known profiles).
- Defect description: free TEXT 255.
- Notes: free TEXT 255.

**What PROPOSAL §6.3 would change**:
1. Rail profile (if free text today) → domain + `OTH` + text.
2. Numeric constraints (tie count, spacing, etc.) → platform-side expectations file (proposal #6);
   form stays numeric input, validation happens at sync.

---

### 26-150 Signal (sig_loc_inv_pt)

**Form file**: `26-150 Signal Inspection Form Schema 2.xlsx` (92 questions, 58 choice rows)

**Layer**: `sig_loc_inv_pt` (signal location)

**Design**: Signal location details, signal aspect configuration, heads (number, type, lamp type),
mast type, cantilever, bridge, bungalow (related ID), detector/relay connections.

**Key fields**:
- Signal location name: free TEXT 50
- Signal aspect configuration: packed text (proposal §8 suggests child rows or domain + grammar)
- Signal head: count + type (domain?)
- Mast type: domain
- Cantilever/bridge: type (domain), material (domain)
- Related bungalow/wayside/crossing IDs: text joins

**Disagreements**:
- **[P-8, issue #729]** `sig_config` (packed grammar: `-` tracks, `|` directions, `/` stacked
  heads) is free TEXT 50, narrow for real sites; proposal suggests child rows + raw text.
- **[P-1 slots]** Signal heads may be slotted (head1..4 type, lamp type) if not child-rowed.
- **[P-4 identity]** `rel_*` asset ID text joins.
- **[T-5 domains]** Mast type, cantilever type, bridge type should all have domain + `OTH` escape.

**Free text and `OTHER` use**:
- Signal aspect configuration: free TEXT 50 (grammar-encoded; not captured as domain).
- Signal head type: check if domain or text for "other" lamp types.
- Mast/cantilever/bridge material: domain-based (Wood, Steel, etc.).
- Notes: free TEXT 255.

**What PROPOSAL §6.3 would change**:
1. Signal configuration (`sig_config`) → leave as packed text for now; future improvement
   (proposal §8) is child rows or a configuration domain.
2. Signal aspect configuration (aspect codes) → domain + `OTH` for unknown aspects.
3. Mast/cantilever/bridge type → add `OTH` + companion text if missing.
4. Lamp type → add `OTH` + companion text if missing.

---

### 26-150 Tank (tank_inv_pt)

**Form file**: `26-150 Tank Inspection Form Schema 2.xlsx` (81 questions, 35 choice rows)

**Layer**: `tank_inv_pt`

**Design**: Fuel/water tank inventory: type (domain, e.g., 120g vertical), material, condition,
year, supports, related generator/wayside equipment.

**Key fields**:
- Tank type/size: domain (e.g., `rmi_trk_tank_size`: 120g_v, 240g_h, etc.; issue #908 embeds
  size and orientation in one code).
- Tank material: domain (Steel, Fiberglass, Plastic, etc.)
- Condition: domain (Excellent, Good, Fair, Poor, Failed)
- Support type: domain
- Related equipment: text asset ID joins

**Disagreements**:
- **[T-5, issue #908]** Tank size codes like `120g_v` (size + orientation) are parsed in TIVS,
  not split in the schema. Proposal suggests decode table if ever split.
- **[P-3 derived]** If tank type and size are separate fields, `has_tank`/`tank_cnt` is derived.
- **[P-4 identity]** `rel_gen_id`, `rel_wayside_det_id` (text asset ID joins).

**Free text and `OTHER` use**:
- Tank type: domain-based; verify if `OTH` code exists for unknown sizes.
- Notes: free TEXT 255.

**What PROPOSAL §6.3 would change**:
1. Tank size codes (e.g., `120g_v`) stay as domain codes (no domain redesign assumed in PROPOSAL);
   future work (#908) may split.
2. Add `OTH` + companion text to tank type domain if missing.

---

### 26-150 Turnout (Complex) (turnout_cx_inv_pt)

**Form file**: `26-150 Turnout (Complex) Inspection Form Schema 2.xlsx` (588 questions, 149 choice rows)

**Layer**: `turnout_cx_inv_pt` (complex trackwork, if `to_complex_type != NML`)

**Design**: The largest and most complex form. Turnout type (normal, complex, crossover, slip),
frog size, rail profile, switches (number, type, stand type, heater, machine), points, stand,
control, detector, and wayside equipment. Highly slotted (27 distinct slot groups proposed per
operator 2026-10-02, PROPOSAL §8.2).

**Key fields** (many):
- Turnout type: domain (NML, MPF, DIA_MPF, LAP_SW, DSLIP, TO_MPF, etc.)
- Frog size: domain
- Rail profile: domain/text
- Switches: numbered slots (switch1..6, each with type, stand, heater, machine)
- Points: numbered (point1..4)
- Stand type: domain (HAND, POWER, DUAL) per switch
- Switch machine: type (domain), make, year
- Derail: type, location
- Detector: type, zone
- Wayside/signal-related: text asset ID joins

**Disagreements** (major):
- **[P-1 slots, issue #1026]** 27 switch/point/stand/heater/derail/detector/equipment slot groups,
  totaling ~200 numbered columns. Proposal #1 (highest value) is to normalize to child rows on sync.
  This form defines the schema 2 slot structure as captured; whether it persists in real layers or
  has migrated to related tables (like `xing_struct_tbl`) is a drift finding.
- **[T-5 domains, open]** Turnout complex type (`to_complex_type`), switch machine type, heater
  type, point type: verify all have `OTH` or need it.
- **[P-4 identity]** `rel_*` asset ID text joins (wayside, signal, etc.).
- **[P-3 derived]** `has_*` (has_switch, has_derail, etc.) and `*_cnt` fields; if slots are
  unmigrated, they are second copies.

**Free text and `OTHER` use**:
- Turnout type: domain + "other" escape (form likely has `OTH` code or free-text notes).
- Switch/heater/machine types: domain-based; verify `OTH` escape.
- Make/model fields: free TEXT 50 (not domains).
- Notes: free TEXT 255.

**What PROPOSAL §6.3 would change**:
1. **Entire form structure** (PROPOSAL §8.2, §10 phase 8): if slots remain columnar after sync,
   apply proposal #1 (normalize to child rows). This is the "worked example" for TIVS asset
   sub-modules.
2. Add `OTH` + companion text to any domain field missing it (turnout type, switch machine type,
   heater type, point type, stand type, derail type).
3. After normalization, each slot group becomes a child row (one per switch, point, stand, etc.),
   with type, year, condition, equipment as columns; queries group by parent + position.

---

### 26-150 Turnout CX (MPF) and (Slip) (turnout_cx_mpf_inv_pt, turnout_cx_slip_inv_pt)

**Form files**:
- `26-150 Turnout CX (MPF) Inspection Form - Schema 2.xlsx` (220 questions, 149 choice rows)
- `26-150 Turnout CX (Slip) Inspection Form - Schema 2.xlsx` (243 questions, 149 choice rows)

**Layers**: `turnout_cx_mpf_inv_pt`, `turnout_cx_slip_inv_pt` (separate sub-types of complex
trackwork, as per PROPOSAL §8.2)

**Design**: Specialized forms for multi-point frog (MPF) and slip switch turnouts. Same structure
as complex form but with type-specific fields (MPF has extra frog details; slip has extra slip-specific
geometry).

**Key fields**: As complex form; possibly with sub-type-specific fields for MPF (frog angle,
frog type) and slip (slip angle, crossover points).

**Disagreements**:
- **[PROPOSAL §8.2]** These forms represent the split complex trackwork example: operator said
  "if we ever wanted to split Complex Trackwork up into its different types, which is probably
  best at some point, this would make it easy." The three forms (Complex, MPF, Slip) are the
  proposed split. After normalization by filter (PROPOSAL §10 phase 8.3), the generic complex
  form's "not NML" filter becomes "not NML and not claimed by MPF and not claimed by Slip";
  MPF and Slip filters are narrower. **No schema change needed; it's a filter registry in TIVS.**

**Free text and `OTHER` use**: Same as Complex form.

**What PROPOSAL §6.3 would change**:
1. Same as complex form: normalize slots to child rows if still columnar.
2. Add `OTH` + companion text to domain fields.

---

### 26-150 Wayside Detector (ontrk, offtrk) (wayside_det_ontrk_inv_pt, wayside_det_offtrk_inv_pt)

**Form files**:
- `26-150 Wayside Det (on-track) Inspection Form Schema 2.xlsx` (117 questions, 38 choice rows)
- `26-150 Wayside Det (off-track) Inspection Form Schema 2.xlsx` (81 questions, 19 choice rows)

**Layers**: `wayside_det_ontrk_inv_pt`, `wayside_det_offtrk_inv_pt`

**Design**: Wayside detector (train-detection equipment: inductive loop, axle counter, acoustic,
etc.) location, type, zone, related signal/track, condition, year installed, related wayside
equipment (e.g., bungalow).

**Key fields**:
- Detector type: domain (Inductive Loop, Axle Counter, Acoustic, etc.; proposed in catalog as
  `wayside.detector`, §7.3)
- Zone information: text/numeric zone ID
- Related signal/track: text asset ID joins
- Condition, year: domains/numeric
- Related equipment: bungalow ID, wayside module (text joins)

**Disagreements**:
- **[T-5, P-4]** Detector type domain may lack `OTH` code or proper companion text.
- **[P-4 identity]** `rel_sig_loc_id`, `rel_sig_id`, `rel_track_id`, `rel_bglw_id` (text joins).
- **[PROPOSAL §8.2]** Wayside detector is not a TIVS asset sub-module (no valuation); it's a
  component in other valuations (signal, crossing). May become a catalog reference in pricing
  (§7A) or a link (§4).

**Free text and `OTHER` use**:
- Detector type: domain; verify `OTH` escape + companion text.
- Zone ID: may be text or numeric (no domain).
- Notes: free TEXT 255.

**What PROPOSAL §6.3 would change**:
1. Detector type domain → add `OTH` + companion text if missing.
2. Zone information → if free text, consider domain if zones are standardized, or keep as
   numeric input with platform expectations (proposal #6).

---

## 26-210 project forms (2 forms, land valuation) — out of scope for design

The two forms are for land valuation and sales data, which MISSION.md and PROPOSAL §8.1 mark
as **out of scope for now**. Inventoried for the record; no design proposals.

### 26-210 Subject (parcel_fc or subject parcel)

**Form file**: `26-210 Subject Inspection Form.xlsx` (25 questions, 18 choice rows)

**Layer**: Subject parcel inspection (likely `subject_parcel_fc` or a valuation-specific layer)

**Design**: Subject property details: address, parcel information, land use, zoning, utilities,
improvements, depreciation drivers, approaches used, value estimate indicators.

**Key fields**: Subject property ID, land use, zoning, utilities (water, sewer, electric, gas,
telephone), structures on site, land area, value indicators by approach.

**Free text and `OTHER` use**: Land use, zoning, utilities are likely domain-based; others may be
free text (property description, depreciation notes).

**Finding**: This form and the comparable form are not analyzed for PROPOSAL §6.3 (domain +
`OTH`/`TBD` + companion text) because land valuation is tabled and out of scope for the rebuild.
The platform must eventually support these forms and the related layers, but design is deferred
(PROPOSAL §8.1, R-8 rewritten per 0.8 for project split #1981).

### 26-210 Comparable (comparable_fc or sale)

**Form file**: `26-210 Comparable Inspection Form.xlsx` (100 questions, 191 choice rows)

**Layer**: Comparable property inspection (likely `comparable_fc` or a sales-analysis layer)

**Design**: Sales data for comparable properties: property details (address, parcel, land use,
zoning), improvements (age, condition, gross living area, etc.), sale price, sale date, seller/buyer,
sale concessions, reconciliation notes.

**Key fields**: Comparable property ID, land use (domain), zoning (text), improvements (structure
type, condition, area), sale date, sale price, price per unit ($/SF, $/acre).

**Free text and `OTHER` use**: Land use domain; others mostly numeric or text (sale notes,
concessions, buyer/seller notes).

**Finding**: See Subject form above. Out of scope; no design proposals. Both forms define the
capture contract for land valuation; the platform must read and preserve them, but redesign is
future work.

---

## Cross-form findings and disagreements with PROPOSAL §6.3

### Summary of free-text and `OTHER` escape patterns (as deployed)

| pattern | count | forms | PROPOSAL change |
|---|---|---|---|
| Free TEXT fields for make/model (`*_mfr`) | ~10 across forms | all | Stay free text; catalog post-processes |
| Free TEXT `notes_*` fields | ~20 across forms | all | Remain free text (general comments) |
| Domain with `OTH` code + unstructured notes | ~8 (e.g., bglw_use → SIG_OTH) | Bungalow, Crossing, Signal | Formalize: add `OTH` + dedicated `*_other` companion text field |
| Domain with no escape code | ~12 (inferred from schema review) | all | Add `OTH` + `*_other` text field |
| Free TEXT for values that should be domain | ~15 (rail profile, turnout subtype, tank size variants) | Rail, Turnout, Tank, Signal | Retrospectively apply domain; capture free text until domain stabilizes |
| Packed text (e.g., `sig_config` grammar) | 1 (signal config) | Signal | Leave as free text; future child rows or domain codes (#729) |
| Numbered slots (switch1..6, point1..4, frog1..3, etc.) | ~27 groups, ~200 columns | Crossing, Turnout (all variants) | Normalize to child rows on sync (proposal #1) |
| Derived flags (`has_*`, `*_cnt`) | ~40–50 fields | all | Compute on sync; store as untrusted; report disagreement (proposal #3) |

### Forms already close to §6.3 pattern

- **26-150 Derail**: `drl_type` domain appears to have `OTH` code already; verify companion text field exists.
- **26-150 Generator**: Mostly domain-based; verify `GEN_TYPE` and `fuel_type` have `OTH` + companion text.
- **26-150 Tank**: Tank type domain has codes; verify `OTH` + companion text.

### Forms needing §6.3 retrofit

- **26-150 Bungalow**: `bglw_use` has `SIG_OTH`; add `OTH` + companion text; same for
  `bglw_class`, `bglw_mat`, condition.
- **26-150 Crossing**: Gate type, flasher type, cantilever type → domain + `OTH` + companion text.
- **26-150 Rail**: Rail profile (if free text) → domain + `OTH` + companion text.
- **26-150 Signal**: Signal aspect codes → domain + `OTH` + companion text; lamp types → domain + `OTH`.
- **26-150 Turnout (all variants)**: ~12 domain fields need `OTH` + companion text (turnout type,
  switch machine type, heater type, point type, stand type, derail type, frog type, etc.).
- **26-150 Wayside Detector**: Detector type → domain + `OTH` + companion text.

### Slot normalization priority (PROPOSAL #1, highest value)

Forms with numbered slot groups that should be normalized on sync:
1. **Crossing** (4–6 gates, 3+ flashers, cantilevers): ~36 columns, high repeating complexity.
2. **Turnout (Complex and variants)** (~27 slot groups, ~200 columns): highest complexity; operator's
   worked example (PROPOSAL §8.2).
3. **Signal** (if signal heads are slotted): medium complexity.
4. **Bungalow, Generator, Tank, Rail, Wayside Det**: lower or no slot complexity.

---

## GIS schema-review overlaps

**Proposal findings relevant to these forms**:

- **#1 (P-1 slots)**: Crossing (`xing_len1..6`, `xing_str_equip1..4`) and Turnout (all variants)
  define the worst case. Forms are the capture contract; normalization is sync-side.
- **#2 (T+P envelope)**: All forms use the 35-field envelope (milepost, status, notes, etc.);
  forms do not teach platform about envelope, only reuse common field names.
- **#3 (P-3 derived)**: All forms use `has_*` and `*_cnt` fields; sync should compute and validate.
- **#4 (P-4 identity)**: All forms use `rel_*` asset ID text joins; sync should resolve to GlobalID edges.
- **#5 (T-5 domains)**: These forms define the domain-check opportunity: ~20 fields with missing
  `OTHER` / `OTH` code and no companion text field pattern.
- **#6 (P-6 constraints, T-6 lint)**: Rail and other forms use numeric fields with no RANGE domain
  (rail weight, tie count, angle ranges); platform-side expectations suffice.
- **#9 (P-9 lat/long)**: All layers have `lat`, `long` fields with `attr_rule: true` (disabled
  or partially applied); platform should compute from geometry when null.

---

## Not verified

- **Live layer drift**: Forms are the capture design; whether published Portal layers match is
  not checked. Schema 2 slot structure persistence is a key uncertainty (does
  `xing_inv_pt` still have `xing_len1..6` or has it migrated to `xing_struct_tbl`?).
- **Data**: No data files (.gpkg) examined. Forms define the contract; real data is `data/`
  placeholder for phase 7 (PROPOSAL §10).
- **Dynamic behaviors**: Survey123 field app appearance, branching logic (`relevant` expressions),
  cascading selects (`choice_filter`), and media (audio, image) not analyzed in detail.
- **Field type mismatches**: Platform will validate collected data at sync; mismatches between
  form type and Portal field type are sync-time findings, not preview here.

---

## Recommendation for next run (0.10 or later, after approval)

After the operator approves PROPOSAL.md:

1. **Before SBIS/TIVS port (phase 9, §10)**: Cross-check live Portal layers against form definitions
   and schema 2 YAML (`rmigis-pyt/templates/`). Confirm slot structure (columnar vs. related table),
   field presence, domain codes, and enum escape patterns. Document any drift as a GIS schema-change
   proposal (§6.4).
2. **Survey123 form updates**: Apply §6.3 retrofit (add `OTH` + companion text to domain fields).
   No Portal schema change needed; forms change only. Apply when GIS domains are finalized (phase 6, §10,
   "publish GIS domains from catalog").
3. **Sync contracts (phase 1)**: Define per-dataset contracts for each form's layer (§6.2),
   including slot group declarations for normalization (proposal #1). Test with fixtures before
   phase 7 data arrival.
4. **Phase 7 (operator data)**: Run 26-150 data (when placed in `data/`) through the sync
   pipeline; validate envelope, child rows, derived facts, link resolution (proposals #1–4).
   This is the contract test before any module uses the data.

---

## Files and sources

- **Operator-provided forms**: `data/survey123/*.xlsx` (14 files, 2026-10-02 placement).
- **Current templates** (for comparison): `~/sources/rmigis-pyt/templates/` (track improvement,
  real property, building & site YAML; last commit 2026-09-09).
- **Schema review**: `docs/inventory/gis-schema-review.md` (task 0.5; top 10 findings referenced
  above by proposal number).
- **GIS schemas inventory**: `docs/inventory/gis-schemas.md` (task 0.3; field counts, domain
  definitions).
- **GIS tools inventory**: `docs/inventory/gis-tools-and-tiling.md` (task 0.4; sync and landing
  pipeline).
- **Architecture proposal**: `docs/architecture/PROPOSAL.md` (§6.3 domain + `OTH`/`TBD` + text,
  §8.2 TIVS asset sub-modules, survey123 change process implicit in §6.4).

