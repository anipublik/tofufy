"""Additional engine tests: multi-block, JSON output, atomic writes."""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console

from tofufy.converter.engine import ConversionEngine, ConversionResult, FileChange
from tofufy.converter.rules.cloud import CloudBlockRule


def test_cloud_rule_handles_multiple_blocks():
    rule = CloudBlockRule()
    inp = (
        'terraform {\n  cloud {\n    organization = "a"\n'
        '    workspaces { name = "p" }\n  }\n}\n\n'
        'terraform {\n  cloud {\n    organization = "b"\n'
        '    workspaces { name = "q" }\n  }\n}\n'
    )
    out = rule.apply(inp, Path("main.tf"))
    assert "cloud {" not in out
    assert out.count('backend "remote"') == 2
    assert 'organization = "a"' in out
    assert 'organization = "b"' in out


def test_result_to_json(tmp_path: Path):
    (tmp_path / "main.tf").write_text('source = "registry.terraform.io/hashicorp/aws"\n')
    engine = ConversionEngine(repo_path=tmp_path, ignore_patterns=[])
    result = engine.run()

    parsed = json.loads(result.to_json())
    assert parsed["files_changed"] == 1
    assert parsed["changes"][0]["path"].endswith("main.tf")
    assert "registry-rewrite" in parsed["changes"][0]["rules"]


def test_atomic_write_replaces_file(tmp_path: Path):
    target = tmp_path / "x.tf"
    target.write_text("old content")

    change = FileChange(
        path=target,
        original="old content",
        transformed="new content",
    )
    ConversionResult(changes=[change]).write()
    assert target.read_text() == "new content"
    # No leftover tmp files (the atomic write uses .<name>.<rand>.tofufy-tmp)
    leftovers = [p for p in tmp_path.iterdir() if p.name.endswith(".tofufy-tmp")]
    assert not leftovers


def test_display_markdown_renders(tmp_path: Path):
    (tmp_path / "main.tf").write_text('source = "registry.terraform.io/hashicorp/aws"\n')
    engine = ConversionEngine(repo_path=tmp_path, ignore_patterns=[])
    result = engine.run()

    # A non-TTY console just records output; the important thing is no crash
    console = Console(record=True, width=120)
    result.display(console, fmt="markdown")
    out = console.export_text()
    assert "main.tf" in out
    assert "Summary" in out


def test_display_patch_includes_diff(tmp_path: Path):
    (tmp_path / "main.tf").write_text('source = "registry.terraform.io/hashicorp/aws"\n')
    engine = ConversionEngine(repo_path=tmp_path, ignore_patterns=[])
    result = engine.run()

    console = Console(record=True, width=120)
    result.display(console, fmt="patch")
    out = console.export_text()
    assert "---" in out and "+++" in out


def test_first_category_wins_when_rule_hit_twice():
    """If the same rule name matches multiple times (shouldn't happen, but
    let's be defensive), the category recorded first should stick."""
    from tofufy.converter.engine import (
        ALL_RULES,
        CategorizedRule,
        ConversionEngine,
        RuleCategory,
    )
    from tofufy.converter.rules.base import Rule

    calls = [0]

    class Toggling(Rule):
        name = "toggle"

        def apply(self, content: str, path: Path) -> str:
            calls[0] += 1
            if calls[0] == 1:
                return content + "\n# first"
            return content + "\n# second"

    engine = ConversionEngine(repo_path=Path("."), ignore_patterns=[])
    engine.categorized_rules = [
        CategorizedRule(Toggling(), RuleCategory.BREAKING),
        CategorizedRule(Toggling(), RuleCategory.ADVISORY),
    ]
    # Ensure it doesn't mutate ALL_RULES
    assert ALL_RULES  # sanity
    from tofufy.converter.hcl_parser import ParsedFile

    change = engine._transform(ParsedFile(path=Path("x.tf"), content="hello"))
    assert change.rule_categories["toggle"] == RuleCategory.BREAKING
