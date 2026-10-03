---
status: ruled
kind: architecture
date: 2026-07-10
refs: []
source_status: "Accepted (2026-07-10)"
imported_from: rmi-platform/docs/adr/0012-platform-document-generation.md
imported_on: 2026-10-03
---
# 0012 — Document generation: platform-owned WeasyPrint service over htpy print templates

**Status**: Accepted (2026-07-10)

## Context

Three modules hold committed PDF consumers: SBIS's bungalow one-sheet (#32), CIV's approved Snapshot & PDF Export layout spec (#134), and TIVS's Wave 4 detail reports (#167) — with #33 already filed as the shared engine. The TIVS plan deferred the stack choice ([plan](../planning/TIVS_2_0_PLAN.md) §7 decision 6: "evaluate print-CSS before re-adopting WeasyPrint"), while #33's grounding and #134's spec both assumed WeasyPrint — a tension that had to be resolved once, platform-wide, before the second module built its own path.

Generated documents are **appraisal workfile artifacts**: they must be stored, batchable, and traceable to the exact code and template that produced them. That requirement drives the evaluation. Full audit and classification: [wave4-reporting-plan.md](../planning/wave4-reporting-plan.md).

Options evaluated per the plan's instruction:

- **Print-CSS in the browser** (user prints the live page): no stored artifact → no batch, no snapshot-attached PDFs, no provenance stamp. Fails the workfile requirement outright.
- **Headless Chromium server-side** (Playwright): can print live pages including JS islands, but adds a heavyweight moving part to the Lightsail container, and a live page violates the reports-from-snapshots rule (#167: "fed from valuation snapshots, not live recompute") — a nondeterministic base for a workfile artifact.
- **WeasyPrint** (pure-Python HTML/CSS→PDF): htpy components render to HTML strings (ADR 0004 — no new templating system), supports page CSS, fonts, embedded images, and SVG. Costs: native dependencies (Pango/Cairo stack) in the Docker image, and **no JavaScript** — charts and maps need server-side answers.

## Decision

**WeasyPrint, wrapped in a platform-owned document-generation service** (epic #208):

- **Platform owns** (`platform_core.documents` + print chrome in `platform_web`): the render service (pure `html + assets → PDF bytes`, with a **restricted resource loader** — WeasyPrint's URL fetcher resolves only allowlisted local/bundled assets and platform-mediated object-store images, and rejects arbitrary network schemes and private/loopback hosts, so rendering never becomes an SSRF surface), the base print template (letterhead slot, footer skeleton with disclaimer + provenance stamp + QR slots, page CSS, fonts), the QR/deep-link helper, batch orchestration (ARQ job, S3 artifacts via `scoped_key`, server-mediated streaming download), and the provenance stamp — `tivs/provenance.py` promoted to `platform_core` (third consumer reached: TIVS run tables, PDF stamps, SBIS one-sheet).
- **Modules own** what each document says: pure, tested `domain → htpy` assembly functions, layouts, vocabulary/guardrail rules, batch selection, and access-checked download routes. Modules never embed the PDF engine.
- **No JS in PDFs, by construction**: charts are server-generated SVG from typed htpy functions (TIVS-owned first, domain-free drawing core for later promotion); map images are captured per module — ArcGIS REST export-map through `platform_core.arcgis` (TIVS/SBIS) or client-captured PNG (CIV's existing save-view path). The platform template takes an image; where the pixels come from is module business.
- **Traceability**: every generated PDF is stamped (footer + generation record) with platform version, git SHA, template id + template version, timestamp, user, and source snapshot id where one exists; generation is audited via `DbAuditSink` in the caller's transaction. Template versions are code constants, not a registry table — templates are not user-editable.
- **Sync vs background**: single documents render synchronously in-request and are **stored, stamped, and audited before the bytes stream back** (store-then-stream — a workfile artifact exists for every generated document; any unstored "preview" path would be a separate, explicit decision). Batches run as ARQ jobs in the existing module-task pattern (#209), with a settings-knob threshold. A batch job cannot ride the caller's transaction, so the payload carries `project_id`, the actor (`enqueued_by`), and the source snapshot/selection ids; the worker re-checks authorization and records the audit row + artifact creation in its own transaction — mirroring the existing TIVS task pattern.
- Generated artifacts are retained indefinitely under `scoped_key` (workfile default; revisit with an explicit policy if storage cost ever matters).

Delivery order: #33 (render + base template + stamp) → #209 (batch) → consumers #167 (TIVS Wave 4), #134 v1 (CIV), #32 (SBIS, first batch exercise). The engine is a parallel platform slice inside TIVS Wave 4 — it does not gate #166/#165 and is not deferred past the wave (Wave 4's exit requires a deliverable).

## Consequences

- One engine integration, one Dockerfile change, one stamp implementation — instead of three module-owned WeasyPrint paths (CIV's spec and TIVS's Wave 4 would otherwise each have carried their own).
- Plan §7 decision 6 is resolved; #167 shrinks to TIVS content and gains explicit dependencies (#166, #33). #134 v1 and #32 become content-on-the-service.
- The Docker image grows by the WeasyPrint native stack — verify image size and cold-start on Lightsail in #33's PR before the dependency is committed. *(Verified 2026-07-11 in #217: 1.04 GB total, ~60–80 MB attributable; no Lightsail concern.)*
- The export-map fidelity check ran 2026-07-11 (#167 slice B/D): the org's federated services expose MapServer twins, so `platform_core.arcgis.export.export_map_image` returns service-symbology PNGs directly — schematic linework on white, which suits exhibit overview maps and sheet insets; basemap-composited insets remain available via the org's `Export Web Map` printing task when a consumer needs geographic context under the features (a refinement, not a blocker).
- Reports render only what snapshots/data provide — no live-page printing. If a future document genuinely needs a rendered JS surface, that is a new decision (headless capture), not a quiet extension of this one.
- Charts gain a server-side SVG idiom that the web surfaces (#165) reuse — one rendering for screen and paper.
- **The service has a rendered-row budget, and exceeding it kills the node rather than slowing it.** ~250 KB of peak RSS per rendered table row, with the cliff between 2,600 and 6,500 rows: past it the container is OOM-killed — `/healthz` fails, Lightsail replaces it, the requester gets a 502 and everyone else on the box gets a brief outage. *(Measured 2026-09-01 inside the production image under the real memory limit; method in #1399, not restated here.)* The working budget is **~2,500 rendered rows**, enforced by `render_pdf` (#1490) so an over-budget document fails with a nameable error instead of a dead container.
- **The budget is sized to the node and moves with it.** Production runs Lightsail power `small` — 1.0 GB per node, shared by api + worker + redis + alloy — with observed service usage of 274–367 MB, leaving the api ~885 MB and therefore ~3,000 rows, of which 2,500 is roughly a 20% margin. *(Measured 2026-09-02; owner ruled `small` the same day, explicitly subject to change if the container is resized — `medium` would put the budget near 6,000 and `large` near 12,500.)* More RAM moves the cliff; it does not remove it, so the design questions below apply at any size.
- **Three questions a new report design must answer before it is built:** how many rows does the widest instance *render* (not how many records it reads — if the answer is a rollup, say what it rolls up *by* and what bounds that dimension); is any rendered dimension unbounded by data growth (sections and processes are bounded by project design, assets and records and frames are not — a per-record row is the failure mode); and if it can exceed the budget it needs paging, server-side aggregation or a streaming writer, decided in the design rather than after the first OOM. A report that must list every record is legitimate — it just cannot be one WeasyPrint render of one HTML string. This gates #1202, #134, #32, #1298/#1299 and TIVS Wave 4, none of which are designed yet.
