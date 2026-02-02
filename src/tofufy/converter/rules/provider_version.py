"""Rule: normalise provider version constraints for OpenTofu compatibility.

OpenTofu publishes providers to registry.opentofu.org under the same versioning
scheme as the Terraform registry. Version constraints themselves don't change,
but two common issues arise:

1. Overly-tight pessimistic constraints using `~>` that lock to a Terraform-only
   minor/patch release:  ~> 4.0  is fine;  ~> 4.67.3  may be overly specific.
   This rule does NOT change version numbers - that requires human judgment -
   but it does annotate constraints using exact-version pins (=) to encourage
   using range constraints.

2. Missing `source` in required_providers - OpenTofu resolves from
   registry.opentofu.org by default, but an explicit source avoids ambiguity.

This rule adds advisory comments only; it never changes version numbers.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from tofufy.converter.rules.base import Rule

if TYPE_CHECKING:
    from pathlib import Path

# Exact-version pin: version = "= 1.2.3" or version = "1.2.3" (no operator)
_EXACT_PIN_RE = re.compile(
    r"""
    (version\s*=\s*"            # version = "
    (?:=\s*)?                   # optional =
    \d+\.\d+\.\d+               # exact semver
    ")                          # closing quote
    """,
    re.VERBOSE,
)

_EXACT_PIN_COMMENT = (
    "# TOFUFY: Exact version pin detected. Consider a range constraint (~> X.Y)\n"
    "# to avoid being blocked on a specific Terraform-era release.\n"
)

# Provider block without a source attribute
_PROVIDER_BLOCK_RE = re.compile(
    r"""
    ^([ \t]*)(\w+)\s*=\s*\{    # name = {
    ([^}]*)                     # body
    \}                          # }
    """,
    re.MULTILINE | re.VERBOSE | re.DOTALL,
)


def _flag_exact_pins(m: re.Match[str]) -> str:
    # Don't double-annotate
    preceding = m.string[max(0, m.start() - 120) : m.start()]
    if "TOFUFY" in preceding:
        return m.group(0)
    return _EXACT_PIN_COMMENT + m.group(0)


class ProviderVersionRule(Rule):
    name = "provider-version-pin"

    def apply(self, content: str, path: Path) -> str:
        if "required_providers" not in content:
            return content

        content = _EXACT_PIN_RE.sub(_flag_exact_pins, content)
        return content
