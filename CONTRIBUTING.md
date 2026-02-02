# Contributing to tofufy

Thanks for your interest. tofufy is MPL-2.0 licensed. Contributions of all kinds are welcome.

## Setup

```bash
git clone https://github.com/anipublik/tofufy
cd tofufy
uv pip install -e ".[dev]"
```

## Running the test suite

```bash
make test        # pytest
make lint        # ruff
make typecheck   # mypy
make ci          # all of the above + pip-audit
```

## Adding a new rule

1. Create `src/tofufy/converter/rules/your_rule.py` inheriting from `Rule`.
2. Implement `name` (str) and `apply(content, path) -> str`.
3. Register it in `src/tofufy/converter/engine.py` → `ALL_RULES`.
4. Add table-driven tests in `tests/unit/test_rules.py`.

## Adding a TACOS platform

Add a template entry in `src/tofufy/tacos/generator.py` → `_TEMPLATES`, then add the platform name to `PLATFORMS` in `src/tofufy/cli/tacos.py`.

## Pull Requests

- Keep PRs focused. One feature or fix per PR.
- All CI checks must pass.
- Cover new code with tests.
- Do not add telemetry, analytics, or network calls beyond what is documented.
