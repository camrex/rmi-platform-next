---
status: ruled
kind: architecture
date: 2026-07-21
refs: []
source_status: "Accepted (2026-07-21)"
imported_from: rmi-platform/docs/adr/0015-browser-map-authentication.md
imported_on: 2026-10-03
---
# 0015 — Browser map authentication: server-minted, referer-bound app token

**Status**: Accepted (2026-07-21)

## Context

ADR 0007 covers server-side ArcGIS access (app-login over httpx, referer-bound) but
explicitly scoped out the browser: *"maps stay on feature services / the ArcGIS JS SDK
client-side (that model works well and is unchanged)."* That client-side model has since
grown into four surfaces — the SBIS Map page and per-bungalow map, the TIVS valuation
map, and the CIV corridor viewer — and its authentication was never a decision of record.
It was settled across issues #29 / #37 / #74, living only in code comments, memory, and
issue threads. Two recent events (the #359 login-prompt regression and its #360 hardening)
showed the cost of that gap: the auth model is load-bearing, cross-cutting, and easy to
"fix" into breakage.

The problem it solves: the ArcGIS Maps SDK renders secured Portal **web maps** and their
operational **feature layers** directly from the browser (`maps.rmigis.cloud`). Those
requests need an ArcGIS credential *in the browser*. Platform SSO (ADR 0007) only
*identifies* the user against the Portal — it does not leave a usable feature-service token
in the page. Two forces constrain the design:

- The Portal app's tokens are **hard referer-bound** to `https://apps.rmigis.cloud` by the
  app registration (a request with any other — or no — `Referer` gets `498 Invalid Token`).
- Project scope is **explicit, never ambient** (ADR 0013): a request without `?project=`
  resolves to no project, and in production a bare GET redirects to the picker.

## Decision

**Mint a short-lived, referer-bound app-identity token server-side and register it with the
SDK's `IdentityManager` in the browser.** Concretely:

1. **A module-gated, project-scoped `/token` endpoint** returns the token. Each map surface's
   route is a thin wrapper guarded by `require_module_access("<key>")`; the referer gate,
   mint, TTL, and payload live once in `platform_core.arcgis.browser_token_response`. The
   token is the **read-only app identity** (the same credential reconcile/discovery use),
   *not* per-user or per-project — but issuance is authorized per (user, project, module),
   and only to the bound origin (parsed-origin compare, not a `startswith`).

2. **The browser registers it through one shared helper** —
   `window.rmiRegisterMapToken(IdentityManager, url, projectCode, onStatus)` from
   `BROWSER_TOKEN_JS`. Every island calls it instead of hand-rolling `fetch` + `registerToken`.

3. **The token fetch MUST be project-scoped, and MUST fail loud.** This is where ADR 0013's
   "explicit project scope" reaches into the map layer: the `/token` route needs `?project=`,
   so the browser stamps it. An unscoped fetch redirects to the picker; the island then
   receives HTML, and — before the shared helper — swallowed the parse error and let the SDK
   fall back to a Portal username/password dialog on every load (#359). The helper *requires*
   a project code, stamps `?project=`, verifies the response is JSON, and surfaces failure to
   the console + a status line instead of silently degrading.

4. **Silent in prod, dialog elsewhere.** Where the page origin is the bound referer (prod),
   the SDK authenticates silently; a non-prod origin (localhost) gets no token and the SDK's
   own sign-in dialog is the fallback — the map still loads.

**Alternatives considered and rejected** (verified empirically under #74):

- **`IdentityManager.registerOAuthInfos` (browser OAuth).** Uses the user's own Portal
  identity — the "correct" per-user model — but shows a **one-time OAuth consent screen per
  user**, and marking the app org-trusted did **not** suppress it. Net UX regression versus
  the silent server token. Rejected.
- **Server-side request-interceptor proxy** (browser holds no credential; the server injects
  the token per request). The strongest posture, but the SDK does not route secured
  Portal/server requests through `esriConfig.request.proxyRules` (it self-authenticates
  direct), so it requires request *interceptors* — high effort. Deferred (#74), to be
  revisited only if the browser must hold no credential.

## Consequences

- **The browser holds a shared, read-only *bearer* token, by design.** Treat it as bearer
  credential exposure, not a leak to be "fixed": it grants only the read access
  reconcile/discovery already have. The referer binding blocks replay from a *browser* at
  another origin (browsers send an honest `Referer`) and scopes who we issue it to — but it
  does **not** stop a non-browser client that forges the header, so it is not a
  non-replayability guarantee. True per-user, non-replayable scoping (the proxy/interceptor
  path) is a **known, deliberate deferral** — #74.
- **One plumbing path, four consumers.** `platform_core.arcgis.browser_token` owns both the
  server mint and the browser helper; new map pages go through it and cannot re-introduce the
  #359 drift (unscoped fetch, silent failure). Behavior is tested in
  `platform/tests/test_browser_token.py`; module tests assert the delegation seam.
- **The map layer inherits ADR 0013's project-scope invariant.** Any browser call to a
  project-scoped platform endpoint must carry `?project=` and treat a non-JSON/redirect
  response as failure, not as "no token."
- **Basemaps stay anonymous.** The web maps' ArcGIS Online basemaps
  (`services.arcgisonline.com`, `cdn.arcgis.com`) are public and need no credential; only
  `maps.rmigis.cloud` resources are covered by the registered token.
- Supersedes nothing; **extends ADR 0007** into the browser it scoped out, and depends on
  ADR 0013 for project scope.
