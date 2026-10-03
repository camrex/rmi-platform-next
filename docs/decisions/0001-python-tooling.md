---
status: ruled
kind: architecture
date: 2026-06-03
refs: []
source_status: "Accepted (2026-06-03)"
imported_from: rmi-platform/docs/adr/0001-python-tooling.md
imported_on: 2026-10-03
---
# 0001 — Python tooling: uv + ruff + pytest

**Status**: Accepted (2026-06-03)

## Context

The platform is a multi-package Python repo (`platform/`, `modules/sbis/`, future modules) that needs reproducible environments, fast CI, and consistent lint/format/test conventions from day one. Options considered: `uv`, Poetry, pip-tools.

## Decision

Standardize on:

- **uv** for Python version pinning, virtual environments, dependency resolution, and lockfiles (`uv.lock`).
- **ruff** for linting and formatting (single tool, replaces flake8/isort/black).
- **pytest** for tests.

CI baseline runs, on every PR: `uv sync`, `ruff check`, `ruff format --check`, `pytest`. A type checker (mypy or pyright) is expected; the specific choice is deferred to the scaffold but the core is written type-annotated.

## Consequences

- Fast, lockfile-reproducible installs locally and in Docker (multi-stage builds use `uv` to produce a pinned environment).
- One tool for lint+format reduces config surface and pre-commit friction.
- Contributors must install `uv`; mitigated by documenting it in the repo README and pinning a version.
