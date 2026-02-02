"""Rule: clean up S3 backend configuration for OpenTofu.

Changes:
  - Remove `skip_s3_checksum` (no-op in OpenTofu, causes warnings)
  - Remove `skip_metadata_api_check` (deprecated alias)
  - Add `# TOFUFY: OpenTofu 1.10+ supports use_lockfile = true (native S3 locking,
    no DynamoDB required)` hint when dynamodb_table is present
  - Add `# TOFUFY: OpenTofu 1.8+ supports variable references in backend blocks`
    hint when hardcoded values look like they could be parameterized
"""

from __future__ import annotations

import re
from pathlib import Path

from tofufy.converter.rules.base import Rule

_S3_BACKEND_BLOCK_RE = re.compile(
    r"""
    backend\s+"s3"\s*\{   # backend "s3" {
    (.*?)                  # body (group 1)
    ^([ \t]*)\}            # closing } (group 2 = indent)
    """,
    re.MULTILINE | re.VERBOSE | re.DOTALL,
)

_SKIP_CHECKSUM_RE = re.compile(r"^[ \t]*skip_s3_checksum\s*=\s*\S+[ \t]*\n", re.MULTILINE)
_SKIP_METADATA_RE = re.compile(r"^[ \t]*skip_metadata_api_check\s*=\s*\S+[ \t]*\n", re.MULTILINE)
_DYNAMODB_RE = re.compile(r"dynamodb_table\s*=")
_USE_LOCKFILE_RE = re.compile(r"use_lockfile\s*=")

_LOCKFILE_HINT = (
    "  # TOFUFY: OpenTofu 1.10+ supports native S3 locking - consider:\n"
    "  #   use_lockfile = true  (replaces dynamodb_table)\n"
)
_VAR_INTERPOLATION_HINT = (
    "  # TOFUFY: OpenTofu 1.8+ allows variable/local references in backend blocks.\n"
)


def _patch_s3_block(m: re.Match) -> str:  # type: ignore[type-arg]
    body = m.group(1)
    closing_indent = m.group(2)
    full = m.group(0)

    body = _SKIP_CHECKSUM_RE.sub("", body)
    body = _SKIP_METADATA_RE.sub("", body)

    # Suggest lockfile if DynamoDB is configured and lockfile not already set
    if _DYNAMODB_RE.search(body) and not _USE_LOCKFILE_RE.search(body):
        body = body.rstrip("\n") + "\n" + _LOCKFILE_HINT

    return full[: m.start(1) - m.start()] + body + closing_indent + "}"


class BackendS3Rule(Rule):
    name = "backend-s3-cleanup"

    def apply(self, content: str, path: Path) -> str:
        if 'backend "s3"' not in content:
            return content

        # Remove deprecated attributes
        content = _SKIP_CHECKSUM_RE.sub("", content)
        content = _SKIP_METADATA_RE.sub("", content)

        # Add lockfile hint near dynamodb_table if not already hinted
        if _DYNAMODB_RE.search(content) and "use_lockfile" not in content:
            content = _DYNAMODB_RE.sub(
                _LOCKFILE_HINT.lstrip() + "  dynamodb_table =",
                content,
                count=1,
            )

        return content
