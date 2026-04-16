"""Tests for git URL parsing and PR body formatting (pure helpers, no network)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from tofufy.git.clone import resolve_source
from tofufy.git.pr import (
    PRCreator,
    _build_pr_body,
    _parse_bitbucket_slug,
    _parse_github_slug,
    _parse_gitlab_slug,
)


class TestParseSlugs:
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("https://github.com/acme/repo.git", "acme/repo"),
            ("https://github.com/acme/repo", "acme/repo"),
            ("git@github.com:acme/repo.git", "acme/repo"),
        ],
    )
    def test_github(self, url: str, expected: str):
        assert _parse_github_slug(url) == expected

    def test_github_invalid(self):
        with pytest.raises(ValueError, match="GitHub"):
            _parse_github_slug("https://example.com/foo/bar")

    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("https://gitlab.com/acme/repo.git", "acme/repo"),
            ("git@gitlab.com:group/sub/repo.git", "group/sub/repo"),
        ],
    )
    def test_gitlab(self, url: str, expected: str):
        assert _parse_gitlab_slug(url) == expected

    def test_bitbucket(self):
        assert _parse_bitbucket_slug("https://bitbucket.org/ws/repo.git") == ("ws", "repo")


@dataclass
class _FakeChange:
    path: str
    rule_hits: list[str]
    breaking_changes: list[str] = field(default_factory=list)
    important_changes: list[str] = field(default_factory=list)
    advisory_changes: list[str] = field(default_factory=list)
    changed: bool = True


@dataclass
class _FakeResult:
    changes: list[_FakeChange]


def test_pr_body_contains_sections_for_categories():
    result = _FakeResult(
        changes=[
            _FakeChange(
                path="main.tf",
                rule_hits=["cloud-block-to-backend"],
                breaking_changes=["cloud-block-to-backend"],
            ),
            _FakeChange(
                path="vars.tf",
                rule_hits=["deprecated-interpolation"],
                important_changes=["deprecated-interpolation"],
            ),
        ]
    )
    body = _build_pr_body(result)
    assert "Breaking changes" in body
    assert "Important updates" in body
    assert "main.tf" in body
    assert "vars.tf" in body
    assert "cloud-block-to-backend" in body
    assert "tofufy" in body  # credit line


def test_pr_body_empty_result():
    body = _build_pr_body(None)
    assert "tofufy" in body


def test_pr_body_no_changes():
    body = _build_pr_body(_FakeResult(changes=[_FakeChange("a", [], changed=False)]))
    assert "No files changed" in body


def test_pr_creator_rejects_unknown_platform(tmp_path: Path):
    with pytest.raises(ValueError, match="Unsupported"):
        PRCreator(platform="svn", token="x", repo_path=tmp_path)


def test_resolve_source_local_path(tmp_path: Path):
    assert resolve_source(str(tmp_path)) == tmp_path


def test_resolve_source_missing():
    with pytest.raises(FileNotFoundError):
        resolve_source("/definitely/does/not/exist/tofufy-xyz")
