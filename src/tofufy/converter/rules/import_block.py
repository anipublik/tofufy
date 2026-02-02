"""Rule: flag import blocks that use variable interpolation in their id attribute.

OpenTofu does not support variable or local references inside import block `id`
values (unlike Terraform 1.5+). These must be hardcoded or moved to the CLI
command `tofu import`.

This rule adds a TOFUFY warning comment above affected import blocks.
"""

from __future__ import annotations

import re
from pathlib import Path

from tofufy.converter.rules.base import Rule

# Find import { ... } blocks where id contains ${ ... }
# The body may contain } inside quoted strings (e.g. "${var.env}"), so we
# match either a quoted string (greedy, allowing any char) or any non-} char.
_IMPORT_BLOCK_RE = re.compile(
    r"""
    ^([ \t]*)                     # indent (group 1)
    import\s*\{                   # import {
    (                             # body (group 2)
        (?:
            "(?:[^"\\]|\\.)*"     #   quoted string (any chars including })
            |[^}]                 #   or any non-} character
        )*?
    )
    \}
    """,
    re.MULTILINE | re.VERBOSE | re.DOTALL,
)

_ID_WITH_INTERP_RE = re.compile(r'\bid\s*=\s*"[^"]*\$\{[^}]+\}[^"]*"')

_WARNING = (
    "# TOFUFY WARNING: OpenTofu does not support variable/local interpolation\n"
    "# in import block `id` values. Replace with a hardcoded string or use:\n"
    "#   tofu import <resource_address> <id>\n"
)


def _check_and_annotate(m: re.Match) -> str:  # type: ignore[type-arg]
    indent = m.group(1)
    body = m.group(2)

    if not _ID_WITH_INTERP_RE.search(body):
        return m.group(0)

    warning = "\n".join(indent + line for line in _WARNING.splitlines()) + "\n"
    return warning + m.group(0)


class ImportBlockRule(Rule):
    name = "import-block-interpolation"

    def apply(self, content: str, path: Path) -> str:
        if "import {" not in content and "import{" not in content:
            return content

        return _IMPORT_BLOCK_RE.sub(_check_and_annotate, content)
