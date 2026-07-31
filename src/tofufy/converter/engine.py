"""Conversion engine - orchestrates rules over a repo."""

from __future__ import annotations

import contextlib
import difflib
import json
import os
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path as _Path
from typing import TYPE_CHECKING, Any

from rich.syntax import Syntax

from tofufy.converter.hcl_parser import ParsedFile, find_tf_files, parse_file
from tofufy.converter.rules.backend_s3 import BackendS3Rule
from tofufy.converter.rules.cdktf_json import CdktfJsonRule
from tofufy.converter.rules.cloud import CloudBlockRule
from tofufy.converter.rules.deprecated_functions import DeprecatedFunctionsRule
from tofufy.converter.rules.deprecated_interpolation import DeprecatedInterpolationRule
from tofufy.converter.rules.import_block import ImportBlockRule
from tofufy.converter.rules.null_resource import NullResourceRule
from tofufy.converter.rules.opentofu_features import OpenTofuFeaturesRule
from tofufy.converter.rules.provider_version import ProviderVersionRule
from tofufy.converter.rules.registry import RegistryRewriteRule
from tofufy.converter.rules.removed_block import RemovedBlockRule
from tofufy.converter.rules.sensitive_output import SensitiveOutputRule
from tofufy.converter.rules.sentinel_to_opa import SentinelToOpaRule
from tofufy.converter.rules.terragrunt import TerragruntRule
from tofufy.converter.rules.tfe_resources import TFEResourcesRule
from tofufy.converter.rules.workspace_vars import WorkspaceVarsRule

if TYPE_CHECKING:
    from pathlib import Path

    from rich.console import Console

    from tofufy.converter.rules.base import Rule


class RuleCategory(str, Enum):
    """Rule execution priority tier."""

    BREAKING = "breaking"  # Will break if not applied
    IMPORTANT = "important"  # Behavioral differences / deprecation warnings
    ADVISORY = "advisory"  # Comments and hints only; no code changes


# Human-readable one-liners for each rule, used by `tofufy rules`
# and the PR-body summary.
RULE_DESCRIPTIONS: dict[str, str] = {
    "cloud-block-to-backend": 'Rewrite cloud{} to backend "remote" {}',
    "cdktf-json-terraform-block": "Convert CDKTF .tf.json for OpenTofu (version, cloud block)",
    "registry-rewrite": "Swap registry.terraform.io → registry.opentofu.org",
    "null-resource-to-terraform-data": "Migrate null_resource → terraform_data",
    "opentofu-features": "Bump required_version and enable OpenTofu features",
    "removed-block-lifecycle": "Hoist destroy out of lifecycle{} in removed{}",
    "deprecated-interpolation": 'Simplify "${expr}" wrappers',
    "deprecated-functions": "Replace list()/map()/*_tfvars with modern syntax",
    "terragrunt-binary": 'Set terraform_binary = "tofu" in terragrunt.hcl',
    "backend-s3-cleanup": "Clean legacy S3 backend flags; hint use_lockfile",
    "sentinel-to-opa": "Scaffold Sentinel → OPA Rego mapping",
    "tfe-resource-annotation": "Flag tfe_* resources for review",
    "import-block-interpolation": "Warn on interpolated import{} ids",
    "provider-version-pin": "Flag exact-version provider pins",
    "workspace-name-annotation": "Annotate terraform.workspace usage",
    "sensitive-output": "Flag outputs that look sensitive but aren't marked",
}


@dataclass
class CategorizedRule:
    rule: Rule
    category: RuleCategory


# Rules are applied in order. Breaking rules run first so later rules see
# already-transformed content.
ALL_RULES: list[CategorizedRule] = [
    # --- BREAKING: must fix for OpenTofu to work ---
    CategorizedRule(CloudBlockRule(), RuleCategory.BREAKING),
    CategorizedRule(CdktfJsonRule(), RuleCategory.BREAKING),
    CategorizedRule(RegistryRewriteRule(), RuleCategory.BREAKING),
    CategorizedRule(NullResourceRule(), RuleCategory.BREAKING),
    CategorizedRule(OpenTofuFeaturesRule(), RuleCategory.BREAKING),
    CategorizedRule(RemovedBlockRule(), RuleCategory.BREAKING),
    # --- IMPORTANT: deprecated constructs that should be updated ---
    CategorizedRule(DeprecatedInterpolationRule(), RuleCategory.IMPORTANT),
    CategorizedRule(DeprecatedFunctionsRule(), RuleCategory.IMPORTANT),
    CategorizedRule(TerragruntRule(), RuleCategory.IMPORTANT),
    CategorizedRule(BackendS3Rule(), RuleCategory.IMPORTANT),
    # --- ADVISORY: annotations and hints for manual review ---
    CategorizedRule(SentinelToOpaRule(), RuleCategory.ADVISORY),
    CategorizedRule(TFEResourcesRule(), RuleCategory.ADVISORY),
    CategorizedRule(ImportBlockRule(), RuleCategory.ADVISORY),
    CategorizedRule(ProviderVersionRule(), RuleCategory.ADVISORY),
    CategorizedRule(WorkspaceVarsRule(), RuleCategory.ADVISORY),
    CategorizedRule(SensitiveOutputRule(), RuleCategory.ADVISORY),
]


@dataclass
class FileChange:
    path: Path
    original: str
    transformed: str
    rule_hits: list[str] = field(default_factory=list)
    rule_categories: dict[str, RuleCategory] = field(default_factory=dict)

    @property
    def changed(self) -> bool:
        return self.original != self.transformed

    @property
    def breaking_changes(self) -> list[str]:
        return [r for r in self.rule_hits if self.rule_categories.get(r) == RuleCategory.BREAKING]

    @property
    def important_changes(self) -> list[str]:
        return [r for r in self.rule_hits if self.rule_categories.get(r) == RuleCategory.IMPORTANT]

    @property
    def advisory_changes(self) -> list[str]:
        return [r for r in self.rule_hits if self.rule_categories.get(r) == RuleCategory.ADVISORY]

    def diff(self) -> str:
        return "".join(
            difflib.unified_diff(
                self.original.splitlines(keepends=True),
                self.transformed.splitlines(keepends=True),
                fromfile=f"a/{self.path}",
                tofile=f"b/{self.path}",
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "changed": self.changed,
            "rules": self.rule_hits,
            "breaking": self.breaking_changes,
            "important": self.important_changes,
            "advisory": self.advisory_changes,
        }


@dataclass
class ConversionResult:
    changes: list[FileChange] = field(default_factory=list)

    @property
    def files_changed(self) -> int:
        return sum(1 for c in self.changes if c.changed)

    @property
    def breaking_count(self) -> int:
        return sum(1 for c in self.changes if c.changed and c.breaking_changes)

    @property
    def important_count(self) -> int:
        return sum(1 for c in self.changes if c.changed and c.important_changes)

    @property
    def advisory_count(self) -> int:
        return sum(1 for c in self.changes if c.changed and c.advisory_changes)

    def display(self, console: Console, fmt: str = "markdown", dry_run: bool = False) -> None:
        if fmt == "json":
            console.print_json(self.to_json())
            return
        if fmt == "patch":
            self._display_patch(console, dry_run)
            return
        # markdown / html / default
        self._display_summary(console, dry_run, show_diff=False)

    def _display_patch(self, console: Console, dry_run: bool) -> None:
        label = "[dim](dry-run)[/dim] " if dry_run else ""
        for change in self.changes:
            if not change.changed:
                continue
            console.print(f"\n{label}[bold cyan]{change.path}[/bold cyan]")
            console.print(Syntax(change.diff(), "diff", theme="monokai"))
        self._print_summary_line(console)

    def _display_summary(self, console: Console, dry_run: bool, show_diff: bool) -> None:
        label = "[dim](dry-run)[/dim] " if dry_run else ""
        for change in self.changes:
            if not change.changed:
                continue

            console.print(f"\n{label}[bold cyan]{change.path}[/bold cyan]")
            if change.breaking_changes:
                console.print(
                    f"  [bold red]breaking:[/bold red] {', '.join(change.breaking_changes)}"
                )
            if change.important_changes:
                console.print(
                    f"  [yellow]important:[/yellow] {', '.join(change.important_changes)}"
                )
            if change.advisory_changes:
                console.print(f"  [dim]advisory:[/dim] {', '.join(change.advisory_changes)}")
            if show_diff:
                console.print(Syntax(change.diff(), "diff", theme="monokai"))

        self._print_summary_line(console)

    def _print_summary_line(self, console: Console) -> None:
        console.print(
            f"\n[bold]Summary:[/bold] {self.files_changed} file(s) changed "
            f"([red]{self.breaking_count} breaking[/red], "
            f"[yellow]{self.important_count} important[/yellow], "
            f"[dim]{self.advisory_count} advisory[/dim])."
        )

    def print_checklist(self, console: Console, dry_run: bool = False) -> None:
        """Print the next-steps checklist after a conversion."""
        if dry_run:
            console.print(
                "\n[dim]Dry run - no files written. Re-run without --dry-run to apply.[/dim]"
            )
            return

        has_tfe = any("tfe-resource-annotation" in c.rule_hits for c in self.changes if c.changed)
        has_workspace = any(
            "workspace-name-annotation" in c.rule_hits for c in self.changes if c.changed
        )
        has_cdktf = any(c.path.name.endswith(".tf.json") for c in self.changes if c.changed)

        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. [cyan]tofu init -upgrade[/cyan]")
        console.print(
            "  2. [cyan]tofu providers lock "
            "-platform=linux_amd64 -platform=darwin_arm64 -platform=windows_amd64[/cyan]"
        )
        console.print("  3. [cyan]tofu plan[/cyan]  (run against your existing TFE backend)")
        console.print(
            "  4. [cyan]tofufy state migrate --org <org> --token "
            "$TFE_TOKEN --target-backend s3[/cyan]"
        )
        if has_tfe:
            console.print(
                "\n  [yellow]tfe_* resources found - "
                "review TOFUFY annotations before applying.[/yellow]"
            )
        if has_workspace:
            console.print(
                "\n  [yellow]terraform.workspace used - "
                "verify workspace names after migration.[/yellow]"
            )
        if has_cdktf:
            console.print(
                "\n  [yellow]CDKTF synthesized files converted - "
                "`cdktf synth` will overwrite cdktf.out; commit the converted "
                "output or migrate stacks off CDKTF.[/yellow]"
            )

    def write(self) -> None:
        """Atomically write all changed files to disk.

        Each file is written to a sibling temp file and renamed in place,
        which avoids leaving a half-written .tf file behind if the process
        is killed mid-write.
        """
        for change in self.changes:
            if not change.changed:
                continue
            _atomic_write(change.path, change.transformed)

    def as_patch(self) -> str:
        return "\n".join(c.diff() for c in self.changes if c.changed)

    def to_json(self) -> str:
        return json.dumps(
            {
                "files_changed": self.files_changed,
                "breaking": self.breaking_count,
                "important": self.important_count,
                "advisory": self.advisory_count,
                "changes": [c.to_dict() for c in self.changes if c.changed],
            },
            indent=2,
        )


def _atomic_write(path: Path, content: str) -> None:
    """Write content to path via a tmp file + rename within the same directory."""
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tofufy-tmp", dir=parent)
    tmp_path = _Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        tmp_path.replace(path)
    except BaseException:
        # Best-effort cleanup; leave path untouched on failure.
        with contextlib.suppress(FileNotFoundError):
            tmp_path.unlink()
        raise


class ConversionEngine:
    def __init__(
        self,
        repo_path: Path,
        ignore_patterns: list[str],
        ai_enabled: bool = False,
        llm_provider: str | None = None,
        api_key: str | None = None,
        verbose: bool = False,
        config: Any = None,
        categories: list[RuleCategory] | None = None,
    ) -> None:
        self.repo_path = repo_path
        self.ignore_patterns = ignore_patterns
        self.ai_enabled = ai_enabled
        self.llm_provider = llm_provider
        self.api_key = api_key
        self.verbose = verbose
        self.config = config

        # Filter rules by category if requested (e.g., breaking-only mode)
        if categories:
            self.categorized_rules = [r for r in ALL_RULES if r.category in categories]
        else:
            self.categorized_rules = ALL_RULES

    def run(self) -> ConversionResult:
        tf_files = find_tf_files(self.repo_path, self.ignore_patterns)
        result = ConversionResult()

        for path in tf_files:
            parsed = parse_file(path)
            change = self._transform(parsed)
            result.changes.append(change)

        if self.ai_enabled and self.api_key:
            result = self._ai_pass(result)

        return result

    def _transform(self, parsed: ParsedFile) -> FileChange:
        content = parsed.content
        hits: list[str] = []
        hit_categories: dict[str, RuleCategory] = {}

        for cr in self.categorized_rules:
            # HCL-syntax rules would corrupt JSON-syntax config; only rules
            # that explicitly support JSON may run on .tf.json files.
            if parsed.is_json and not cr.rule.supports_json:
                continue
            new_content = cr.rule.apply(content, parsed.path)
            if new_content != content:
                if cr.rule.name not in hit_categories:
                    # First hit wins: a rule can only belong to one category, so
                    # re-hitting the same rule should not clobber the record.
                    hits.append(cr.rule.name)
                    hit_categories[cr.rule.name] = cr.category
                content = new_content

        return FileChange(
            path=parsed.path,
            original=parsed.content,
            transformed=content,
            rule_hits=hits,
            rule_categories=hit_categories,
        )

    def _ai_pass(self, result: ConversionResult) -> ConversionResult:
        from tofufy.ai.assistant import AIAssistant

        assistant = AIAssistant(provider=self.llm_provider or "anthropic", api_key=self.api_key)
        return assistant.refine(result)
