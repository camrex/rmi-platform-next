# rmi-sbis-extract: signal bungalow equipment extraction pipeline

**Inventory of the extraction pipeline, catalog structure, outputs, and what SBIS can consume.**

Project repository: ~/sources/rmi-sbis-extract (read-only source).

**Corrected 2026-10-02 (task 0.7b)**: first written at `4caea94` (2026-09-29); re-read to `28d5bfe` (2026-09-30). Fixed: the "503 rows" and "27 of 503" statements, the catalog counts, and the new naming rule, documents and scripts (section "Added since first written" below). See `changes-since-2026-09-30.md` §2.

---

## What it does: end-to-end pipeline

The project reads railroad signal bungalow **as-built drawing sets** and extracts an **inventory of equipment with audit trails**. Its focus is relay extraction (the proof-of-method run on UP Geneva Sub CP Kedzie found 535 Type B relays, 129 Type J relays, 16 timers, with 499 at High confidence). It is designed to scale to all equipment classes (relays, timers, rectifiers, batteries, transformers, WIU/VIO, switch machines, chargers, comms, etc.).

The pipeline produces two things:
1. **Drawing parsing manifest** — what is on each page, its type, render kind (vector/scanned/mixed), with provenance.
2. **Contact references with audit trail** — `(relay, sheet, contact_position, front/back, method, location, confidence, source_document)` tuples, where every row is traced back to a specific drawing and specific sheet.

**Governing rule** (from HANDOFF.md): *"every part-number assignment carries a source and a confidence so a later correction propagates."*

---

## Pipeline stages (M0–M12, working documents in docs/)

### M0 — Ingest and sheet classification
- **Input**: PDF plan sets (e.g., `plans/kedzie/GENEVA_03.60-BUNG_1.pdf`, 6 locations, 143 sheets).
- **Process**: Read each page, infer sheet type (relay layout, rack layout, circuit, power distribution, tower indication) from title block and content, classify render (vector/scanned/mixed).
- **Output**: `conf/sets/kedzie.yaml` — manifest with 140 of 143 sheets identified from title blocks; 93 vector, 30 fully scanned, 20 mixed.
- **Code path**: `src/sbis_extract/ingest/classify.py`, `ingest/title_block.py`.

### M1 — Deterministic vector parsing (M1_FINDINGS.md)
- **Input**: Manifest, PDFs, roster (relay names and coil values per location).
- **Process**: Parse vector text layers on five sheet types:
  - **Relay layout sheets**: enumerate relay names and contact positions from layout stubs.
  - **Rack arrangement sheets**: read contact arrays by position from a legend.
  - **Circuit sheets**: match relay name + contact number (number below name) to a contact reference.
  - **Power-distribution sheets**: parse `nH`/`nF`/`nB` bus feed terminals as heel-contact evidence.
  - **Tower indication sheets**: extract bungalow-relay contact references wired to HLC inputs (cross-structure links).
- **Output**: 1,097 deterministic contact references (vs. baseline 1,069 in scope). Example: `(name="3RDR", sheet="12C", position=3, method=TEXT_PARSE, location="BUNG_1")`.
- **Confidence**: Method is `text-parse`, `power-dist`, `tower-indication`, or `vector-overlay` (2016 PTC overlays on raster sheets). No tier; deterministic parsers either found a reference or did not.
- **Code path**: `src/sbis_extract/parsers/circuit_vector.py`, `relay_layout.py`, `rack_layout.py`, `power_dist.py`, `tower_indication.py`, and orchestration in `pipeline.py`.

### M2 — Vision pass for rasterized sheets (M2_FINDINGS.md)
- **Input**: Pages classified as scanned or mixed; a roster; reference fixtures.
- **Process**: Tile rasterized sheets at 150 dpi, send tiles to Claude vision model with a structured prompt (schema-constrained extraction).
- **Output**: Corroborated, majority, or single-reader contact references per tile, with diffs against the fixture (487 chat-era reads, frozen). Example: `(name="3RDR", position=3, front_back="F", reading=CORROBORATED)`.
- **Confidence**: Deterministic (three independent readers, two agree, one disagreed) or majority/single-reader, scored against the fixture at 93% / 88% / 30% precision respectively.
- **Cost**: Billed per tile and cached by hash; can be preempted on a leased work queue (rmi-fleet contract).
- **Code path**: `src/sbis_extract/vision/client.py`, `runner.py`, `scoring.py`, and CLI in `cli.py --vision --confirm`.

### M3 — Identification (M4_IDENTIFICATION.md, infer/)
- **Input**: Contact references (name, coil value, contact features).
- **Process**: Match against a dictionary (YAML rules `conf/partnum/up.yaml`) that keys on coil + relay class + discriminating features (contact arrangement, polarity, release). Example: 500 Ω neutral with back-contact at position 5/6 → `56001-762-02` (A62-262, 6FB).
- **Output**: Part number with confidence tier. Of 676 Kedzie relays: 108 `Stated` (16%), 262 `High` (39%, discriminator tested), 211 `High (untested default)` (31%, default applied), 60 uncovered (9%).
- **Rules sourced to**: Alstom P1457 Table 7-11 (coil resistance), UP Material Reference sheets 16–18 (railroad tab decode), Siemens cross-reference, vendor catalogs.
- **Code path**: `src/sbis_extract/infer/identify.py`, `coil.py`, `contact_type.py`, `outlier.py`.

### M4–M8 — Verification and inventory proposal
- **Rack layouts** (M5): Read Mayfair rack legend and contact arrays to confirm part numbers (Confirmed tier).
- **SBIS reconciliation** (M7): Pull live SBIS catalog and instances; diff parsed relays against recorded inventory. At Kedzie: 676 relays on drawings, 75 relay units in SBIS.
- **Inventory command**: Propose new equipment by category (relays counted from drawings; non-relays proposed by text matching, tiers: Stated / Likely / Possible / In table).
- **Roster extraction** (M10): Count distinct relay designations per bungalow from circuit sheets (59% recall; the limiting factor is raster sheets without text layers).
- **Declaring sheet**: Identify which drawing declares an item (house diagram vs. part count vs. equipment sheet). At Bungalow A: 6 of 25 SBIS rows appear on the drawings; 19 do not.
- **Code path**: `src/sbis_extract/inventory/`, `sbis/`, `verify/`; commands in `cli.py`: `sbis-pull`, `sbis-check`, `sbis-queue`, `inventory`.

### M9–M12 — Envelope and future work
- **UP Asset Audit** (M11, M12): Received Sept 2026, independent source (not drawn off). Measures coverage gaps.
- **Lake Street field session**: Physical inspection to resolve thin identifications (Tower relays nameplate read, etc.).

---

## Catalog structure and model

### What the catalog is
A **single equipment part catalog**, designed to replace / restructure SBIS's `equipment_catalog` (503 rows on the 2026-09-20 copy; 505 on the 2026-09-30 copy, after SBIS removed 47, added 45 and rewrote 29 between copies). One **canonical definition** per physical item, with:
- All identifier forms (manufacturer part number, catalog number, railroad tab, railroad reference, competitor part, model designation, stock number).
- Identity attributes (coil resistance, contact arrangement, polarity, duty, release, contact material, family).
- Relations (plugs-into base, equivalent-to competitor part, is-part-of assembly).
- Classification (family hierarchy: relay → B1 / B2 / VTB → neutral / biased-neutral / etc., per manufacturer).
- Traceability (issuer per identifier, source document, confidence tier per identity claim).

### Why the redesign (CATALOG_ENTRY_SPEC.md §§ 1–6)
**Current SBIS catalog problems**:
- No single identifier present on all sources. Catalog keys on one; others are dropped.
- Compound identifier columns (`884 (G108)`, `580-588 (G142-145)`) cannot be joined.
- `display_name` holds four kinds of name (tab, catalog number, part number, placeholder) in one field.
- No issuer recorded, so `884` from a railroad cannot be distinguished from `884` from a vendor.
- No confidence recorded; two identical part numbers with different confidences become one row (uniqueness on `(bungalow, catalog_item)` erases the distinction).
- Discriminating attributes (coil, contact arrangement, polarity, duty) live as a sentence in `long_name` on 9 rows; unmapped on 494.
- No relation between parts (which relay plugs into which base, which cards make up which chassis).
- No distinction between a part (identity) and a part number (name). Catalog conflates them.

### Proposed shape (CATALOG_ENTRY_SPEC.md §§ 6–8, PART_JSON_MODEL.md)
**One JSON file per part**, one per-part catalog entry in the relational table, with:

**Core identifiers**:
```json
"identifiers": [
  {
    "value": "56001-783-02",
    "issuer": "Alstom",
    "kind": "ordering-number",
    "source": "Alstom 2019 Estimator's Guide p. 181",
    "valid_era": [null, null]  // open interval if era known
  },
  {
    "value": "A62-277",
    "issuer": "GRS",
    "kind": "catalogue-number",
    "source": "UP Halsted GEN00080 sheet 16"
  },
  {
    "value": "884A",
    "issuer": "Union Pacific",
    "kind": "railroad-tab",
    "source": "UP Halsted GEN00080 sheet 16"
  }
]
```

**Identity attributes** (the four fields that actually discriminate):
```json
"coil_ohms": 500,
"contact_arrangement": "4FB-2F-1B",
"polarity": "neutral",
"release": "standard",
"contact_material": "silver/carbon",
"duty": "standard"
```

**Classification** (path, not flat tier):
```json
"classification": ["relay", "b1", "neutral"],
"classification_aliases": {"GRS": "Type B1", "Siemens": "ST-1"}
```

**Relations** (stored as references, not name strings):
```json
"plugs_into": [{"part_id": "p0506", "note": "base"}],
"equivalent_to": [{"part_id": "p0400004", "issuer": "Siemens"}],
"is_part_of": [{"part_id": "p8000804460000", "quantity": 1}]
```

**Traceability** (per identity claim, not one tier for the whole row):
```json
"identity_sources": [
  {
    "claim": "coil=500",
    "evidence": "Alstom P1457 Table 7-11, entry A62-277",
    "confidence": "confirmed"
  }
]
```

### Implementation status
- **Data contributed day one**: 569 identifier rows transcribed from Alstom P1457, UP material reference, Siemens cross-reference (`conf/dictionary/`).
- **Catalog built from**: Alstom 2019 Estimator's Guide (relays p. 181–205; transformers, WIU/VIO, AFTAC II, NVHLC); Alstom P1457 O&M manual (parts catalog, Appendix A); Siemens SIE-RA-CMP-001-18-EN (cross-reference); Hitachi Rail RSE Product Catalog 2024 (US&S lineage); UP's own material reference (Halsted/Harvard sheets); 427 plan sets (identification by drawing evidence).
- **SBIS rows answered by a catalog part**: every one. `catalog/sbis_coverage.csv` (2026-09-30 copy, **505 rows**): 276 held (a number the row states finds a part), 49 declared by hand, 180 "as SBIS wrote it" (part keyed `sbis-<row id>`, no identifier; 95 of them installed in a bungalow). A handful of numbers on 6 rows still find nothing. *(Corrected 2026-10-02: this line said "27 of 503 SBIS rows"; that was an early resolution count, and 503 was the 2026-09-20 copy.)* Catalog size: **4,054 parts, 6,620 identifier values that find a part** (`catalog/README.md:13-14`; was 4,063 / 6,618 before the fresh copy).

### What it does NOT cover yet
- Non-relay equipment (rectifiers, batteries, chargers, transformers, WIU/VIO, POR/POK, timers, logic controllers, comms, switch machines, inverters, flashers) — in `Other_Equipment` as prose, needs structured extraction.
- GCS-issued identifiers (feature classes as catalog rows) — TIVS reads SBIS, never the reverse (ADR 0010), so GIS-issued part IDs are modeled as one issuer type with domain codes.
- Succession timing (which identifiers were current when) — left open pending a second railroad's material reference, since only UP data exists today.
- Assemblies vs. components pricing (does a valuation price a whole GCP 4000 or only its modules?) — owner to decide.

---

## What it produces: outputs and formats

### Drawing-based outputs
1. **Manifest (YAML)**: `conf/sets/kedzie.yaml` — sheet inventory, type, render, page count, title block provenance.
2. **Contact references (CSV/JSON)**: `kedzie_output/Kedzie_Interlocking_Consolidated_Relay_Inventory.xlsx` / JSON — 1,560+ rows with method, location, confidence, source sheet.
3. **Audit trail tabs** (in workbook):
   - `Relay_Master` — distinct relay names and coils per location.
   - `Contact_Refs` — every reference with method (text-parse, power-dist, tower, vision) and confidence.
   - `Not_High` — relays not pinned to the interlocking (36 of 676).
   - `UP_Tab_Decode` — 36 rows mapping railroad tab → part number → description (corrected from Halsted material reference).
   - `Alstom_A62_to_PN` — 111 rows, catalog → ordering number.
   - `Siemens_Alstom_Xref` — 83 rows, cross-manufacturer equivalence with attributes.
   - `PN_Dictionary` — 17 rows, drawing evidence → candidate P/N → tier.

### Catalog outputs (to SBIS)
1. **Equipment catalog loader**: Takes the JSON part files, produces SBIS rows. Maps old identifiers to new rows (handles cases like row 115 "ACSP/DCSP" → 4 distinct parts).
2. **Instance proposal**: `sbis-extract inventory` outputs `SBIS_inventory_proposals.csv` — tiers: `counted` (relay draws from drawings with quantity), `proposed` (text match, Likely tier), `confirmed` (present in SBIS), `recorded` (in SBIS's own source), `expected` (from prior statistics). Over 53 Incomplete/Partial bungalows: **688 instance rows** estimated.
3. **Reconciliation workbook**: Diff parsed relays vs. SBIS recorded inventory, flags: matches, conflicts, not-comparable (e.g., SBIS row 115 has four part-number candidates on the drawing).

---

## Architecture of the project

### Directory layout
```
rmi-sbis-extract/
  src/sbis_extract/
    cli.py                # command-line entry point
    pipeline.py           # orchestration: run (route all sheets to their parsers)
    dictionary.py         # lineage + coil + attributes → part number rules
    model/
      drawing.py          # DrawingSet, File, Sheet, Manifest
      evidence.py         # ContactRef, Method, PositionScheme, Reading, Provenance
      region.py           # ROI boxes for vision
      provenance.py       # InventoryBasis (documents, revisions)
    ingest/               # M0: read PDFs, classify sheets
      classify.py         # page → title block → sheet type / render / page number
      title_block.py      # parse title block fields (sheet id, revision, drawing #)
      manifest.py         # manifest YAML I/O and verification
    parsers/              # M1: deterministic vector parsers
      circuit_vector.py   # relay name + contact number → ContactRef
      relay_layout.py     # enumeration: find every relay on a layout sheet
      rack_layout.py      # read contact arrays from a rack legend
      power_dist.py       # parse heel-terminal feeds (bus + contact)
      tower_indication.py # cross-bungalow relay references
      contact_array.py    # decode contact stubs (front/back, position count)
      layout_raster.py    # tile a raster sheet for vision; join overlapping reads
    infer/                # M3: identify part number from evidence
      identify.py         # coil + relay class + features → catalog number + confidence
      coil.py             # parse coil values from text
      contact_type.py     # discriminate front/back from symbol geometry
      outlier.py          # flag relays whose coil is not in the dictionary
    inventory/            # M4–M8: reconciliation and inventory proposal
      expect.py           # which bungalows we have drawings for, estimate gaps
      propose.py          # text match + statistics → equipment proposals
      report.py           # render reconciliation workbook
      tokens.py           # every word of every sheet, indexed
      textindex.py        # build and query the index
      relays.py           # reconcile relays specifically
    sbis/                 # SBIS database I/O (only commands that touch a DB)
      *.py                # sbis-pull, sbis-check, sbis-queue, sbis-plans
    vision/               # M2: vision-model tile reader and orchestration
      client.py           # API call orchestration, caching, cost accounting
      runner.py           # tile, deduplicate overlaps, score against fixture
      schema.py           # structured output schema (closed Pydantic model)
      prompts/            # versioned vision prompts (relay_contacts_v1.md, etc.)
      scoring.py          # agreement measurement (corroborated / majority / single)
  conf/
    dictionary/           # source identifiers, mappings (yaml, tsv)
      up_material_reference.tsv          # 250 UP tabs / references / part numbers
      alstom_a62_to_pn.tsv               # 111 catalog → ordering number
      alstom_p1457_appendix_a.tsv        # 208 drawing → catalog → ED sheet
      alstom_p1457_coils.tsv             # 74 coil resistance → catalog
      siemens_xref_clean.json            # 83 cross-mfg equivalence
      uss_apparatus_winnetka.tsv         # 46 US&S apparatus reference
      up_stock_numbers.tsv               # 42 railroad stock numbers
      manual_parts.tsv                   # hand-curated thin identifications
    deltas/               # defects found in baseline, declared per location
      kedzie.yaml         # 11 corrections to Halsted baseline (P001–P006)
    sets/                 # manifests (generated from PDFs)
      kedzie.yaml         # ingest M0 output for Kedzie
    partnum/
      up.yaml             # dictionary rules: coil + class + features → P/N
  catalog/
    parts/                # one JSON file per equipment part (to be built)
    identify_queue.csv    # which parts need identification next
  docs/                   # reference and working documents
    READING_BUNGALOW_PLANS.md          # grammar: relay contract, coil fingerprints, sheet types
    CATALOG_ENTRY_SPEC.md              # requirements for equipment catalog (permanent)
    M0_FINDINGS.md .. M12_AUDIT_CABIN_REVIEW.md  # milestone findings
  scripts/
    build.py, pdparse.py, etc.         # chat-era parsing scripts (reference material)
    build_identify_queue.py            # rank what parts to identify next
    read_battery_callouts.py           # extract batteries by text matching
    read_wall_block.py                 # relay wall-block grids (Wood St, Harvard)
    read_up_stock_numbers.py           # search all sets for railroad stock numbers
    read_up_asset_audit.py             # reconcile UP audit vs. SBIS
  tests/                  # pytest suite (async-native)
  fixtures/
    sbis/                 # sample SBIS data (from prod copy)
    vision/               # frozen reference fixture (487 chat-era reads)
    local_vlm/            # local vision model test data
  plans/                  # PDFs (structure: subdirectory per railroad/location)
    kedzie/               # 6 bungalows + tower
    harvard/              # Mayfair, Clybourn, Wood St, etc.
    halsted/              # Halsted reference sheets
  pyproject.toml
  uv.lock                 # locked dependencies
```

### Key abstractions

**Drawing** (src/sbis_extract/model/drawing.py):
- `DrawingSet`: railroad, interlocking, set_id, files, manifests.
- `File`: path, location (structure name), sheets.
- `Sheet`: sheet label (e.g., "12C"), page number, type (relay_layout / circuit / etc.), render (vector / scanned / mixed).

**Evidence** (src/sbis_extract/model/evidence.py):
- `ContactRef`: relay name, sheet, contact position, front/back, method, location, confidence tier, reading (for vision).
- `Method`: TEXT_PARSE, POWER_DIST, TOWER_INDICATION, VECTOR_OVERLAY, VISION, OCR, MANUAL.
- `PositionScheme`: B1_PLUGBOARD (1–7), TIMER_TERMINAL (6, 7, 12, 13), TYPE_J_TERMINAL (12, 17, 22, 27, 32, 37), B2_TERMINAL.
- `Reading`: DETERMINISTIC, CORROBORATED (vision: 3 readers, all agree), MAJORITY (2+ agree), SINGLE_READER.

**Provenance** (src/sbis_extract/model/provenance.py):
- Every row carries document SHA256, page, sheet id, title-block fields, revision printed on the sheet.
- `InventoryBasis` records the set of documents and revision span.

### Parsers and logic

**Deterministic parsers** (all return `SheetResult` with `ContactRef` list):
1. **relay_layout**: Find stub blocks (contact arrays) by bounding box geometry or text proximity; read contact positions and count. Example: `1-8` means 8-position relay.
2. **rack_layout**: Decode legend rows (catalog number ↔ contact arrangement symbols); read cell by cell.
3. **circuit_vector**: Regex match relay name (with aliases) + contact-position number below it.
4. **power_dist**: Parse `nH` / `nF` / `nB` + terminal number as bus feed to a contact.
5. **tower_indication**: Match relay names printed on the page; resolve to a bungalow via ownership roster.

**Identification** (infer/identify.py):
- Input: ContactRef (relay name, coil value from roster or parsed from layout).
- Rules: Keyed on `(coil, relay_class_prefix, back_contact_count, polarity_symbol)`.
- Output: Candidate part number with confidence tier.
- Example: 500 Ω, class "GZR" (Type B1), back at position 5/6 → 6FB → A62-262 → 56001-762-02 at tier HIGH.

### Dependencies
- **pdfplumber>=0.11**: PDF text extraction and table reading.
- **openpyxl>=3.1**: Workbook writing (reconciliation output).
- **pydantic>=2.9**: Structured data models (vision schema).
- **anthropic>=0.69**: Claude vision API (M2 vision pass).
- **pytesseract, pillow**: OCR for scanned sheets (optional).
- **psycopg[binary], boto3**: SBIS database and S3 (optional, only for `sbis-pull`, `sbis-plans`).

---

## What SBIS can consume

### Inputs SBIS needs
1. **Relay count per bungalow** (`equipment_instance` with `count` field). Example: `(bungalow="BUNG_1", catalog_row=884, count=38)`. **Source**: relay rosters extracted from drawings (distinct names from circuit sheets) — today at 59% recall, limited by raster sheets.
2. **Non-relay equipment** (chargers, batteries, rectifiers, transformers, WIU/VIO, etc.) identified by **text matching and prior statistics**. Example: "GCP 4000 Comprehensive Single Track" appears on a plan set → propose at tier Likely.
3. **Part number corrections** for 27 SBIS catalog rows where the project found manufacturer P/Ns via two independent routes (UP material reference + Alstom guide).
4. **Equipment catalog replacement** (503 rows on the old copy, now 505; the "~300" figure is the entry spec's early estimate and is **not re-measured** — battery rows now go to cells, 51 → 21 in the spec; with identifiers and attributes properly separated). Includes a mapping table for existing instances (old row ID → new rows, noting granularity changes like row 115 → 4 parts).

### Outputs SBIS can produce (with the redesigned catalog)
1. **Equipment queries**: Find all relays with coil=500 and contact=4FB; find all parts equivalent to Siemens US2:400004.
2. **Verification reports**: Given a drawing set, flag which catalog rows are present, which are absent, which have disagreement on part number.
3. **Valuation support**: Price a bungalow's equipment from the catalog (once pricing is populated per part, per pricing source).
4. **BOM export**: Assemble a bill of materials from an instance list, with correct quantities (one row per part, not per physical unit arrangement).
5. **GIS seam**: Map external equipment (switch machines, ESL, SCC, detectors) via GIS issuer to catalog rows, enabling TIVS to link to the catalog without embedding knowledge of it (ADR 0010 contract: TIVS reads SBIS, not the reverse).

### Data contract (SBIS ↔ rmi-sbis-extract)
- **SBIS is the source of record for live inventory** (owner ruling, ADR 0010). This project's reconciliation reads SBIS and produces a proposal file, never writes back.
- **Identifiers go in an `identifiers` table** (one row per name, with issuer and kind), not compound strings in `display_name`.
- **Instance rows carry source and confidence** (new fields on `equipment_instance` or a separate evidence table).
- **Uniqueness on `(bungalow, catalog_item)` is dropped** if a bungalow holds the same item at two confidences (211 relays at Kedzie are untested defaults; same count, two evidence levels).
- **No part_number overwrite without evidence** — the 27 rows this project can resolve stay at reconciliation tier until imported with source documents.

---

## Known limitations and open questions

### Pipeline
- **Raster relay layouts** (Bungalow #2 sheet 45C is scanned, 0 relays declared) — vision pass is the only route. 7 of 53 queue bungalows sit on scanned sets (111 of 688 estimated instance rows).
- **Front/back contact type from vision** — 64% accuracy on Kedzie fixture; needs refinement or manual review.
- **Stub counting on layout sheets** — not yet automated; inferred from coil, not counted.
- **Thin identifications** (relays with no coil printed on any sheet, 151 of 364 Lake St Tower relays) — needs nameplate photograph or secondary document.

### Catalog
- **Granularity**: Is a GCP 4000 assembly one orderable thing, or only its modules? Owner to decide.
- **Dimensions vs. part number**: Batteries are identified by `(cells, amp-hours)` pairs; houses by size (`HS - 6X6`). Are these parts or attributes? Currently mixed.
- **Relations across lineages**: Do 83 Siemens/Alstom cross-references span all relevant parts, or only a sample? Measured on relays only.
- **GIS identifiers**: How are feature-class attributes (turnout.esl_type = "10A") mapped to parts? Domain code as issuer, or as an attribute? Unresolved.

### Coverage
- **Chandrayaan sets without text layers** (70 of 427 sets are fully scanned, unreadable by text extraction). Halsted material reference is one of them; its 250-row UP dictionary was read by manual OCR at 400 dpi, not by a text search.
- **Material reference sheets** (UP's is complete; do other railroads have one? Winnetka US&S sheet found as a second source; no third). Limits dictionary confidence.
- **Equipment classes beyond relays**: Rectifiers, timers, WIU/VIO have structured evidence on some sets; prose-only on others.

### What closes these gaps
- **Vision improvements** (better prompts, multi-page tile context).
- **Field sessions** (nameplate reads to pin thin tower relays).
- **Second railroad** (material reference sheets to test cross-railroad catalog model).
- **Vendor catalogs** (chassis bill-of-materials to model assemblies; second take on crossing/signal equipment).
- **UP Asset Audit integration** (independent source now available for reconciliation).

---

## Key reference documents in the repo

**Permanent (do not delete)**:
- `docs/READING_BUNGALOW_PLANS.md` — grammar for reading relay schematics; prerequisite for understanding every parser.
- `docs/CATALOG_ENTRY_SPEC.md` — requirements for equipment catalog, with evidence and reasoning (283 rows cited).

**Working (disposable)**:
- `HANDOFF.md` — what the proof-of-method run achieved, goals for next phases.
- `docs/CLAUDE.md` — chat-era session transcript summary.
- `docs/M0_FINDINGS.md` through `M12_AUDIT_CABIN_REVIEW.md` — milestone investigations.
- `docs/PART_JSON_MODEL.md` — draft JSON schema for catalog entries.

---

## Added since first written (2026-09-29 → 2026-09-30)

- **Fresh SBIS copy** rebuilt in `0d12964`; the build reads the most recent dated snapshot. Rules forced by it: a number shared by rows that name different parts is a *family* and joins nothing; a range written as one cell is not expanded.
- **Power branch naming**: where a rating is stated the part's name carries it (`Charger, 12 V 20 A, Cragg 20EC-12V`, `src/sbis_extract/catalog/power.py`, 23 parts); one top branch each for charger, arrester, transformer.
- **Batteries**: the cell is the part, a bank is a count; UP's `B` code names a (cell, count) pair as drawn at that document's date and is corroboration, never the key. Matches rmi-platform v1.59.0's cell model (#124).
- **Working docs**: `BUNGALOW_FUNCTION.md` (vocabulary for what a bungalow does, each term proved by named evidence, an absent link proves nothing; scored on 382 `Complete` bungalows); `M11_UP_ASSET_AUDIT.md`; `CHARGERS_AND_CELLS_CONSOLIDATED.md` (a proposal, not done: 14 charger rows → 14 + 5 rating-only lines; 22 cell rows → 5 sizes + 8 held); `UP_AUDIT_PLATFORM_HANDOFF.md`.
- **Snapshot** also pulls `bungalow_external_ref` and `dax_relation` (existing SBIS tables).
- **Scripts**: `audit_chargers_and_cells.py`, `audit_recorders_and_filters.py`, `derive_bungalow_function.py`, `collect_signal_readings.py`, `prepare_signal_job.py`, `read_safetran_catalog.py`, `read_signal_plans_api.py`, `refresh_prod_copy.sh`, `remote/signal_job.sh`. **Data**: `catalog/classification_review.csv`, `conf/dictionary/battery_banks.tsv`, `safetran_st_relays.tsv`.
- Owner, 2026-09-29: entries read consistently and carry only the source file and perhaps page, not narratives.

## Commands (CLI surface in cli.py)

```bash
# M0: Ingest and classify
sbis-extract classify <pdf>...              # page-by-page: sheet, render, type
sbis-extract propose  <manifest.yaml>       # (re)build manifest from drawings
sbis-extract verify   <manifest.yaml>       # diff manifest against drawings
sbis-extract basis    <manifest.yaml>       # document provenance record

# M1–M3: Parse and identify
# (run via Python scripts in scripts/ or through test fixtures)

# M2: Vision pass (costs money)
sbis-extract vision <manifest.yaml> --fixture <json>  # price a vision job
sbis-extract vision <manifest.yaml> --fixture <json> --confirm  # run it

# M4–M8: Verification and inventory
sbis-extract sbis-pull  --like '%kedzie%' --out data/sbis/kedzie.json
sbis-extract sbis-check <snapshot.json>
sbis-extract sbis-check <snapshot.json> --workbook <xlsx>
sbis-extract sbis-queue <snapshot.json>
sbis-extract sbis-plans <snapshot.json> -n  # fetch missing drawing sets from S3

sbis-extract inventory data/sbis/estate.json --csv proposals.csv

# Utilities
sbis-extract rack     <manifest.yaml>       # rack layout reconciliation
sbis-extract stubs    <manifest.yaml>       # contact stubs on raster layouts
```

---

## Test coverage
- **pytest suite**: Async-native, fixtures in `tests/`; covers parsers, identification, ingest, vision scoring.
- **Regression test**: `Contact_Refs` (1,560 rows) from proof-of-method run frozen in fixture; diffs against new parser output.
- **Marked tests**: `@pytest.mark.pdf` skipped if plan sets not present; others run offline.

---

## Entry points for SBIS integration
1. **Loader**: `sbis-extract` emits JSON/CSV; new loader reads it and updates SBIS catalog and instances.
2. **Reconciliation surface**: SBIS UI shows proposals from `sbis-extract inventory`, flags conflicts, allows accept/reject per row.
3. **Verification job**: Scheduled task runs `sbis-extract sbis-pull`, `sbis-check` against latest SBIS; emails diffs.
4. **GIS seam**: TIVS queries `sbis.equipment_catalog` by external equipment's GIS-issued identifier (feature class, attribute, value).
