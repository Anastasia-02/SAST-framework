#!/usr/bin/env python3
"""
Main entry point for SAST Regression Testing Framework
"""

import sys
from pathlib import Path
import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .core.test_runner import RegressionTestRunner
from .utils.logger import logger

app = typer.Typer(help="SAST Regression Testing Framework")
console = Console()


@app.command()
def run_all(
        config_dir: str = typer.Option("./config", help="Configuration directory"),
        results_dir: str = typer.Option("./results", help="Results directory"),
        save_baseline: bool = typer.Option(False, "--save-baseline", help="Save results as baseline"),
        project: Optional[str] = typer.Option(None, help="Run only specific project")
):
    """Run regression tests on all projects"""

    try:
        runner = RegressionTestRunner(config_dir, results_dir)

        # Setup
        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
        ) as progress:
            task = progress.add_task("Setting up test environment...", total=None)

            if not runner.setup():
                console.print("[red]Failed to setup test runner[/red]")
                sys.exit(1)

            progress.update(task, completed=1, description="Setup completed")

        # Run tests
        if project:
            console.print(f"\n[blue]Running tests for project: {project}[/blue]")
            success = runner.run_project(project, save_baseline)
        else:
            console.print(f"\n[blue]Running tests for all projects[/blue]")
            success = runner.run_all(save_baseline)

        # Cleanup
        runner.cleanup()

        if success:
            console.print("\n[green]✓ Regression testing completed successfully[/green]")
            sys.exit(0)
        else:
            console.print("\n[yellow]⚠ Regression testing completed with warnings[/yellow]")
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Test execution interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        logger.exception("Unhandled exception")
        sys.exit(1)


@app.command()
def list_projects(config_dir: str = typer.Option("./config", help="Configuration directory")):
    """List all configured projects"""

    from .core.config_loader import ConfigLoader

    try:
        config_loader = ConfigLoader(config_dir)
        config = config_loader.load()

        table = Table(title="Configured Projects")
        table.add_column("Name", style="cyan")
        table.add_column("Language", style="green")
        table.add_column("Path", style="yellow")
        table.add_column("Analyzers", style="magenta")

        for project in config.projects:
            analyzers = ", ".join(project.analyzers)
            table.add_row(
                project.name,
                project.language,
                project.path,
                analyzers
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@app.command()
def list_tools(config_dir: str = typer.Option("./config", help="Configuration directory")):
    """List all configured tools"""

    from .core.config_loader import ConfigLoader

    try:
        config_loader = ConfigLoader(config_dir)
        config = config_loader.load()

        table = Table(title="Configured Tools")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Image/Command", style="yellow")

        for tool_name, tool in config.tools.items():
            if tool.type == "docker":
                command = f"{tool.image}:{tool.version}"
            else:
                command = tool.command

            table.add_row(
                tool_name,
                tool.type,
                command
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@app.command()
def show_baselines():
    """Show available baseline results"""

    from .core.baseline_manager import BaselineManager

    try:
        baseline_dir = Path("./baseline")
        if not baseline_dir.exists():
            console.print("[yellow]No baseline directory found[/yellow]")
            return

        manager = BaselineManager(baseline_dir)
        baselines = manager.list_baselines()

        if not baselines:
            console.print("[yellow]No baselines found[/yellow]")
            return

        table = Table(title="Available Baselines")
        table.add_column("Project", style="cyan")
        table.add_column("Tools", style="green")

        for project_name, tools in baselines.items():
            table.add_row(
                project_name,
                ", ".join(tools)
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def main():
    """Main entry point"""
    app()


if __name__ == "__main__":
    main()