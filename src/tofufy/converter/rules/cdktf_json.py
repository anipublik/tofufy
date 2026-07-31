"""Rule: convert CDKTF-synthesized .tf.json files for OpenTofu.

CDKTF synthesizes to Terraform JSON config (cdktf.out/stacks/<name>/cdk.tf.json),
which OpenTofu reads natively. This rule works on the parsed document instead of
regexing text, since HCL-oriented rules cannot run on JSON:

- Ensure terraform.required_version allows OpenTofu (>= 1.6). CDKTF omits it.
- Rewrite terraform.cloud to terraform.backend.remote (JSON form of cloud{}) when
  every workspace-selection argument can be represented by the remote backend.
  Tag/project-based selection is left as a cloud block rather than silently
  losing workspace-selection behavior.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from tofufy.converter.rules.base import Rule

if TYPE_CHECKING:
    from pathlib import Path

_MIN_OPENTOFU = (1, 6)
_CONSTRAINT_RE = re.compile(r"^(>=|~>)\s*([\d.]+)$")
_VERSION_RE = re.compile(r"^(?:=\s*)?([\d.]+)$")
_SUPPORTED_WORKSPACE_KEYS = {"name", "prefix"}


def _version_tuple(ver: str) -> tuple[int, int]:
    parts = ver.split(".")
    major = int(parts[0]) if parts and parts[0].isdigit() else 0
    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return major, minor


def _bump_required_version(value: Any) -> str:
    """Ensure OpenTofu 1.6+ is allowed without dropping other constraints.

    Compound constraints such as ">= 1.5, < 2.0" keep their upper bound, and
    constraints that already allow OpenTofu (including exact pins) are untouched.
    """
    if not isinstance(value, str):
        return ">= 1.6"

    conditions = [condition.strip() for condition in value.split(",") if condition.strip()]
    if not conditions:
        return ">= 1.6"
    if any(
        _version_tuple(version) >= _MIN_OPENTOFU for _, version in _parse_conditions(conditions)
    ):
        return value

    updated: list[str] = []
    minimum_bumped = False
    for condition in conditions:
        m = _CONSTRAINT_RE.match(condition)
        if m and not minimum_bumped and _version_tuple(m.group(2)) < _MIN_OPENTOFU:
            updated.append(">= 1.6")
            minimum_bumped = True
        else:
            updated.append(condition)
    if not minimum_bumped:
        updated.append(">= 1.6")
    return ", ".join(updated)


def _parse_conditions(conditions: list[str]) -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    for condition in conditions:
        m = _CONSTRAINT_RE.match(condition)
        if m:
            parsed.append((m.group(1), m.group(2)))
            continue
        if exact := _VERSION_RE.match(condition):
            parsed.append(("=", exact.group(1)))
    return parsed


def _cloud_to_remote_backend(cloud: Any) -> dict[str, Any] | None:
    if not isinstance(cloud, dict):
        return None

    workspaces = cloud.get("workspaces")
    if isinstance(workspaces, dict) and any(k not in _SUPPORTED_WORKSPACE_KEYS for k in workspaces):
        # The remote backend cannot represent project/tag selection. Keep cloud{}
        # intact instead of dropping that behavior or emitting workspaces {}.
        return None
    if workspaces is not None and not isinstance(workspaces, dict):
        return None

    backend: dict[str, Any] = {"hostname": cloud.get("hostname", "app.terraform.io")}
    if org := cloud.get("organization"):
        backend["organization"] = org
    if isinstance(workspaces, dict) and workspaces:
        backend["workspaces"] = dict(workspaces)
    return backend


class CdktfJsonRule(Rule):
    name = "cdktf-json-terraform-block"
    supports_json = True

    def apply(self, content: str, path: Path) -> str:
        try:
            doc = json.loads(content)
        except json.JSONDecodeError:
            return content
        if not isinstance(doc, dict):
            return content

        changed = False
        terraform = doc.get("terraform")
        if not isinstance(terraform, dict):
            terraform = {}
            doc["terraform"] = terraform
            changed = True

        new_version = _bump_required_version(terraform.get("required_version"))
        if terraform.get("required_version") != new_version:
            terraform["required_version"] = new_version
            changed = True

        if "cloud" in terraform:
            remote_backend = _cloud_to_remote_backend(terraform["cloud"])
            if remote_backend is not None:
                backend = terraform.setdefault("backend", {})
                if isinstance(backend, dict):
                    terraform.pop("cloud")
                    backend["remote"] = remote_backend
                    changed = True

        if not changed:
            return content
        return json.dumps(doc, indent=2) + "\n"
