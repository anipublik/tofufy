.PHONY: help install lint format typecheck test test-fast audit ci build binary clean

help:  ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:  ## Install with dev extras
	uv pip install -e ".[dev,all]"

lint:  ## Run ruff check
	ruff check src tests

format:  ## Auto-format code with ruff
	ruff format src tests

typecheck:  ## Run mypy
	mypy src/tofufy

test:  ## Run full test suite with coverage
	pytest

test-fast:  ## Run tests without coverage
	pytest --no-cov -x

audit:  ## Run pip-audit
	pip-audit --strict --skip-editable

ci: lint typecheck test audit  ## Run everything CI runs

build:  ## Build wheel + sdist
	hatch build

binary:  ## Build standalone PyInstaller binary
	pyinstaller --onefile --name tofufy --collect-all tofufy src/tofufy/cli/root.py

clean:  ## Remove build / cache artifacts
	rm -rf dist/ build/ *.egg-info .coverage coverage.xml .mypy_cache .ruff_cache .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
