---
status: ruled
kind: architecture
date: 2026-08-04
refs: []
source_status: "Accepted (2026-08-04, owner sign-off same day — Signal Engineers onboard the week of 2026-08-04)"
imported_from: rmi-platform/docs/adr/0019-conversations-and-support-requests.md
imported_on: 2026-10-03
---
# 0019 — Conversations & support requests: a platform-owned collaboration layer

**Status**: Accepted (2026-08-04, owner sign-off same day — Signal Engineers onboard the week of 2026-08-04)

## Context

The Signal Engineers become active users this week. Their questions — "is this
crossing's config right?", "why is this component unpriced?", "how do I read
this page?" — currently have nowhere to live except email, which severs the
question from the data it is about. Issue #600 (owner idea 2026-07-27, scope
extended 2026-08-04) asks for three shapes of conversation:

1. **About an asset** — a TIVS asset, an SBIS bungalow or signal asset, a CIV
   asset.
2. **About a piece of equipment/component** — an SBIS catalog item or an
   equipment line.
3. **A plain support request** — "just TIVS/SBIS/CIV support requests," not
   anchored to any entity.

Plus an **Inbox** ("what's addressed to me") and **@mentions** ("I flag
something to an engineer; an engineer flags something to me").

The owner's explicit design constraint: **extensible across
TIVS/SBIS/CIV/CVS/PM and every future module.** The platform already has the
patterns this needs: cross-cutting services live in `platform_core` with
per-module attachment points wired explicitly at composition (audit, storage,
documents — ADR 0012); module capability is declared in the `ModuleManifest`
and registered without auto-discovery (GIS slots — ADR 0007 #141; card
slots — #532); and the one shared topbar (`platform_core.web.chrome`, A2) means a
single chrome change reaches every module at once.

What must NOT happen: per-module conversation tables, module-specific columns
on a shared table, or a design where adding a module (or a new entity kind
inside a module) requires touching the platform service.

## Decision

**A platform-owned conversations service** (`platform_core.conversations`,
platform schema, platform Alembic chain) with **manifest-declared anchors**
and one Inbox.

### The anchor contract (the extensibility core)

Every conversation is keyed by an **anchor**:

```text
(project_id, module_key | NULL, target_kind | NULL, target_id | NULL)
```

- **Entity thread**: `(project, module, kind, id)` — e.g.
  `("26-150", "sbis", "bungalow", "1042")`, `("26-150", "tivs", "asset",
  "XN-04-000004")`. `target_id` is a STRING: modules key entities however they
  already do (int PKs, GIS asset ids) — the platform never interprets it.
- **Module support request**: `(project, module, NULL, NULL)` — the owner's
  third shape. A CHECK enforces `target_kind`/`target_id` both-set or
  both-NULL.
- **Project-level** (`module_key` NULL) is schema-legal but ships no MVP UI —
  a later surface, not a later migration.

Modules declare their anchor kinds in the `ModuleManifest`
(`conversation_anchors`: kind + label), and composition registers a
**resolver** per kind (the card-slot registry pattern, `platform_core.web.slots`
precedent): `resolve(project_id, target_id) → (label, url) | None`. The
resolver gives the Inbox and thread headers a human label and a deep link
("XN-04-000004 — Crossing → /sbis/assets/17"), and validates existence at
post time. An anchor whose kind is no longer registered (module removed,
kind retired) renders **inert-but-visible** — label falls back to
`kind · id`, no link — never a broken Inbox (the stale-loud posture).

Adding a module or a new entity kind = one manifest entry + one resolver
function at composition. Zero platform changes.

### Model (platform schema)

- `conversation` — anchor columns, `title` (nullable; support requests get
  one), `status` (`open` / `resolved`), `created_by`, timestamps. Indexed on
  the anchor and on `(project_id, module_key, status)` for the support queue.
- `conversation_message` — conversation FK, author, **plain-text body**
  (URLs linkified at render; no rich text in MVP), created_at. Flat threads —
  no nesting; `resolved` is the work-off state and reopening is just posting
  again (status flips to open on a new message after resolve — a resolved
  thread with a new question must not stay silently resolved).
- `conversation_mention` — message FK, mentioned `user_id`, `read_at`
  (nullable). Mentions are extracted at post time (`@username` against the
  project's users — below) and are the Inbox's backbone.
- Every write records through `DbAuditSink` in the same transaction (the
  audit-rides-the-caller's-transaction rule).

### Mentions & the Inbox

- `@username` resolves against **users with effective access to the thread's
  module on the thread's project** (`AccessService`; super_admin implicit).
  An unresolvable mention posts as plain text — never a silent drop or a
  guessed user. There is no preview; the "loud" half is a note after posting
  (#776, 2026-09-16) naming each handle that notified nobody, and saying so
  when the author mentioned themself, which never notifies. An `@` inside a
  word (an email address) is not a mention.
- Every composer has an **@-typeahead** (#776): the kit's `mentions.js`, on
  every `document()`, reads `/conversations/mentionable?project=&module=`,
  the same addressable set less the caller. A composer opts in with
  `data-mentions`; empty means "read this form's project and module fields",
  which the Ask / report form uses.
- **Inbox** is a platform surface (`platform-web`, `/inbox`): Mentions,
  Replies (threads I authored or posted in), and a **Support queue** view
  (module support requests — visible to project admins, so the owner triages
  "TIVS support" in one place). Read/unread per mention; mark-read on view.
- The unread badge rides the shared `module_topbar` — one chrome change,
  every module (and the platform shell) shows it.

### Access

- **Read/post**: any user with effective access to the module on the project
  — viewers included, deliberately: conversation is not a data write, and
  engineers may be viewers on some modules. No new facet.
- **Resolve**: the thread author or anyone with `can_write` on the module.
- Support requests: author + project admins (the triage audience); entity
  threads: everyone with module access (the conversation lives next to the
  data, so its visibility matches the data's).

### UI attachment

- A shared `conversation_panel(...)` htpy component in `platform_core.web` —
  modules embed it on entity surfaces **adopt-as-touched** (the #143 rule).
  MVP adopters: TIVS asset pages, SBIS bungalow + signal-asset pages; CIV's
  panel rides #507/#453.
- An **"Ask / report"** entry in the shared topbar opens the module's support
  composer from any page — one click to shape 3.

### Non-goals (MVP)

Email/push notification depth (the badge suffices for this population — an
explicit later decision); rich text; file attachments (**#601 documents will
reuse this exact anchor contract** — same key, sibling service); realtime;
cross-project threads; editing/deleting messages (audited plain text stands —
corrections are replies).

*Amended 2026-09-16 (owner ruling, #777): an admin may REMOVE a post.* Live use
asked for it (a post on the wrong bungalow's thread). Authors still never edit or
delete their own posts, so corrections are still replies. What a super admin, or a
project admin on the thread's project, can do is soft-delete a post: the body is
blanked, the row stays as a "removed by an admin" tombstone so the thread keeps its
shape, its mentions leave the Inbox, and a `platform.conversation.remove` audit
event records who removed which post without keeping the text. The role is enough;
no ADR 0017 capability, because this is in-project administration of project data.

### Delivery

Three slices, each releasable: (1) platform service + migration + Inbox +
topbar badge + support composer; (2) SBIS adoption (bungalow + asset pages) +
mentions polish; (3) TIVS adoption + support-queue triage refinements. CIV
follows with #507.

## Consequences

- Every current and future module gets conversations by declaring anchors and
  a resolver — the platform service never changes for a new module (the
  owner's extensibility constraint, structurally enforced).
- The Inbox becomes the platform's first cross-module personal surface; the
  topbar badge is its one integration point.
- Support requests give module problems a first-class home and the owner a
  triage queue — replacing ad-hoc email from the engineers' first week.
- `#601` (documents on equipment) inherits a ready-made anchor vocabulary,
  keeping "conversation about X" and "document on X" addressable identically.
- New platform migration; no module migrations. Mention resolution couples
  the service to `AccessService` (read-only) — grants stay the one authority
  on who is addressable.
