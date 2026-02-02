"""Rule: structural mapping of Sentinel policy files to OPA .rego equivalents."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from tofufy.converter.rules.base import Rule

if TYPE_CHECKING:
    from pathlib import Path

# Sentinel structural patterns -> OPA Rego equivalents
_REPLACEMENTS: list[tuple[re.Pattern, str]] = [  # type: ignore[type-arg]
    # import "tfplan" -> import future.keywords; import input as tfplan
    (
        re.compile(r'^import\s+"tfplan(?:/v2)?"', re.MULTILINE),
        'import future.keywords\nimport input as tfplan',
    ),
    # import "tfconfig" -> import input as tfconfig
    (
        re.compile(r'^import\s+"tfconfig(?:/v2)?"', re.MULTILINE),
        'import future.keywords\nimport input as tfconfig',
    ),
    # main = rule { ... }  ->  default allow = false\nallow { ... }
    (
        re.compile(r"^main\s*=\s*rule\s*\{", re.MULTILINE),
        "default allow := false\nallow {",
    ),
    # Sentinel 'all' -> OPA 'every' (basic structural)
    (re.compile(r"\ball\b\s+(\w+)\s+in\s+(\w+)\s+\{"), r"every \1 in \2 {"),
    # Sentinel 'any' -> OPA 'some'
    (re.compile(r"\bany\b\s+(\w+)\s+in\s+(\w+)\s+\{"), r"some \1 in \2; {"),
    # Boolean literals
    (re.compile(r"\btrue\b"), "true"),
    (re.compile(r"\bfalse\b"), "false"),
]

_SENTINEL_EXTENSIONS = {".sentinel", ".hcl"}  # sentinel policies are .sentinel files


class SentinelToOpaRule(Rule):
    name = "sentinel-to-opa"

    def apply(self, content: str, path: Path) -> str:
        if path.suffix not in _SENTINEL_EXTENSIONS:
            return content
        if "sentinel" not in path.name.lower() and path.suffix != ".sentinel":
            return content

        result = content
        for pattern, replacement in _REPLACEMENTS:
            result = pattern.sub(replacement, result)

        # Add Rego package header if not present
        if not result.lstrip().startswith("package"):
            pkg_name = re.sub(r"[^a-z0-9_]", "_", path.stem.lower())
            result = f"package {pkg_name}\n\n" + result

        return result
