"""Tests for TACOS generator."""

from __future__ import annotations

from pathlib import Path

import pytest

from tofufy.tacos.generator import TACOSGenerator


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "prod").mkdir()
    (tmp_path / "prod" / "main.tf").write_text("resource {}\n")
    (tmp_path / "staging").mkdir()
    (tmp_path / "staging" / "main.tf").write_text("resource {}\n")
    return tmp_path


@pytest.mark.parametrize("platform", ["atlantis", "spacelift", "env0", "scalr", "digger"])
def test_all_platforms_generate(tmp_path: Path, repo: Path, platform: str):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    gen = TACOSGenerator(platform=platform, repo_path=repo, out_path=out_dir)
    files = gen.generate()
    assert files
    for f in files:
        assert f.exists()
        content = f.read_text()
        # Each workspace we created should appear in output
        assert "prod" in content
        assert "staging" in content


def test_tacos_dry_run_writes_nothing(repo: Path, tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    gen = TACOSGenerator(platform="atlantis", repo_path=repo, out_path=out_dir)
    files = gen.generate(dry_run=True)
    assert files
    for f in files:
        assert not f.exists()


def test_custom_template_dir_overrides(tmp_path: Path, repo: Path):
    tmpl_dir = tmp_path / "tmpl"
    tmpl_dir.mkdir()
    (tmpl_dir / "custom.yml").write_text("hello: world\n")

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    gen = TACOSGenerator(
        platform="atlantis", repo_path=repo, out_path=out_dir, template_dir=tmpl_dir
    )
    files = gen.generate()
    assert len(files) == 1
    assert files[0].name == "custom.yml"
    assert "hello: world" in files[0].read_text()


def test_unknown_platform_generates_nothing(repo: Path, tmp_path: Path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    gen = TACOSGenerator(platform="unknown-platform", repo_path=repo, out_path=out_dir)
    assert gen.generate() == []
