REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
WORKSPACE_ROOT := $(abspath $(REPO_ROOT)/..)
VENV := $(REPO_ROOT)/.venv
DEV_STAMP := $(VENV)/.baseline-tools-installed
PYTHON := $(VENV)/bin/python3.11
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
RUFF := $(PYTHON) -m ruff

.PHONY: help venv dev-install fix format format-check lint test test-all release-check check clean

help:
	@printf '%s\n' \
		'Targets:' \
		'  make dev-install   Create/update .venv and install openminion-eval with dev extras' \
		'  make fix           Apply Ruff formatting and autofixes' \
		'  make format        Run Ruff formatter' \
		'  make format-check  Check formatting without changing files' \
		'  make lint          Run Ruff lint' \
		'  make test          Run standalone public package pytest suite' \
		'  make test-all      Run all repo-local tests, including OpenMinion integration tests' \
		'  make release-check Build sdist/wheel and smoke-test the installed wheel' \
		'  make check         Run format-check, lint, and test' \
		'  make clean         Remove repo-local cache/build artifacts'

venv:
	@test -x "$(PYTHON)" || python3.11 -m venv "$(VENV)"

$(DEV_STAMP): pyproject.toml | venv
	$(PIP) install --upgrade pip setuptools wheel
	cd "$(REPO_ROOT)" && $(PIP) install -e ".[dev]"
	@touch "$(DEV_STAMP)"

dev-install: $(DEV_STAMP)

fix: $(DEV_STAMP)
	$(RUFF) format "$(REPO_ROOT)"
	$(RUFF) check --fix "$(REPO_ROOT)"

format: $(DEV_STAMP)
	$(RUFF) format "$(REPO_ROOT)"

format-check: $(DEV_STAMP)
	$(RUFF) format --check "$(REPO_ROOT)"

lint: $(DEV_STAMP)
	$(RUFF) check "$(REPO_ROOT)"

test: $(DEV_STAMP)
	@printf '%s\n' \
		'Ignoring tests/eval/integration: live credentials or external runtime state required.' \
		'Ignoring tests/eval/test_eval_adjacent_owner_dispositions.py: enforced by main workspace gates.' \
		'Ignoring tests/eval/test_memory_eval.py: yaml-backed optional fixture suite outside the standalone public slice.' \
		'Ignoring tests/eval/test_trace_flywheel.py: broader integration owner than the standalone public package gate.'
	PYTHONPATH="$(REPO_ROOT)/src" $(PYTEST) -q "$(REPO_ROOT)/tests/eval" \
		--ignore="$(REPO_ROOT)/tests/eval/integration" \
		--ignore="$(REPO_ROOT)/tests/eval/test_eval_adjacent_owner_dispositions.py" \
		--ignore="$(REPO_ROOT)/tests/eval/test_memory_eval.py" \
		--ignore="$(REPO_ROOT)/tests/eval/test_trace_flywheel.py"

test-all: $(DEV_STAMP)
	PYTHONPATH="$(REPO_ROOT)/src:$(WORKSPACE_ROOT)/openminion/src" $(PYTEST) -q "$(REPO_ROOT)/tests"

release-check: $(DEV_STAMP)
	$(PYTHON) "$(REPO_ROOT)/scripts/check_release_package.py"

check: format-check lint test

clean:
	find "$(REPO_ROOT)" \
		-path "$(VENV)" -prune -o \
		\( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache -o -name build -o -name dist -o -name '*.egg-info' \) \
		-prune -exec rm -rf {} +
