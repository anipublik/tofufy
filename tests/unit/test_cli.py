"""CLI smoke tests using Typer's CliRunner."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from tofufy.cli.root import app

runner = CliRunner()


def test_version_cmd_runs():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0, result.output
    assert "tofufy" in result.output
    assert "Python" in result.output


def test_rules_cmd_lists_all():
    result = runner.invoke(app, ["rules"])
    assert result.exit_code == 0, result.output
    assert "cloud-block-to-backend" in result.output
    assert "registry-rewrite" in result.output
    assert "sensitive-output" in result.output


def test_rules_cmd_filters_breaking():
    result = runner.invoke(app, ["rules", "--category", "breaking"])
    assert result.exit_code == 0
    assert "cloud-block-to-backend" in result.output
    # Advisory rules must not appear
    assert "sensitive-output" not in result.output


def test_rules_cmd_rejects_unknown_category():
    result = runner.invoke(app, ["rules", "--category", "potato"])
    assert result.exit_code != 0


def test_convert_dry_run_on_empty_dir(tmp_path: Path):
    result = runner.invoke(app, ["convert", str(tmp_path), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "0 file(s)" in result.output


def test_convert_dry_run_with_changes(tmp_path: Path):
    (tmp_path / "main.tf").write_text('source = "registry.terraform.io/hashicorp/aws"\n')
    result = runner.invoke(app, ["convert", str(tmp_path), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "main.tf" in result.output


def test_convert_dry_run_json_output(tmp_path: Path):
    (tmp_path / "main.tf").write_text('source = "registry.terraform.io/hashicorp/aws"\n')
    result = runner.invoke(
        app,
        ["convert", str(tmp_path), "--dry-run", "--output", "json"],
    )
    assert result.exit_code == 0, result.output
    assert '"files_changed"' in result.output
    assert "registry-rewrite" in result.output


def test_convert_rejects_unknown_output_format(tmp_path: Path):
    result = runner.invoke(app, ["convert", str(tmp_path), "--dry-run", "--output", "yaml"])
    assert result.exit_code != 0


def test_convert_writes_with_yes_flag(tmp_path: Path):
    (tmp_path / "main.tf").write_text('source = "registry.terraform.io/hashicorp/aws"\n')
    result = runner.invoke(app, ["convert", str(tmp_path), "--yes"])
    assert result.exit_code == 0, result.output
    content = (tmp_path / "main.tf").read_text()
    # Exact-match the rewritten line; this is a plain file-content check,
    # not URL validation (avoids false positives from URL-substring lints).
    assert content.strip() == 'source = "registry.opentofu.org/hashicorp/aws"'


def test_convert_nonexistent_path():
    result = runner.invoke(app, ["convert", "/nonexistent/path/xyz", "--dry-run"])
    assert result.exit_code != 0
