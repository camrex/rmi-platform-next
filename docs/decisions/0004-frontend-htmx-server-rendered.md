---
status: ruled
kind: architecture
date: 2026-06-03
refs: []
source_status: "Accepted (2026-06-03)"
imported_from: rmi-platform/docs/adr/0004-frontend-htmx-server-rendered.md
imported_on: 2026-10-03
---
# 0004 — Frontend: server-rendered + HTMX over a frontend-agnostic core

**Status**: Accepted (2026-06-03)

## Context

[Core spec §5](../planning/IDEAL_CORE_STACK_SPEC.md) recommends server-rendered FastAPI + HTMX as the default, but states the actual key decision is that the **core is frontend-agnostic** — identity, project, module-access, and domain data are exposed as Python services + versioned REST, and frontends are thin, reversible adapters that never own policy or data.

The SBIS reference app (`rmi-bglw-inv`) is FastAPI + Jinja2 + HTMX, but we are not bound to lift it verbatim. The goal here is the *ideal* fit for this platform's stated principles, not the flashiest framework.

## Decision

1. **Preserve the frontend-agnostic core as the primary invariant.** All identity/project/module-access/domain data flows through platform services and versioned REST. Frontends never authenticate, authorize, or reach data directly.
2. **Interaction model: server-rendered + HTMX** for the platform shell and SBIS. This keeps the thin, low-state, low-lock-in posture the agnostic-core bet depends on.
3. **HTML authoring: typed Python components** (composable, testable, single-language) as the target over stringly-typed Jinja templates. Validate this on the first dense SBIS form; **raw Jinja remains an acceptable fallback** and is fine for trivial scaffold pages (health, login). The specific component library is selected at scaffold time and is an internal, reversible detail.
4. **Explicitly not** Reflex / NiceGUI for the shell or SBIS: their stateful, app-owning model fights the frontend-agnostic principle.
5. **Streamlit** remains a first-class adapter for analytics/dashboard surfaces and as the TIVS/CVS migration bridge. **Next.js + TypeScript** remains the documented escape hatch for a future module that genuinely needs rich client-side UX — not the default, not the shell.

## Consequences

- The frontend choice stays reversible: because policy/data live in the core, an adapter can be replaced without core rewrites.
- Zero/low build step; single language (Python) end to end for the default path.
- Adopting a Python component layer is a bet validated on a real screen before broad commitment; if it disappoints, Jinja+HTMX is the fallback with no architectural change.

## Validation (2026-06-03)

Validated on the first dense SBIS screen (read-only bungalow list + detail). The selected component library is **htpy** (typed Python HTML, renders to strings, composes with FastAPI — no separate framework, no build step). HTMX live filtering works via the fragment-on-`HX-Request` pattern. The web layer lives in the SBIS module (`sbis/web/`) and composes over `platform_core`, keeping the core frontend-agnostic. The component approach is adopted; Jinja was not needed.
