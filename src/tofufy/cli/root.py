"""Root CLI entry point."""

from __future__ import annotations

import typer
from rich.console import Console

from tofufy import __version__
from tofufy.cli import convert, pr, state, tacos

app = typer.Typer(
    name="tofufy",
    help="TFE to OpenTofu. The whole thing, not just the code.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()

app.add_typer(convert.app, name="convert")
app.add_typer(state.app, name="state")
app.add_typer(tacos.app, name="tacos")
app.add_typer(pr.app, name="pr")


@app.command("version")
def version_cmd() -> None:
    """Show version, Python info, and LLM provider status."""
    import platform
    import sys

    console.print(f"[bold]tofufy[/bold] {__version__}")
    console.print(f"Python {sys.version}")
    console.print(f"Platform: {platform.platform()}")
