# `make check` is the gate: lint, format, types, tests. CI runs exactly this.
# Tools come from uv (docs/TOOLCHAIN.md). Later tasks add checks to `check`.
# uv and make live in ~/.local/bin, which the runner's PATH lacks (docs/TOOLCHAIN.md).
export PATH := $(HOME)/.local/bin:$(PATH)
UV ?= uv

.PHONY: help sync lint format typecheck test check check-size check-core-clean check-isolation
help:
	@echo "make sync | lint | format | typecheck | test | check | check-size"

sync:
	$(UV) sync --python 3.12 --all-packages

lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format:
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

typecheck:
	$(UV) run pyright

test:
	$(UV) run pytest

check-core-clean:
	$(UV) run python scripts/check_core_clean.py

# Not part of `check` (it needs arguments): CI runs it on module branches.
#   make check-isolation BASE=origin/main MODULE=sbis
check-isolation:
	$(UV) run python scripts/check_module_isolation.py $(BASE) --module $(MODULE)

check: sync lint typecheck test check-size check-core-clean
