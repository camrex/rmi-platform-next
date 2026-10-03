---
status: ruled
kind: architecture
date: 2026-07-03
refs: []
source_status: "Accepted (2026-07-03)"
imported_from: rmi-platform/docs/adr/0010-bungalow-inventory-sbis-source-of-record.md
imported_on: 2026-10-03
---
# 0010 — Bungalow inventory: SBIS is the source of record; TIVS consumes one seam

**Status**: Accepted (2026-07-03)

## Context

Bungalows are inventoried on two bases: **internal** (contents — equipment, main systems, DAX, batteries — SBIS's identity) and **external** (what the bungalow serves when contents are unknown — historically recorded in TIVS's ArcGIS inventory). TIVS 2.0 ([plan](../planning/TIVS_2_0_PLAN.md) §4.7) must value bungalows either way, and the obvious risk was two parallel inventory paths with basis-routing logic living in TIVS.

Separately, SBIS is already working toward **linking the related external assets** a bungalow controls (manual today; automation is an existing SBIS vision item).

## Decision

1. **SBIS is the single inventory source of record for bungalows, on both bases.** Internal (contents) and external (function + linked external assets) inventorying both live in SBIS.
2. **TIVS learns a bungalow exists from the ArcGIS inventory sync** (like any point asset), then obtains the full inventory — whichever basis — through **one read-only, service-mediated seam** into SBIS. SBIS reports each bungalow's inventory basis; TIVS's valuation-process selection follows it. No basis logic lives in TIVS.
3. **TIVS owns all valuation stages** (costing → RCN → depreciation → valuation) for bungalows, exactly as for every other asset: one cost library, one RCN engine, one depreciation engine, one rollup, one audit trail.
4. **The dependency is one-directional**: TIVS reads SBIS; SBIS never depends on TIVS. The seam is a Python service contract (module-to-module via services, per platform convention — no ORM joins across module schemas).
5. Basis is **per-bungalow, not per-project**: a bungalow moves from function-based to contents-based valuation automatically when its SBIS survey completes.

## Consequences

- SBIS gains two roadmap items: expose the inventory-basis/full-inventory contract for consumption, and automate external-asset linking.
- Costing/RCN machinery is never duplicated into SBIS; a bungalow's value lands in the same TIVS project rollup as every other asset.
- The seam is the platform's first real cross-module domain-data contract — its shape (service protocol, versioning, testing) becomes the precedent for future module-to-module consumption.
- If SBIS data is absent entirely for a project, TIVS bungalow valuation degrades explicitly (reported as missing inventory per plan §4.8), never silently.
- Evidence received from a third party (first: Union Pacific's signal asset audit, 2026-09-29) sits beside this inventory and never writes it. [ADR 0025](0025-third-party-evidence-reconciles-against-the-inventory.md) says what it may and may not do; nothing in it crosses the seam.
