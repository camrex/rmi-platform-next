---
status: ruled
kind: architecture
date: 2026-06-03
refs: []
source_status: "Accepted (2026-06-03)"
imported_from: rmi-platform/docs/adr/0003-async-worker-arq.md
imported_on: 2026-10-03
---
# 0003 — Async worker: ARQ on Redis

**Status**: Accepted (2026-06-03)

## Context

The core is async FastAPI. Background work is needed for ArcGIS sync, import/export pipelines, long-running valuation/rebuild operations, and document processing ([core spec §3.3](../planning/IDEAL_CORE_STACK_SPEC.md)). Candidates: Celery vs an async-native worker (ARQ / Dramatiq). The MVP-core surface (spec §12) does not strictly require a worker yet, but it will be stood up from day one so the pattern exists and the deployment topology is proven early.

## Decision

- **ARQ** as the worker runtime, **Redis** as broker/result backend.
- Rationale: async-native (matches FastAPI/asyncio without thread/process bridging), small operational footprint vs Celery, sufficient for current scale.
- The worker runs as a **separate container/service** in local compose and in the Lightsail deployment profile, sharing the platform settings/secret-loading and DB/session machinery.
- Job enqueue happens through a thin platform service boundary (not direct Redis calls from domain code) so the broker stays swappable.

## Consequences

- Local compose and the deploy profile include Redis + a worker service from the first scaffold.
- If scale or feature needs outgrow ARQ, the enqueue abstraction allows migration (e.g., to Dramatiq/Celery or SQS-backed) without rewriting domain code.
- Adds Redis as an operational dependency now; acceptable since Redis is also the natural cache/broker per the core stack.
