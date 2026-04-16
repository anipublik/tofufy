"""Root CLI entry point."""

from __future__ import annotations

import importlib.util
import platform
import sys

import typer
from rich.console import Console
from rich.table import Table

from tofufy import __version__
from tofufy.cli import pr, state, tacos
from tofufy.cli.convert import convert_command

app = typer.Typer(
    name="tofufy",
    help="TFE to OpenTofu. The whole thing, not just the code.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()

# `convert` has no subcommands — registering it as a plain command keeps the
# CLI parser from treating a user-provided source path as a sub-command name.
app.command("convert", help="Convert a Terraform repo to OpenTofu.")(convert_command)
app.add_typer(state.app, name="state")
app.add_typer(tacos.app, name="tacos")
app.add_typer(pr.app, name="pr")


def _module_available(name: str) -> bool:
    """Return True iff the named module is importable.

    `importlib.util.find_spec` raises ModuleNotFoundError for dotted names
    when a parent package is missing, so swallow that.
    """
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


@app.command("version")
def version_cmd() -> None:
    """Show version, Python info, and optional-integration status."""
    from tofufy.ai.assistant import PROVIDER_MODELS

    console.print(f"[bold]tofufy[/bold] {__version__}")
    console.print(f"Python   {sys.version.split()[0]}  ({sys.executable})")
    console.print(f"Platform {platform.platform()}")

    ai_available = _module_available("litellm")
    git_available = _module_available("git") and _module_available("github")

    def _status(ok: bool, extra: str) -> str:
        if ok:
            return "[green]available[/green]"
        # Rich treats `[x]` as markup; escape so users actually see the extra name.
        return rf"[dim]missing (install tofufy\[{extra}])[/dim]"

    console.print("\n[bold]Optional integrations:[/bold]")
    console.print(f"  AI        {_status(ai_available, 'ai')}")
    console.print(f"  Git/PR    {_status(git_available, 'git')}")
    console.print(f"  S3 state  {_status(_module_available('boto3'), 's3')}")
    console.print(f"  GCS state {_status(_module_available('google.cloud.storage'), 'gcs')}")

    if ai_available:
        providers = ", ".join(sorted(PROVIDER_MODELS))
        console.print(f"\n  Providers: {providers}")


@app.command("rules")
def rules_cmd(
    category: str | None = typer.Option(
        None,
        "--category",
        "-c",
        help="Filter by category: breaking | important | advisory",
    ),
) -> None:
    """List all conversion rules grouped by category."""
    from tofufy.converter.engine import ALL_RULES, RULE_DESCRIPTIONS, RuleCategory

    allowed: set[RuleCategory] | None
    if category is None:
        allowed = None
    else:
        try:
            allowed = {RuleCategory(category.lower())}
        except ValueError as err:
            valid = ", ".join(c.value for c in RuleCategory)
            raise typer.BadParameter(f"Unknown category. Valid: {valid}") from err

    table = Table(title="tofufy rules", show_lines=False, header_style="bold")
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Name", no_wrap=True)
    table.add_column("What it does")

    colors = {
        RuleCategory.BREAKING: "red",
        RuleCategory.IMPORTANT: "yellow",
        RuleCategory.ADVISORY: "dim",
    }

    for cr in ALL_RULES:
        if allowed is not None and cr.category not in allowed:
            continue
        label = f"[{colors[cr.category]}]{cr.category.value}[/{colors[cr.category]}]"
        desc = RULE_DESCRIPTIONS.get(cr.rule.name, "")
        table.add_row(label, cr.rule.name, desc)

    console.print(table)
    console.print(
        f"\n[dim]{len(ALL_RULES)} rules available. "
        f"Use --category breaking|important|advisory to filter.[/dim]"
    )
