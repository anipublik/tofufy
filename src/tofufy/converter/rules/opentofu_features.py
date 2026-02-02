"""Rule: enable OpenTofu-native feature flags and syntax updates."""

from __future__ import annotations

import re
from pathlib import Path

from tofufy.converter.rules.base import Rule

# OpenTofu supports provider-defined functions - no terraform.functions{} shim needed.
# Matches comment-delimited workaround blocks: # provider-defined functions workaround ... # end workaround
_PROVIDER_FUNCTIONS_SHIM_RE = re.compile(
    r"[#]\s*provider-defined\s+functions\s+workaround[^\n]*\n(?:.*\n)*?[#]\s*end\s+workaround[^\n]*\n?"
)

# TF 1.5+ `import` block is supported natively in OpenTofu - remove any
# experimental feature flag that enabled it in earlier TF versions.
_EXPERIMENTAL_IMPORT_RE = re.compile(
    r"experiments\s*=\s*\[\s*[^\]]*?\bmodule_variable_optional_attrs\b[^\]]*?\]"
)

# Required_providers terraform source -> opentofu source hint comment
_TF_REQUIRED_VERSION_RE = re.compile(
    r'(required_version\s*=\s*")(~>|>=)\s*([\d.]+)(")',
)


def _bump_required_version(m: re.Match) -> str:  # type: ignore[type-arg]
    """Ensure required_version allows OpenTofu 1.x (>= 1.6)."""
    prefix, op, ver, suffix = m.groups()
    parts = ver.split(".")
    major = int(parts[0]) if parts else 1
    if major < 1 or (major == 1 and len(parts) > 1 and int(parts[1]) < 6):
        return f'{prefix}>= 1.6{suffix}'
    return m.group(0)


class OpenTofuFeaturesRule(Rule):
    name = "opentofu-features"

    def apply(self, content: str, path: Path) -> str:
        content = _PROVIDER_FUNCTIONS_SHIM_RE.sub("", content)
        content = _EXPERIMENTAL_IMPORT_RE.sub("", content)
        content = _TF_REQUIRED_VERSION_RE.sub(_bump_required_version, content)
        return content
