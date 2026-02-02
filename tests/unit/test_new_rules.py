"""Table-driven tests for the 10 new rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from tofufy.converter.rules.backend_s3 import BackendS3Rule
from tofufy.converter.rules.deprecated_functions import DeprecatedFunctionsRule
from tofufy.converter.rules.deprecated_interpolation import DeprecatedInterpolationRule
from tofufy.converter.rules.import_block import ImportBlockRule
from tofufy.converter.rules.null_resource import NullResourceRule
from tofufy.converter.rules.provider_version import ProviderVersionRule
from tofufy.converter.rules.removed_block import RemovedBlockRule
from tofufy.converter.rules.sensitive_output import SensitiveOutputRule
from tofufy.converter.rules.terragrunt import TerragruntRule
from tofufy.converter.rules.tfe_resources import TFEResourcesRule
from tofufy.converter.rules.workspace_vars import WorkspaceVarsRule

P = Path("main.tf")


# ---------------------------------------------------------------------------
# NullResourceRule
# ---------------------------------------------------------------------------

class TestNullResourceRule:
    rule = NullResourceRule()

    def test_renames_resource_type(self):
        inp = 'resource "null_resource" "wait" {\n  triggers = { always = timestamp() }\n}\n'
        out = self.rule.apply(inp, P)
        assert 'resource "terraform_data"' in out
        assert "null_resource" not in out

    def test_renames_triggers(self):
        inp = 'resource "null_resource" "x" {\n  triggers = {\n    id = var.id\n  }\n}\n'
        out = self.rule.apply(inp, P)
        assert "triggers_replace" in out
        assert "triggers =" not in out

    def test_removes_provider_null(self):
        inp = 'resource "null_resource" "x" {\n  provider = null\n  triggers = {}\n}\n'
        out = self.rule.apply(inp, P)
        assert "provider = null" not in out

    def test_renames_self_triggers(self):
        inp = (
            'resource "null_resource" "x" {}\n'
            'output "v" { value = null_resource.x.self.triggers.key }\n'
        )
        out = self.rule.apply(inp, P)
        assert "self.triggers_replace" in out

    def test_removes_null_from_required_providers(self):
        inp = (
            'terraform {\n  required_providers {\n'
            '    null = {\n      source = "hashicorp/null"\n    }\n'
            '  }\n}\n'
            'resource "null_resource" "x" {}\n'
        )
        out = self.rule.apply(inp, P)
        # After rename, null provider block should be removed
        assert '"hashicorp/null"' not in out

    def test_noop_when_no_null_resource(self):
        content = 'resource "aws_instance" "x" {}\n'
        assert self.rule.apply(content, P) == content


# ---------------------------------------------------------------------------
# DeprecatedInterpolationRule
# ---------------------------------------------------------------------------

class TestDeprecatedInterpolationRule:
    rule = DeprecatedInterpolationRule()

    @pytest.mark.parametrize("inp,expected", [
        ('name = "${var.foo}"', "name = var.foo"),
        ('value = "${local.bar}"', "value = local.bar"),
        ('source = "${module.vpc.id}"', "source = module.vpc.id"),
        ('arn = "${data.aws_caller_identity.current.arn}"',
         "arn = data.aws_caller_identity.current.arn"),
    ])
    def test_simplifies_solo_interpolation(self, inp, expected):
        assert self.rule.apply(inp, P) == expected

    @pytest.mark.parametrize("unchanged", [
        'name = "prefix-${var.foo}"',        # has literal prefix
        'name = "${var.a}-${var.b}"',         # two interpolations
        'name = "literal"',                   # no interpolation
    ])
    def test_leaves_complex_strings_alone(self, unchanged):
        assert self.rule.apply(unchanged, P) == unchanged


# ---------------------------------------------------------------------------
# DeprecatedFunctionsRule
# ---------------------------------------------------------------------------

class TestDeprecatedFunctionsRule:
    rule = DeprecatedFunctionsRule()

    def test_encode_tfvars(self):
        inp = 'x = encode_tfvars(var.config)'
        assert "jsonencode(" in self.rule.apply(inp, P)

    def test_decode_tfvars(self):
        inp = 'x = decode_tfvars(var.blob)'
        assert "jsondecode(" in self.rule.apply(inp, P)

    def test_list_function(self):
        inp = 'x = list("a", "b", "c")'
        out = self.rule.apply(inp, P)
        assert '["a", "b", "c"]' in out

    def test_map_function(self):
        inp = 'x = map("key", var.value)'
        out = self.rule.apply(inp, P)
        assert "key = var.value" in out

    def test_template_file_annotated(self):
        inp = 'data "template_file" "init" {\n  template = file("tmpl.tpl")\n}\n'
        out = self.rule.apply(inp, P)
        assert "TOFUFY" in out
        assert 'data "template_file"' in out  # block still present

    def test_noop_when_no_deprecated(self):
        content = 'x = jsonencode(var.config)\n'
        assert self.rule.apply(content, P) == content


# ---------------------------------------------------------------------------
# TerragruntRule
# ---------------------------------------------------------------------------

class TestTerragruntRule:
    rule = TerragruntRule()
    tg_path = Path("terragrunt.hcl")

    def test_replaces_binary_setting(self):
        inp = 'terraform_binary = "terraform"\n'
        out = self.rule.apply(inp, self.tg_path)
        assert 'terraform_binary = "tofu"' in out

    def test_injects_binary_in_terraform_block(self):
        inp = 'terraform {\n  source = "git::https://example.com/module.git"\n}\n'
        out = self.rule.apply(inp, self.tg_path)
        assert 'terraform_binary = "tofu"' in out

    def test_noop_on_tf_file(self):
        inp = 'terraform_binary = "terraform"\n'
        assert self.rule.apply(inp, Path("main.tf")) == inp

    def test_noop_when_already_tofu(self):
        inp = 'terraform_binary = "tofu"\n'
        assert self.rule.apply(inp, self.tg_path) == inp


# ---------------------------------------------------------------------------
# TFEResourcesRule
# ---------------------------------------------------------------------------

class TestTFEResourcesRule:
    rule = TFEResourcesRule()

    def test_annotates_tfe_resource(self):
        inp = 'resource "tfe_workspace" "main" {\n  name = "prod"\n}\n'
        out = self.rule.apply(inp, P)
        assert "TOFUFY" in out
        assert 'resource "tfe_workspace"' in out  # block still present

    def test_annotates_tfe_data(self):
        inp = 'data "tfe_organization" "org" {\n  name = "acme"\n}\n'
        out = self.rule.apply(inp, P)
        assert "TOFUFY" in out

    def test_noop_when_no_tfe(self):
        content = 'resource "aws_instance" "x" {}\n'
        assert self.rule.apply(content, P) == content

    def test_idempotent(self):
        inp = 'resource "tfe_workspace" "main" {\n  name = "prod"\n}\n'
        once = self.rule.apply(inp, P)
        twice = self.rule.apply(once, P)
        assert once == twice


# ---------------------------------------------------------------------------
# ImportBlockRule
# ---------------------------------------------------------------------------

class TestImportBlockRule:
    rule = ImportBlockRule()

    def test_flags_interpolated_id(self):
        inp = 'import {\n  id = "prefix-${var.env}"\n  to = aws_instance.x\n}\n'
        out = self.rule.apply(inp, P)
        assert "TOFUFY WARNING" in out

    def test_no_flag_for_literal_id(self):
        inp = 'import {\n  id = "i-1234567890abcdef0"\n  to = aws_instance.x\n}\n'
        out = self.rule.apply(inp, P)
        assert "TOFUFY" not in out

    def test_noop_when_no_import(self):
        content = 'resource "aws_instance" "x" {}\n'
        assert self.rule.apply(content, P) == content


# ---------------------------------------------------------------------------
# BackendS3Rule
# ---------------------------------------------------------------------------

class TestBackendS3Rule:
    rule = BackendS3Rule()

    def test_removes_skip_s3_checksum(self):
        inp = (
            'backend "s3" {\n'
            '  bucket            = "my-bucket"\n'
            '  skip_s3_checksum  = true\n'
            '}\n'
        )
        out = self.rule.apply(inp, P)
        assert "skip_s3_checksum" not in out
        assert "my-bucket" in out

    def test_removes_skip_metadata_api_check(self):
        inp = 'backend "s3" {\n  skip_metadata_api_check = false\n  bucket = "x"\n}\n'
        out = self.rule.apply(inp, P)
        assert "skip_metadata_api_check" not in out

    def test_adds_lockfile_hint_when_dynamodb_present(self):
        inp = 'backend "s3" {\n  dynamodb_table = "lock"\n  bucket = "x"\n}\n'
        out = self.rule.apply(inp, P)
        assert "use_lockfile" in out

    def test_noop_when_no_s3_backend(self):
        content = 'backend "gcs" {\n  bucket = "x"\n}\n'
        assert self.rule.apply(content, P) == content


# ---------------------------------------------------------------------------
# ProviderVersionRule
# ---------------------------------------------------------------------------

class TestProviderVersionRule:
    rule = ProviderVersionRule()

    def test_flags_exact_pin(self):
        inp = (
            'terraform {\n  required_providers {\n'
            '    aws = {\n      source = "hashicorp/aws"\n'
            '      version = "5.12.0"\n    }\n  }\n}\n'
        )
        out = self.rule.apply(inp, P)
        assert "TOFUFY" in out

    def test_noop_on_range_constraint(self):
        inp = (
            'terraform {\n  required_providers {\n'
            '    aws = {\n      source = "hashicorp/aws"\n'
            '      version = "~> 5.0"\n    }\n  }\n}\n'
        )
        assert "TOFUFY" not in self.rule.apply(inp, P)

    def test_noop_when_no_required_providers(self):
        content = 'resource "aws_instance" "x" {}\n'
        assert self.rule.apply(content, P) == content


# ---------------------------------------------------------------------------
# RemovedBlockRule
# ---------------------------------------------------------------------------

class TestRemovedBlockRule:
    rule = RemovedBlockRule()

    def test_hoists_destroy_from_lifecycle(self):
        inp = (
            "removed {\n"
            "  from = aws_instance.old\n"
            "  lifecycle {\n"
            "    destroy = false\n"
            "  }\n"
            "}\n"
        )
        out = self.rule.apply(inp, P)
        assert "lifecycle" not in out
        assert "destroy = false" in out

    def test_noop_when_no_removed_lifecycle(self):
        content = 'resource "aws_instance" "x" {}\n'
        assert self.rule.apply(content, P) == content


# ---------------------------------------------------------------------------
# WorkspaceVarsRule
# ---------------------------------------------------------------------------

class TestWorkspaceVarsRule:
    rule = WorkspaceVarsRule()

    def test_annotates_first_usage(self):
        inp = 'env = terraform.workspace\n'
        out = self.rule.apply(inp, P)
        assert "TOFUFY" in out
        assert "terraform.workspace" in out

    def test_idempotent(self):
        inp = 'env = terraform.workspace\n'
        once = self.rule.apply(inp, P)
        twice = self.rule.apply(once, P)
        assert once == twice

    def test_noop_when_no_workspace_ref(self):
        content = 'x = var.env\n'
        assert self.rule.apply(content, P) == content


# ---------------------------------------------------------------------------
# SensitiveOutputRule
# ---------------------------------------------------------------------------

class TestSensitiveOutputRule:
    rule = SensitiveOutputRule()

    def test_flags_sensitive_keyword_in_name(self):
        inp = 'output "db_password" {\n  value = aws_db.x.password\n}\n'
        out = self.rule.apply(inp, P)
        assert "TOFUFY" in out

    def test_no_flag_when_already_marked(self):
        inp = (
            'output "db_password" {\n'
            '  value     = aws_db.x.password\n'
            '  sensitive = true\n'
            '}\n'
        )
        out = self.rule.apply(inp, P)
        assert "TOFUFY" not in out

    def test_no_flag_for_innocuous_output(self):
        inp = 'output "instance_id" {\n  value = aws_instance.x.id\n}\n'
        assert "TOFUFY" not in self.rule.apply(inp, P)

    def test_noop_when_no_output(self):
        content = 'resource "aws_instance" "x" {}\n'
        assert self.rule.apply(content, P) == content
