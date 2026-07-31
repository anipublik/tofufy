"""Tests for CDKTF .tf.json conversion."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from tofufy.converter.engine import ConversionEngine
from tofufy.converter.rules.base import Rule
from tofufy.converter.rules.cdktf_json import CdktfJsonRule
from tofufy.converter.rules.registry import RegistryRewriteRule

if TYPE_CHECKING:
    from pathlib import Path


def _apply(doc: dict) -> dict:
    out = CdktfJsonRule().apply(json.dumps(doc), path=None)  # type: ignore[arg-type]
    return json.loads(out)


def test_json_support_is_explicitly_opted_in() -> None:
    assert Rule.supports_json is False
    assert CdktfJsonRule.supports_json is True
    assert RegistryRewriteRule.supports_json is True


def test_adds_required_version_when_missing() -> None:
    doc = {"//": {"metadata": {"stackName": "app"}}, "resource": {}}
    result = _apply(doc)
    assert result["terraform"]["required_version"] == ">= 1.6"
    # cdktf metadata comment block must survive
    assert result["//"]["metadata"]["stackName"] == "app"


def test_bumps_old_required_version() -> None:
    doc = {"terraform": {"required_version": ">= 1.3"}}
    assert _apply(doc)["terraform"]["required_version"] == ">= 1.6"


def test_keeps_adequate_required_version() -> None:
    content = json.dumps({"terraform": {"required_version": ">= 1.8"}}) + "\n"
    assert CdktfJsonRule().apply(content, path=None) == content  # type: ignore[arg-type]


def test_preserves_upper_bound_when_bumping_required_version() -> None:
    doc = {"terraform": {"required_version": ">= 1.5, < 2.0"}}
    assert _apply(doc)["terraform"]["required_version"] == ">= 1.6, < 2.0"


def test_keeps_compatible_compound_constraint() -> None:
    content = json.dumps({"terraform": {"required_version": ">= 1.8, < 2.0"}}) + "\n"
    assert CdktfJsonRule().apply(content, path=None) == content  # type: ignore[arg-type]


def test_keeps_exact_compatible_version() -> None:
    content = json.dumps({"terraform": {"required_version": "= 1.8.2"}}) + "\n"
    assert CdktfJsonRule().apply(content, path=None) == content  # type: ignore[arg-type]


def test_blank_required_version_becomes_minimum() -> None:
    doc = {"terraform": {"required_version": ", ,"}}
    assert _apply(doc)["terraform"]["required_version"] == ">= 1.6"


def test_appends_minimum_to_constraint_without_lower_bound() -> None:
    doc = {"terraform": {"required_version": "< 2.0"}}
    assert _apply(doc)["terraform"]["required_version"] == "< 2.0, >= 1.6"


def test_converts_cloud_block_to_remote_backend() -> None:
    doc = {
        "terraform": {
            "cloud": {
                "hostname": "app.terraform.io",
                "organization": "acme",
                "workspaces": {"name": "prod"},
            }
        }
    }
    result = _apply(doc)
    assert "cloud" not in result["terraform"]
    backend = result["terraform"]["backend"]["remote"]
    assert backend["hostname"] == "app.terraform.io"
    assert backend["organization"] == "acme"
    assert backend["workspaces"] == {"name": "prod"}


def test_invalid_json_returned_unchanged() -> None:
    assert CdktfJsonRule().apply("{not json", path=None) == "{not json"  # type: ignore[arg-type]


def test_preserves_tag_based_cloud_workspace_selection() -> None:
    """tag/project selection cannot be represented by the remote backend."""
    doc = {
        "terraform": {
            "cloud": {
                "hostname": "app.terraform.io",
                "organization": "acme",
                "workspaces": {"project": "platform", "tags": ["prod"]},
            }
        }
    }
    result = _apply(doc)
    assert result["terraform"]["cloud"] == doc["terraform"]["cloud"]
    assert "backend" not in result["terraform"]


def test_preserves_existing_backend_when_cloud_is_unsupported() -> None:
    doc = {
        "terraform": {
            "cloud": {"workspaces": {"tags": ["prod"]}},
            "backend": {"s3": {"bucket": "state"}},
        }
    }
    result = _apply(doc)
    assert result["terraform"]["cloud"] == doc["terraform"]["cloud"]
    assert result["terraform"]["backend"] == doc["terraform"]["backend"]


def test_preserves_non_dict_cloud() -> None:
    doc = {"terraform": {"cloud": "invalid"}}
    result = _apply(doc)
    assert result["terraform"]["cloud"] == "invalid"
    assert "backend" not in result["terraform"]


def test_preserves_non_dict_workspaces() -> None:
    doc = {"terraform": {"cloud": {"workspaces": "invalid"}}}
    result = _apply(doc)
    assert result["terraform"]["cloud"] == doc["terraform"]["cloud"]
    assert "backend" not in result["terraform"]


def test_converts_cloud_without_optional_fields() -> None:
    doc = {"terraform": {"cloud": {}}}
    result = _apply(doc)
    assert "cloud" not in result["terraform"]
    assert result["terraform"]["backend"]["remote"] == {"hostname": "app.terraform.io"}


def test_converts_cloud_with_empty_workspaces() -> None:
    doc = {"terraform": {"cloud": {"workspaces": {}}}}
    result = _apply(doc)
    backend = result["terraform"]["backend"]["remote"]
    assert backend == {"hostname": "app.terraform.io"}


def test_non_dict_json_document_returned_unchanged() -> None:
    content = json.dumps(["not", "a", "config"]) + "\n"
    assert CdktfJsonRule().apply(content, path=None) == content  # type: ignore[arg-type]


def test_preserves_cloud_when_existing_backend_is_invalid() -> None:
    doc = {"terraform": {"cloud": {}, "backend": "invalid"}}
    result = _apply(doc)
    assert result["terraform"]["cloud"] == {}
    assert result["terraform"]["backend"] == "invalid"


def test_engine_converts_synthesized_stack(tmp_path: Path) -> None:
    synth = {
        "//": {"metadata": {"backend": "local", "stackName": "app"}},
        "terraform": {
            "required_providers": {
                "aws": {"source": "registry.terraform.io/hashicorp/aws", "version": "~> 5.0"}
            }
        },
        "resource": {"aws_s3_bucket": {"bucket_ABC123": {"bucket": "my-bucket"}}},
    }
    stack = tmp_path / "cdktf.out" / "stacks" / "app"
    stack.mkdir(parents=True)
    (stack / "cdk.tf.json").write_text(json.dumps(synth))
    (tmp_path / "cdktf.json").write_text('{"language": "typescript"}')

    engine = ConversionEngine(repo_path=tmp_path, ignore_patterns=[])
    result = engine.run()

    assert result.files_changed == 1
    change = result.changes[0]
    assert "cdktf-json-terraform-block" in change.rule_hits
    assert "registry-rewrite" in change.rule_hits
    converted = json.loads(change.transformed)
    assert converted["terraform"]["required_version"] == ">= 1.6"
    provider = converted["terraform"]["required_providers"]["aws"]
    assert provider["source"] == "registry.opentofu.org/hashicorp/aws"


def test_engine_skips_hcl_rules_on_json(tmp_path: Path) -> None:
    """HCL-regex rules must not touch JSON files (e.g. interpolation cleanup)."""
    synth = {
        "terraform": {"required_version": ">= 1.6"},
        "output": {"endpoint": {"value": "${aws_lb.web.dns_name}"}},
    }
    (tmp_path / "cdk.tf.json").write_text(json.dumps(synth, indent=2) + "\n")

    engine = ConversionEngine(repo_path=tmp_path, ignore_patterns=[])
    result = engine.run()

    assert result.files_changed == 0
