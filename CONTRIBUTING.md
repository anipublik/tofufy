# Contributing to tofufy

Thanks for your interest. tofufy is MPL-2.0 licensed. Contributions of all kinds are welcome.

## Setup

```bash
git clone https://github.com/anipublik/tofufy
cd tofufy
uv pip install -e ".[dev]"
pre-commit install                 # optional but recommended
```

## Running the test suite

```bash
make test        # pytest with coverage
make lint        # ruff check
make format      # ruff format (in-place)
make typecheck   # mypy
make audit       # pip-audit
make ci          # everything CI runs
```

Coverage floor is enforced at 60%. Aim higher for new rules — table-driven tests make it cheap.

## Adding a new conversion rule

1. Create `src/tofufy/converter/rules/your_rule.py` inheriting from `Rule`.
2. Implement `name` (str) and `apply(content, path) -> str`. Return `content` unchanged if the rule doesn't fire.
3. Register it in `src/tofufy/converter/engine.py` → `ALL_RULES` with the right `RuleCategory` (BREAKING / IMPORTANT / ADVISORY).
4. Add a one-line description to `RULE_DESCRIPTIONS` in the same file — it shows up in `tofufy rules`.
5. Add table-driven tests in `tests/unit/test_rules.py` or `tests/unit/test_new_rules.py`.

Rules should be idempotent: running them twice should produce the same output as running them once. `test_idempotent`-style tests are encouraged.

## Adding a TACOS platform

1. Add a template entry in `src/tofufy/tacos/generator.py` → `_TEMPLATES`.
2. Add the platform name to `PLATFORMS` in `src/tofufy/cli/tacos.py`.
3. Add the platform to the parametrized platform test in `tests/unit/test_tacos.py`.

## Pull requests

- Keep PRs focused. One feature or fix per PR.
- All CI checks must pass (lint, format, mypy, pytest, pip-audit).
- Cover new code with tests.
- Do not add telemetry, analytics, or network calls beyond what is documented in `SECURITY.md`.
