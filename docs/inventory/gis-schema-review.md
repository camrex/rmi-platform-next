# GIS schema review

**Task 0.5.** Review of the field catalogs, domains and feature-class YAML that define the Portal layers, and of how the platform consumes them.
**Sources** (read-only): `~/sources/rmigis-pyt/templates/` (newer, last commit 2026-09-09, used for every count below unless stated), `~/sources/rmigis-agp-toolbox/templates/` (older, one commit 2026-08-15), `~/sources/rmi-platform/platform/src/platform_core/arcgis/`, `~/sources/rmi-platform/modules/tivs/src/tivs/assets/`, and issues in `~/sources/rmi-platform-issues/issues/`.
Earlier inventory: `docs/inventory/gis-schemas.md`, `docs/inventory/gis-tools-and-tiling.md`, `docs/inventory/rmi-platform-issues.md`.

## The constraint on every proposal

**None of these assumes the Portal changes.** The live feature service stays the schema authority (`tivs/assets/envelope.py` docstring; `FieldInfo` carries the coded-value domains). Every proposal is one of:

- **P** — platform side only. Works against today's layers unchanged.
- **T** — template/tooling side (`rmigis-pyt` YAML or loader). Changes what the *next* layer build or a lint says. It never edits a published layer.
- **O** — optional ask to the schema owner. The platform must work the same if it is declined.

## Method and caveats

I loaded the three template bundles with the `rmigis-pyt` resolution rules (catalog `inherit`, per-FC `fields_order`) and counted. Counts are from the YAML, not from a live service, so they describe *what the templates declare*. A published layer may lag them; #1042 shows 26-160 layers with no lat/long rule at all. The two repos differ, and a few defects below exist only in the older `rmigis-agp-toolbox` (marked). I did not read the Portal, Survey123 forms or any data.

## Shape of the schema (measured)

| bundle | catalog fields | FCs/tables | domains | field slots across FCs |
|---|---|---|---|---|
| `trk_impr` | 570 (298 TEXT, 246 SHORT, 18 DOUBLE, 3 DATE, 1 LONG + system) | 21 | 59 | 1,413 |
| `real_prop` | 283 (161 TEXT, 58 DOUBLE, 41 SHORT, 13 LONG, 6 DATE) | 10 | 34 | — |
| `bldg_site` | 61 | 3 | 16 | — |

- **419 of 570** `trk_impr` fields are used by exactly one FC; 35 fields appear in 15 or more of the 21 FCs and make up 648 of the 1,413 slots. That set is the de-facto envelope: `asset_id`, `mp_pre`, `mp_rr`, `mp_meas`, `rr_subd`, `rr_fac_num`, `location`, `section`, `dens_class`, `status`, `lat`, `long`, `include`, `insp_*`, `notes_*`, `flex_attr1..5`, `schema_version`, editor tracking. The platform re-declares it by hand as `ENVELOPE` in `tivs/assets/envelope.py`.
- The only non-nullable fields are `OBJECTID` and `GlobalID`. Defaults exist for `inspected`, `schema_version`, `equip_qty` (trk) and a handful in real_prop.
- `GlobalID` is on 33 of 34 FCs/tables (`costarexp_fc` is the exception, an export layer).
- `rmigis-pyt`'s loader is strict: `extra="forbid"` models, duplicate-key detection, and unresolved names raise `SchemaValidationError` (`src/rmigis/core/schema/loader.py`). The toolbox reported unresolved names but nothing was found that consumed the report. So the typo class below is mostly closed in the newer repo.

---

## Findings and proposals, ranked by value

Value = how much sync, validation or query pain it removes, weighted by how many layers and issues it touches. Effort is rough.

### 1. Numbered slot groups → normalise on sync into child rows (P, and O for new layers) — **highest**

**What.** About 190 of 1,413 field slots (≈13%) are numbered-slot columns: `turnout_cx` 76 of 159, `xing` 36 of 115, `wayside_det_ontrk` 26 of 102, `track_centerline` 24, `diamond` 16, `tank` 4. Groups seen: `ts1..6` (type, year, tie %, surfaced), `frog_*1..3`, `point_*1..4`, `stand_*1..3`, `heater_*1..3`, `dd_*1..4`, `xing_len1..6`, `trk_*_div1..2`, `rel_bglw_id1..2`. Each slot repeats 4–7 attributes. (Regex count; ~204 by a looser pattern in an earlier pass. The point is the order of magnitude.)

**Why it matters.**
- The type list is a hard ceiling. #1026 says detector types outgrow four slots. #746 asks to retire `xing_str_equip1..4`.
- TIVS has to key on position: `surf_type1..6` and `xing_str_equip1..4` rules are POSITIONAL (`tivs/consumption.py` ~L177). `turnout_complex.py` has to say "the TRACKWORK slots are not coalesced" because 27 of the 27 DSLIPs really use slot 3. Two consumers of the same columns read them two ways.
- `turnout_pnt_fc` (101 fields) and `turnout_cx_pnt_fc` (159) already disagree on the shape of the same idea: the plain turnout has *unnumbered* `frog_size`, `heater_type`, `stand_type`, etc. (24 fields only in the plain layer, 77 shared).

**Precedent already in the schema.** `xing_struct_tbl` (one row per structure, relation `xing_to_struct_rel`, `parentglobalid` ← `GlobalID`) and, in the newer repo, `wayside_det_eq_tbl` (one row per model per track, `equip_qty`, `equip_family`, domain `rmi_trk_wayside_equip`). Design: `rmi-platform/docs/planning/WAYSIDE_DETECTOR_TABLE_DESIGN.md`. Owner note on #1026 (2026-08-12): consider it, do not lock in.

**Proposal.**
1. **P:** the sync/landing layer defines a *slot group* declaration (prefix, suffix set, max index) and lands one normalised child row per non-empty slot: `(parent_feature_id, group, position, type, year, cond, …)`. Positional keys and "first non-null" coalescing become queries over child rows. This works on today's layers and on tomorrow's related tables, because both produce the same child-row shape. It is also the seam #1028 wanted.
2. **O:** new asset families use a related table as `xing_struct_tbl` does. Do not migrate the old layers.

Cost: medium (one declaration per group, about eight groups). Removes a whole class of positional-rule code.

### 2. One envelope, declared once (T + P)

**What.** The ~35 shared fields are repeated in every FC YAML's `fields_order` and again in `tivs/assets/envelope.py`. Alias and type drift is the result:
- `equip_year` / `equip_cond` were aliased "Crossing Equipment …" in the toolbox and became "Equipment …" in `rmigis-pyt` once the detector table shared them.
- `sig_loc_name`, `sig_loc_plan`, `sig_strip_map`, `rel_sig_loc_id` occupy 52 slots.
- `status` is a real field in trk (TEXT 50, **no domain**), and `real_prop` defines a *second* different catalog entry that collides on the column name `status` (the catalog keys are `sale_status`, `sale_substatus`, `sale_status_notes` but the column names are `status`, `substatus`, `status_notes`; the catalog also has an unrelated real `status`).
- `dens_class` is a field on 18 of 34 FCs but only four TIVS sources read it (envelope docstring).

**Proposal.**
- **T:** a `templates/envelope` group in the catalog that every FC pulls by name, so adding a layer cannot forget or re-type it. `rmigis-pyt` already supports `templates:` with `inherit`.
- **P:** generate `ENVELOPE` in the platform from the *live* layer's `FieldInfo` rather than transcribing (it already validates contracts against the service at sync time). Fail loud on type mismatch, which `landing.py` reports as `bad_type` gaps today.
- Rename real_prop's colliding catalog key/column pair *in the catalog only*, so key == column name (`name:` ≠ key is the trap).

Cost: low. Value: removes the manual transcription that `envelope.py` says it did ("transcribed … rather than decided").

### 3. Derived facts stored as attributes: treat as untrusted on sync (P)

**What.** 46 slots are `has_*` flags and ~35 fields are `*_cnt`/`*_qty` counts, many derivable from other data. Examples: `has_stand`/`stand_cnt`, `has_heater`/`heater_cnt`, `has_xing`/`xing_cnt`, `has_signal_str`/`signal_str_cnt`, `has_wayside_det_eq`/`wayside_det_eq_cnt`, `frog_cnt`/`point_cnt` vs populated slots, `bungalow.xing_cnt`/`xing_str_cnt`, and `sig_head_1asp_cnt..4asp_cnt` vs `sig_config` (#729). `equip_summary` (TEXT 255) and `str_code` (TEXT 50) are packed summaries of the structure table rows that `field_grammar.py` decodes.

**Why it matters.** Each is a second copy of a fact that can disagree with the first, and nothing checks. `has_switch_machine` (#747) is a fresh example.

**Proposal (P).** Compute the truth on sync (child rows from #1, counts from relations) and land the stored value beside it; report disagreement as a data-quality finding the same way `landing` reports gaps, never overwrite. Do not use the stored flag for pricing where a child row exists. **O:** stop adding new `has_*`/`_cnt` fields; the GIS-write design (attribute updates via the deferred change queue in MISSION.md) is not a place to keep them in sync.

### 4. Identity: asset_id has no uniqueness, and `rel_*` links are text joins (P, then O)

**What.**
- `asset_id` is TEXT 12 in the catalog, on 22 of 34 FCs, with no unique or index declaration; the builder makes none. The platform already knows it is not unique ("asset_id is not unique per segment": `modules/tivs/tests/test_tivs_frame_parity.py:83`; SBIS refuses a duplicate: `test_sbis_pg_create_unlinked.py:179`).
- 61 catalog fields start with `rel_`. Of those, `rel_xing_id`, `rel_gen_id`, `rel_tank_id`, `rel_sig_id`, `rel_sig_loc_id`, `rel_det_site_id`, `rel_bglw_id`, `rel_bglw_id1`, `rel_bglw_id2` (on six FCs: xing, gen, signal and the three wayside-detector layers; the numbered and un-numbered forms differ per layer) and `rel_trk_id*`/`rel_parent_trk_id*` (22 fields each, 32–34 slots) hold *asset IDs*, not GlobalIDs. Only `xing_struct_tbl` uses a real relationship class with `parentglobalid`.
- Settled decision (`rmi-platform-issues.md`): GlobalID is the stable key; asset ID is display and write-back text.

**Proposal.**
- **P:** the platform resolves every `rel_*` to a GlobalID at sync (`globalid_for_asset_id` exists already per OWNER_RULINGS L865) and stores the *resolved link* as a first-class edge `(from_feature, to_feature, via_field)` with unresolved and ambiguous links as findings. Queries join on edges, not on text. This turns "which signals belong to this location" into one index scan.
- **P:** a per-dataset `asset_id` uniqueness check on landing, reported not enforced.
- **O:** publish the same link check as a nightly report so the owner sees the collisions. No layer change needed.

### 5. Domains: fix in the template repo, normalise on the platform (T + P)

**Measured defects** (the fixed ones are noted so a reader does not chase them):

| defect | evidence | status |
|---|---|---|
| Yes/No triplicated | `rmi_trk_yes_no`, `rmi_yes_no`, `rmi_bs_yes_no` are byte-identical 0/1 | open |
| Rating triplicated and different | `rmi_trk_rating` (Failed…New), `rmi_rating` (0 = "Not"), `rmi_bs_rating` | open |
| `include` and `fence_type` use a different domain per bundle | `include` SHORT, domain per bundle; #896 adds `include` to `xing_str_tbl` | open |
| Year range drift | `rmi_trk_year` 1880–2030, `rmi_bs_year` 1850–2030; both hard-coded to 2030 | open |
| Numeric codes in TEXT domains | 7 CODED TEXT domains with int/float codes, e.g. `rmi_trk_frog_sz` (8.5), `rmi_trk_weight`, `CL_DEEDC`, `CL_TRNTP` | Handled by `DomainDef` normalisation in `rmigis-pyt`; the platform must do the same |
| Codes embed data | tank codes like `120g_v` (#908, size and orientation in one code); lower-case codes in `rmi_trk_tank_size`, `rmi_trk_gen_size_unit`, `rmi_status_costar` | open |
| Duplicate labels | `CL_DEEDC`, `CL_LUSE`, `CL_PROPIND` | open |
| No escape code | 21 of 57 (older count) trk domains have no OTHER/UNKNOWN | open |
| YAML boolean trap | toolbox `bldg_site_domains.yaml` L840 `[OFF, Office]` loads as `False` (YAML 1.1); pyt quotes it (`"OFF"`) | fixed in pyt |
| Malformed pair | toolbox `CL_SALECD` `[C Confirmed]` (one element, merges two code sets) | fixed in pyt (`[C, Confirmed]`), but the domain still mixes the CoreLogic sale codes with a local one |
| `stand_comp`, `heater_comp` | catalog entries used by no FC (the numbered `stand_comp1..3` variants are used); domain-bearing length 20 for a max code length of 8 | delete the two unused entries |

**Proposal.**
- **T:** one shared `rmi_yes_no`, `rmi_rating`, `rmi_year` (upper bound computed at build, not typed), with per-bundle names as aliases only when the published layer already uses them. Add a lint to the `rmigis-pyt` loader: duplicate labels, lower/mixed-case codes, unquoted YAML 1.1 booleans, domain with no OTHER/UNKNOWN (warn only).
- **P:** the platform matches values to domains **case- and type-insensitively** and returns `(code, label)` for every coded field via `FieldInfo`, so `120g_v` never has to be parsed in TIVS. Put a decode table for #908's case sizes next to `field_grammar.py` rather than asking for new codes.
- **O:** if the owner ever splits `tank_size` into size and orientation, the decode table is the migration path.

### 6. Constraints: ranges the schema never states (T for the new lint, P for validation)

**What.** Only 2 RANGE domains exist in trk (`rmi_trk_year`, `rmi_trk_qty_min1`) and 1 in bldg_site; real_prop has none. 92 of 246 trk SHORT fields have no domain at all and are neither slot nor coded; they include obvious ranges: `section`, `num_tracks`, `tie_count`, `cant_lanes`, `route_a_bearing_deg`/`route_b_bearing_deg` (0–360), `cross_angle_deg`, `max_speed_*_mph`, `failed_tie_pct` and `ts*_tie_pct` (0–100), `*_qty_*`, `tie_spacing_in`. Also 8 `*_type` fields with no domain and all 17 `_mfr` fields free TEXT 50.

**Proposal.**
- **P:** put ranges in a platform-side *expectations* file (field → range/regex), applied at landing as advisory `out_of_range` gaps beside `missing_value` and `bad_type`. This does not require a Portal domain and can be built field by field from measured data, as #1039 and `dens_class` were.
- **T:** add the same ranges as RANGE domains only to *new* FCs, where adding a domain costs nothing.
- **P:** for `_mfr` and `_type` free text, keep a normalisation map (case, whitespace, aliases) and report unmapped values, so a domain can be proposed from data, not from guessing.
- `section` is `required=True` on the envelope (#1039) though the schema says nullable: state the requirement in the expectations file, not in a Portal domain.

### 7. Same concept, two names or types (P now, O later)

| concept | inconsistency | note |
|---|---|---|
| Crossing angle | `cross_angle_deg` SHORT and `xing_angle_deg` TEXT 5 with domain `rmi_trk_xing_angle` (code == label), same alias "Crossing Angle (deg)" | a numeric field and a bucket for one fact |
| Dates | real_prop `sale_dt`, `rec_dt` are LONG (`parcel_etl.py` `sale_year()` slices `str(sale_dt)[:4]`, so the LONG is date-like; its exact encoding was not checked), while `costarexp` has `sale_date`, `rec_date` as DATE; `sale_year` SHORT is derived from the LONG | three types for one date |
| Year built | `year_built` and `yr_blt` | |
| Parcel APN | `apn` was 50, now 60 in pyt because `frm_apn` is 60 (#37); `sale_apns` grew to 1000 | length must follow the widest source; this is the recurring failure |
| Bungalow relations | `rel_bglw_id`, `rel_bglw_id1`, `rel_bglw_id2` across six FCs | numbered vs un-numbered differs per layer |
| Length units | `seg_len_mi`/`_ft` DOUBLE, `tie_sample_len_ft` SHORT, `xing_len1..6` SHORT, `fence_len_ft` DOUBLE, `sld_fence_len` SHORT (no unit in name) | int vs float for one dimension |
| Lat/long | on 22 of 34 FCs, `attr_rule: true`, but only bound to a rule where the tool applied one (#1042: 26-160 has none; 26-150 signal 82/352 null) | see #9 |
| Legacy detector layer | `wayside_det_pnt_fc` (52 fields in pyt; 93 in toolbox) overlaps `ontrk` (102) and `offtrk` (63) | superseded by site + `wayside_det_eq_tbl`; `wayside_migration.py` is the one-off |
| Sibling layers | `track_cl_parent` (44) / `track_centerline` (93) share 42; `subjectseg` / `subjectseg_line` share 54 of 55/56 (differ only in `Shape_Area`, `m_feet`, `m_miles`); `parcel_fc` (116) / `sale_fc` (101) share 83 | fine as layers, but all common fields should come from one group |

**Proposal (P).** A single *coercion table* in the platform: date LONG/DATE/TEXT → date, `xing_angle_deg` → number when parseable, `yr_blt`/`year_built` → one query name, length fields → float. It exists to give the query layer one name per concept (see #8). **O:** no schema change requested; if the owner does ever retire one of a pair, the coercion table is a one-line deletion.

### 8. Query/sync ergonomics (P)

- **Keys.** `gis_dataset_row` already has `feature_id` (GlobalID, OBJECTID fallback), `object_id`, `attrs JSONB`, `labels JSONB`. Add typed generated columns *only for the envelope*, which a Postgres generated column or view does; the rest stays in JSONB. Envelope fields are the ones every query filters on (`asset_id`, `mp_pre`, `rr_subd`, `section`, `include`, `status`).
- **Milepost.** `mp_pre` is TEXT 4, `mp_rr` and `mp_meas` are DOUBLE, so `mp_pre` + `mp_meas` is the line-referencing key. Land a computed sortable `(subdivision, mp)` and stop each module sorting differently.
- **Packed text.** `sig_config` (TEXT 50; grammar: `-` tracks, `|` directions, `/` stacked heads) has overflowed its own field on real sites (#729). `field_grammar.py` decodes it. Store the decoded structure as child rows via #1 and keep the raw text; widening it (#729) is then a convenience, not a prerequisite.
- **`flex_attr1..5`** (in 21 of 34 FCs) and 25 `notes_*` free text fields: land as opaque, never key a computation on them. `cost_tables.py:400` shows a schema-1 identity keyed on `flex_attr1`; retire it when schema 1 drops.
- **Schema era.** `schema_version` (default 2) is on 23 of 34 FCs; `inventory/models.py:622` already carries `schema_era`. Keep it: a value of NULL means Schema 1.

### 9. Lat/long (#1042) (P, T)

The rule is a vendored Arcade expression (`templates/attribute_rules/calc_latlong.arcade`, 1,232 coordinate-system codes) packaged by `attribute_rules.py` as an Export-Attribute-Rules CSV, applied **disabled**, triggered on shape only, and existing rows need a seeding pass. Only `parcel_fc` and `sale_fc` have an `attr_rule_path`; for the trk FCs the field flag `attr_rule: true` is documentation, not the binding (the pyt `field_defs.py` says attribute rules are "not field properties"). #1042's measured nulls sit in a few layers (26-160 derail 16/16, tank 8/8, turnout_cx 87/87; 26-150 signal 82/352).

**Proposal.**
- **P (no Portal change):** compute `lat`/`long` from the synced geometry in the platform when the attribute is null, and label the value `derived` in `labels`. That covers the layers where the rule was never applied and the platform's own map/CIV/TIVS use. Never write it back (consistent with MISSION.md: attribute updates only, via the queue).
- **T:** make `attr_rule: true` verifiable, i.e. a check in `rmigis-pyt` that an FC with a `lat`/`long` field lists its rule.
- **O:** applying the rule and running the seeding pass on the affected layers stays the owner's call.

### 10. Housekeeping (T, low)

- **Delete dead catalog entries:** `stand_comp`, `heater_comp` (unused as bare names; the numbered variants are in use). Toolbox-only: `assoc_blgw_cnt` typo in `bungalow_pnt_fc.yaml` (fixed in pyt), `has_sld_fence`/`sld_fence_len`/`sld_fence_side` legacy-only fields (in the toolbox; unused in pyt).
- **`lyrx` vs `styles`:** 9 real_prop templates have `lyrx` but no `styles`; `turnout_cx_pnt_fc` used `turnout_cx_inv_pt.lyrx` in the toolbox but `turnout_inv_pt.lyrx` in pyt (likely a copy-paste bug). Add a lint: `lyrx` must equal `base_name.lyrx` unless declared.
- **`reg_vers_en_rep: true`** is missing on `milepost_pnt_fc` (trk); real_prop has others. Say why in the YAML or set it.
- **Text lengths:** 92 of 120 domain-bearing TEXT fields in trk have length == longest code exactly. Not a bug alone, but every new code longer than the field breaks the load. The pyt `field_sync.py` compares lengths; a lint should warn when a domain changes without a length check.
- **`GlobalID`:** only `real_prop/costarexp_fc` lacks it; say in the YAML that it is an export layer, not a synced one.

---

## What each finding means for the rebuild

1. The sync layer, not the schema, is where the fixes go. Everything above can be built without a Portal change: child rows from slot groups, resolved link edges, derived lat/long, coded-value decoding, expectations file, coercion table.
2. The platform should treat the live service's `FieldInfo` as the **only** schema input and the YAML repos as *documentation for the owner*. Do not import the YAML at runtime; `envelope.py`'s hand transcription is the risk to remove, and generating from `FieldInfo` removes it.
3. Contract per GIS dataset (a plugin contract for the rebuild): `key`, `envelope`, `slot_groups`, `links`, `expectations`, `grammar`. Not a hand-typed `CalcField` list (~410 uses in the current code).
4. A schema-drift check (live `FieldInfo` vs the previous sync) would have caught #1042, #729 and the APN truncation.
5. TIVS snapshotting (MISSION.md) needs the normalised child rows in the snapshot, so it never re-reads slots by position.

## Open questions for the owner

- Are the older layers (`wayside_det_pnt_fc`, `turnout_pnt_fc` vs `turnout_cx_pnt_fc`) intended to converge on related tables, or should the fixed slot groups stand? (#1026's answer was "do not commit to either".)
- Which of the ~35 envelope fields does the owner consider *required* (the platform's `required=True` set is `objectid`, `globalid`, `section`, `include`)?
- Is `asset_id` supposed to be unique per layer, or per project, or not at all (it is not unique per segment)?

## Not verified

- I did not compare published layers to the templates; a layer can differ from its YAML.
- Counts of `has_*` (46) and `_cnt` fields are by name pattern.
- Which fields are referenced by Survey123 forms was not checked.
- "≈190 numbered slots" uses a name regex; a few unrelated fields (`tie_spacing_in`, `sig_head_1asp_cnt`) may be miscounted either way.
