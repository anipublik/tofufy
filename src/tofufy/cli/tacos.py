"""TACOS subcommands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

app = typer.Typer(help="Generate TACOS platform configuration files.")
console = Console()

PLATFORMS = ["atlantis", "spacelift", "env0", "scalr", "digger"]


@app.command("init")
def tacos_init(
    platform: str = typer.Option(
        ..., "--platform", help="atlantis | spacelift | env0 | scalr | digger"
    ),
    repo_path: Annotated[Path, typer.Option("--path", help="Repo root")] = Path("."),
    out: Annotated[
        Path | None, typer.Option("--out", help="Output path (default: repo root)")
    ] = None,
    template_dir: Annotated[
        Path | None, typer.Option("--template-dir", help="Custom template directory")
    ] = None,
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Generate TACOS platform config files for a converted repo."""
    if platform not in PLATFORMS:
        console.print(
            f"[red]Unknown platform:[/red] {platform}. "
            f"Supported: {', '.join(PLATFORMS)}"
        )
        raise typer.Exit(1)

    from tofufy.tacos.generator import TACOSGenerator

    out_path = out or repo_path
    generator = TACOSGenerator(
        platform=platform,
        repo_path=repo_path,
        out_path=out_path,
        template_dir=template_dir,
    )

    files = generator.generate(dry_run=dry_run)

    for f in files:
        prefix = "[dim](dry-run)[/dim] " if dry_run else "[green]wrote[/green] "
        console.print(f"{prefix}{f}")

    if not dry_run:
        console.print(f"\n[bold green]{platform}[/bold green] config generated in {out_path}")
