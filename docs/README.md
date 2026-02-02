# tofufy

**TFE to OpenTofu. The whole thing, not just the code.**

<!-- TODO: add an animated GIF of a full conversion run here -->

---

## Install

```bash
pipx install tofufy
uv tool install tofufy
pip install tofufy
```

Standalone binaries for Linux, macOS, and Windows ship with every [GitHub Release](https://github.com/anipublik/tofufy/releases). No Python needed.

---

## Quick start

```bash
# See what would change, touch nothing
tofufy convert ./my-infra --dry-run

# Convert with a backup first
tofufy convert ./my-infra --backup

# Convert and open a GitHub PR in one shot
tofufy convert ./my-infra --backup --github-pr --token $GITHUB_TOKEN
```

After converting, run this:

```bash
tofu init -upgrade
tofu providers lock -platform=linux_amd64 -platform=darwin_arm64 -platform=windows_amd64
tofu plan
```

---

## What it does

Point it at a repo - local path or git URL. It rewrites your HCL, migrates your state, generates your TACOS config, and opens a PR. You don't touch any of it.

**Rule-based changes (no AI key needed):**

- `cloud {}` block stripped and replaced with `backend "remote" {}`
- `registry.terraform.io` rewritten to `registry.opentofu.org` everywhere
- `null_resource` migrated to `terraform_data` - triggers renamed, null provider removed
- `required_version` bumped to `>= 1.6`
- `removed {}` lifecycle syntax fixed for OpenTofu
- Deprecated `"${var.foo}"` interpolations simplified to `var.foo`
- Deprecated `list()` and `map()` functions replaced with literal syntax
- `encode_tfvars` / `decode_tfvars` replaced with `jsonencode` / `jsondecode`
- S3 backend cleaned up - `skip_s3_checksum` removed, DynamoDB users get a lockfile hint
- `terraform_binary` set to `tofu` in any Terragrunt files found

**Advisory annotations (added as comments, nothing deleted):**

- `tfe_*` resources flagged - they still work but may need TACOS platform equivalents
- `import {}` blocks with variable interpolation in `id` flagged - OpenTofu doesn't support that
- Sentinel policy files get a structural Rego mapping with a TODO
- Exact-version provider pins flagged for review
- `terraform.workspace` usage annotated with workspace naming caveat
- Outputs with names like `db_password` or `api_token` that lack `sensitive = true` flagged

**AI-assisted pass (bring your own key, optional):**

Pass `--ai --llm-provider anthropic --api-key $KEY` and tofufy runs a second pass with an LLM over every changed file, catching module refactors and Sentinel logic that regex can't handle safely.

---

## File extensions

tofufy converts `.tf` files. It does not rename them to `.tofu`.

The `.tofu` extension (added in OpenTofu 1.8) is for OpenTofu-specific overrides - when you have both `foo.tf` and `foo.tofu` in a directory, OpenTofu loads only `foo.tofu`. That's useful for module authors supporting both tools. For a full migration you don't need it, and renaming everything would break most existing tooling.

---

## State

tofufy does not touch your `.tfstate` files during HCL conversion. State migration is a separate step.

```bash
# Pull all workspace state from TFE
tofufy state migrate --org my-org --token $TFE_TOKEN --target-backend s3

# Or just pull first to inspect
tofufy state pull --org my-org --token $TFE_TOKEN --out-dir ./state-backup
```

State files from Terraform 1.5.x and earlier load in OpenTofu without changes. If you're on Terraform 1.6+, migrate sooner rather than later - the state format started diverging after the license change.

---

## Commands

```
tofufy convert <path|git-url>   Full repo conversion
tofufy state list               List TFE orgs and workspaces
tofufy state pull               Pull state from TFE
tofufy state migrate            Pull TFE state, push to S3/GCS/AzureRM/local
tofufy state rotate-keys        Rotate state encryption keys
tofufy tacos init               Generate Atlantis/Spacelift/env0/Scalr/Digger config
tofufy pr create                Open a PR from the converted diff
tofufy version                  Version and LLM provider status
```

**Global flags:**

```
--dry-run              Show diff, write nothing
--backup               Snapshot repo before writing anything
--verbose              Full debug output
--config FILE          YAML config file
--output FORMAT        json | markdown | html | patch
--ai                   Enable AI-assisted pass
--llm-provider NAME    anthropic | openai | kimi | openrouter
--api-key KEY          Your LLM key - not stored, not logged
```

---

## Safety

Nothing is written without `--backup` or a confirmation prompt. Dry run shows a colored diff file by file using Rich.

`.tofufyignore` works like `.gitignore`. Anything listed there is skipped. Use it for vendor dirs, generated code, or modules you don't own.

No telemetry. No analytics. No phoning home. The LLM key goes straight from your shell to the provider - tofufy never stores it.

---

## TACOS support

```bash
tofufy tacos init --platform atlantis
tofufy tacos init --platform spacelift
tofufy tacos init --platform env0
tofufy tacos init --platform scalr
tofufy tacos init --platform digger
```

Template-driven. Drop a custom template in `~/.tofufy/tacos/` to add your own platform.

---

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md).
