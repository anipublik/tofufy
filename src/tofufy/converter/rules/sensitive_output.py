"""Rule: flag output blocks that expose potentially sensitive values without
marking them as sensitive = true.

Heuristics: output names or resource references containing common sensitive
keywords (password, secret, token, key, cert, private) that lack `sensitive = true`.

This rule is advisory only - it adds a comment, never modifies values.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from tofufy.converter.rules.base import Rule

if TYPE_CHECKING:
    from pathlib import Path

_SENSITIVE_KEYWORDS = re.compile(
    r"\b(password|secret|token|api_key|private_key|cert|credential|auth)\b",
    re.IGNORECASE,
)

# Match output blocks
_OUTPUT_BLOCK_RE = re.compile(
    r"""
    ^([ \t]*)output\s+"([^"]+)"\s*\{   # output "name" {
    (.*?)                                # body
    ^([ \t]*)\}                         # closing }
    """,
    re.MULTILINE | re.VERBOSE | re.DOTALL,
)

_SENSITIVE_FLAG_RE = re.compile(r"\bsensitive\s*=\s*true\b")

_COMMENT = (
    "# TOFUFY: This output may expose sensitive data. "
    "Consider adding: sensitive = true\n"
)


def _check_output(m: re.Match[str]) -> str:
    indent = m.group(1)
    name = m.group(2)
    body = m.group(3)

    looks_sensitive = _SENSITIVE_KEYWORDS.search(name) or _SENSITIVE_KEYWORDS.search(body)
    already_marked = _SENSITIVE_FLAG_RE.search(body)

    if not looks_sensitive or already_marked:
        return m.group(0)

    comment = indent + _COMMENT
    return comment + m.group(0)


class SensitiveOutputRule(Rule):
    name = "sensitive-output"

    def apply(self, content: str, path: Path) -> str:
        if "output" not in content:
            return content

        if "TOFUFY: This output" in content:
            return content  # already annotated

        return _OUTPUT_BLOCK_RE.sub(_check_output, content)
