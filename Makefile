.PHONY: install lint typecheck test audit build clean

install:
	uv pip install -e ".[dev]"

lint:
	ruff check src tests

typecheck:
	mypy src/tofufy

test:
	pytest

audit:
	pip-audit

ci: lint typecheck test audit

build:
	hatch build

binary:
	pyinstaller --onefile --name tofufy --collect-all tofufy src/tofufy/cli/root.py

clean:
	rm -rf dist/ build/ *.egg-info .coverage coverage.xml .mypy_cache __pycache__
