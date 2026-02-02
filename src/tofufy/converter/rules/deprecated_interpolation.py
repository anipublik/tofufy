"""Rule: simplify unnecessary string interpolation wrappers.

"${expr}"   ->  expr    (when the entire string value is a single interpolation)

Only fires when:
  - The attribute value is exactly "${...}" with no surrounding text
  - The inner expression is a simple reference (var., local., module., data.,
    resource name, path., terraform.)
  - The attribute is an assignment (not inside a dynamic block condition, etc.)

Does NOT change mixed strings like "prefix-${var.foo}" or "${a}-${b}".
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from tofufy.converter.rules.base import Rule

if TYPE_CHECKING:
    from pathlib import Path

# Matches:  = "${<expr>}"  where <expr> has no nested interpolations
# Capture group 1: leading whitespace + key + operator
# Capture group 2: the inner expression
_SOLO_INTERP_RE = re.compile(
    r"""
    (                         # group 1: everything before the value
        ^[ \t]*               #   leading indent
        [\w\-]+               #   attribute name (may include hyphens)
        [ \t]*=[ \t]*         #   = with optional spaces
    )
    "                         # opening quote
    \$\{                      # ${
    (                         # group 2: the expression inside
        (?:
            var\.|local\.|module\.|data\.|path\.|terraform\.
        )
        [A-Za-z0-9_.\[\]"'-]+ # the reference chain
    )
    \}                        # }
    "                         # closing quote
    """,
    re.MULTILINE | re.VERBOSE,
)


def _replace(m: re.Match[str]) -> str:
    return m.group(1) + m.group(2)


class DeprecatedInterpolationRule(Rule):
    name = "deprecated-interpolation"

    def apply(self, content: str, path: Path) -> str:
        return _SOLO_INTERP_RE.sub(_replace, content)
