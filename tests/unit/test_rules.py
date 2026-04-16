"""Table-driven rule tests: input HCL in, expected HCL out."""

from __future__ import annotations

from pathlib import Path

import pytest

from tofufy.converter.rules.cloud import CloudBlockRule
from tofufy.converter.rules.opentofu_features import OpenTofuFeaturesRule
from tofufy.converter.rules.registry import RegistryRewriteRule
from tofufy.converter.rules.sentinel_to_opa import SentinelToOpaRule

FIXTURES = Path(__file__).parent.parent / "testdata" / "fixtures"


# ---------------------------------------------------------------------------
# RegistryRewriteRule
# ---------------------------------------------------------------------------

REGISTRY_CASES = [
    pytest.param(
        'source = "registry.terraform.io/hashicorp/aws"',
        'source = "registry.opentofu.org/hashicorp/aws"',
        id="single-provider",
    ),
    pytest.param(
        "registry.terraform.io/hashicorp/google\nregistry.terraform.io/hashicorp/aws",
        "registry.opentofu.org/hashicorp/google\nregistry.opentofu.org/hashicorp/aws",
        id="multi-provider",
    ),
    pytest.param(
        "no registry reference here",
        "no registry reference here",
        id="no-op",
    ),
]


@pytest.mark.parametrize(("inp", "expected"), REGISTRY_CASES)
def test_registry_rule(inp: str, expected: str) -> None:
    rule = RegistryRewriteRule()
    assert rule.apply(inp, Path("main.tf")) == expected


def test_registry_rule_fixture() -> None:
    rule = RegistryRewriteRule()
    inp = (FIXTURES / "registry_input.tf").read_text()
    expected = (FIXTURES / "registry_expected.tf").read_text()
    assert rule.apply(inp, Path("main.tf")) == expected


# ---------------------------------------------------------------------------
# CloudBlockRule
# ---------------------------------------------------------------------------

_CLOUD_INPUT_SIMPLE = """\
terraform {
  cloud {
    hostname     = "app.terraform.io"
    organization = "acme"
    workspaces {
      name = "prod"
    }
  }
}
"""

# The critical real-world case: cloud{} appears AFTER required_providers{}
# The old regex couldn't handle this because [^}]*? breaks on nested braces.
_CLOUD_INPUT_WITH_REQUIRED_PROVIDERS = """\
terraform {
  required_version = ">= 1.3"

  required_providers {
    aws = {
      source  = "registry.terraform.io/hashicorp/aws"
      version = "~> 5.0"
    }
  }

  cloud {
    hostname     = "app.terraform.io"
    organization = "acme"
    workspaces {
      name = "prod"
    }
  }
}
"""


def test_cloud_block_rule_simple() -> None:
    rule = CloudBlockRule()
    result = rule.apply(_CLOUD_INPUT_SIMPLE, Path("main.tf"))
    assert 'backend "remote"' in result
    assert "cloud {" not in result


def test_cloud_block_rule_with_required_providers() -> None:
    """Regression test: cloud{} after required_providers{} must still convert."""
    rule = CloudBlockRule()
    result = rule.apply(_CLOUD_INPUT_WITH_REQUIRED_PROVIDERS, Path("main.tf"))
    assert 'backend "remote"' in result
    assert "cloud {" not in result
    # required_providers block must survive intact
    assert "required_providers" in result
    assert "hashicorp/aws" in result


def test_cloud_block_preserves_org_and_workspace() -> None:
    rule = CloudBlockRule()
    result = rule.apply(_CLOUD_INPUT_SIMPLE, Path("main.tf"))
    assert 'organization = "acme"' in result
    assert 'name   = "prod"' in result


def test_cloud_block_rule_noop_when_no_cloud() -> None:
    rule = CloudBlockRule()
    content = 'terraform {\n  backend "s3" {}\n}\n'
    assert rule.apply(content, Path("main.tf")) == content


def test_cloud_block_prefix_workspace() -> None:
    """Workspace prefix (for multiple workspaces) must be preserved."""
    inp = """\
terraform {
  cloud {
    organization = "acme"
    workspaces {
      prefix = "myapp-"
    }
  }
}
"""
    rule = CloudBlockRule()
    result = rule.apply(inp, Path("main.tf"))
    assert 'prefix = "myapp-"' in result


# ---------------------------------------------------------------------------
# OpenTofuFeaturesRule
# ---------------------------------------------------------------------------

OTF_CASES = [
    pytest.param(
        'required_version = "~> 1.3"',
        'required_version = ">= 1.6"',
        id="bump-old-version",
    ),
    pytest.param(
        'required_version = ">= 1.7"',
        'required_version = ">= 1.7"',
        id="already-new-enough",
    ),
]


@pytest.mark.parametrize(("inp", "expected"), OTF_CASES)
def test_opentofu_features_version(inp: str, expected: str) -> None:
    rule = OpenTofuFeaturesRule()
    assert rule.apply(inp, Path("main.tf")) == expected


# ---------------------------------------------------------------------------
# SentinelToOpaRule
# ---------------------------------------------------------------------------


def test_sentinel_to_opa_adds_package() -> None:
    rule = SentinelToOpaRule()
    inp = 'import "tfplan"\n\nmain = rule { true }\n'
    result = rule.apply(inp, Path("policy.sentinel"))
    assert result.startswith("package ")
    assert "default allow" in result


def test_sentinel_to_opa_ignores_tf_files() -> None:
    rule = SentinelToOpaRule()
    content = 'import "tfplan"\n'
    assert rule.apply(content, Path("main.tf")) == content
