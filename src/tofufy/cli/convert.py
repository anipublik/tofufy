"""Convert command - full repo migration."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from tofufy.backup import snapshot
from tofufy.config import load_config
from tofufy.converter.engine import ConversionEngine
from tofufy.git.clone import resolve_source
from tofufy.utils.ignore import load_ignore_patterns

app = typer.Typer(help="Convert a Terraform repo to OpenTofu.")
console = Console()


@app.callback(invoke_without_command=True)
def convert(
    ctx: typer.Context,
    source: str = typer.Argument(..., help="Local path or git URL to the repo"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show changes without writing"),
    backup: bool = typer.Option(False, "--backup", help="Snapshot repo before any writes"),
    verbose: bool = typer.Option(False, "--verbose", help="Full debug output"),
    config: Annotated[Path | None, typer.Option("--config", help="YAML config file")] = None,
    output: str = typer.Option("markdown", "--output", help="json | markdown | html | patch"),
    ai: bool = typer.Option(False, "--ai", help="Enable AI-assisted transformation"),
    llm_provider: str | None = typer.Option(
        None, "--llm-provider", help="anthropic | openai | kimi | openrouter"
    ),
    api_key: str | None = typer.Option(None, "--api-key", envvar="TOFUFY_API_KEY"),
    github_pr: bool = typer.Option(False, "--github-pr", help="Open a GitHub PR after conversion"),
    token: str | None = typer.Option(None, "--token", envvar="GITHUB_TOKEN"),
    platform: str | None = typer.Option(
        None, "--platform", help="github | gitlab | bitbucket"
    ),
) -> None:
    """Convert a Terraform repository to OpenTofu."""
    if ctx.invoked_subcommand is not None:
        return

    cfg = load_config(config)
    ignore = load_ignore_patterns(Path(".tofufyignore"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=not verbose,
    ) as progress:
        # Resolve source - clone if URL, use path if local
        task = progress.add_task("Resolving source...", total=None)
        repo_path = resolve_source(source, verbose=verbose)
        progress.update(task, description=f"Source: [cyan]{repo_path}[/cyan]")

        if backup and not dry_run:
            progress.update(task, description="Creating backup snapshot...")
            snap = snapshot(repo_path)
            console.print(f"[green]Backup created:[/green] {snap}")

        # Run conversion engine
        progress.update(task, description="Scanning Terraform files...")
        engine = ConversionEngine(
            repo_path=repo_path,
            ignore_patterns=ignore,
            ai_enabled=ai,
            llm_provider=llm_provider,
            api_key=api_key,
            verbose=verbose,
            config=cfg,
        )

        progress.update(task, description="Applying conversion rules...")
        result = engine.run()
        progress.stop()

    # Display results
    result.display(console=console, fmt=output, dry_run=dry_run)

    if not dry_run:
        if not backup:
            confirmed = typer.confirm(
                "\nNo backup was made. Write changes to disk?", default=False
            )
            if not confirmed:
                raise typer.Abort()

        result.write()
        console.print(f"\n[bold green]Done.[/bold green] {result.files_changed} file(s) changed.")
        result.print_checklist(console=console, dry_run=False)

        if github_pr or platform:
            _create_pr(repo_path, result, token, platform or "github")
    else:
        console.print(
            f"\n[dim]Dry run complete. {result.files_changed} file(s) would change.[/dim]"
        )
        result.print_checklist(console=console, dry_run=True)


def _create_pr(
    repo_path: Path, result: object, token: str | None, platform: str
) -> None:
    from tofufy.cli.pr import _do_create

    _do_create(repo_path=repo_path, result=result, token=token, platform=platform)
