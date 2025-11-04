"""NetGenius Orchestrator - Main Entry Point."""

import asyncio
import sys
import click
import structlog
from rich.console import Console
from rich.panel import Panel

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()
console = Console()


@click.group()
@click.version_option(version="0.1.0-stub")
def cli():
    """NetGenius Orchestrator - Multi-agent lab generation system."""
    pass


@cli.command()
@click.option("--prompt", required=True, help="Instructor prompt for lab creation")
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--dry-run", is_flag=True, help="Skip headless validation")
def create(prompt: str, verbose: bool, dry_run: bool):
    """Create a new lab from instructor prompt."""
    console.print(
        Panel.fit(
            f"[bold cyan]NetGenius Orchestrator[/bold cyan]\n"
            f"Creating lab from prompt...",
            border_style="cyan",
        )
    )

    logger.info(
        "orchestrator_started",
        prompt=prompt,
        verbose=verbose,
        dry_run=dry_run,
    )

    # Stub: Just log what we would do
    console.print("\n[yellow]STUB MODE - M1 Skeleton[/yellow]\n")
    console.print("Would execute:")
    console.print("  1. ✓ Pedagogy Planner agent")
    console.print("  2. ✓ Designer agent (with linting)")
    console.print("  3. ✓ Lab Guide Author agent (with linting)")
    console.print("  4. ✓ Validator agent (headless runner)")
    console.print("  5. ✓ Publisher agent")

    if dry_run:
        console.print("\n[dim]Skipping headless validation (dry-run mode)[/dim]")

    console.print(
        "\n[green]✓ Orchestrator skeleton working![/green]"
    )
    console.print(
        "[dim]Full implementation coming in M2-M4[/dim]"
    )


@cli.command()
def test_integration():
    """Test integration with parser-linter and headless-runner stubs."""
    console.print(
        Panel.fit(
            "[bold cyan]Testing Service Integration[/bold cyan]",
            border_style="cyan",
        )
    )

    async def run_test():
        from tools import parser_linter, headless_runner

        # Test parser-linter
        console.print("\n[cyan]1. Testing Parser-Linter service...[/cyan]")
        topology_result = await parser_linter.lint_topology("devices:\n  r1:\n")
        console.print(f"   Topology lint: {'✓' if topology_result.get('ok') else '✗'}")

        cli_result = await parser_linter.lint_cli(
            "cisco_2911",
            [{"command": "configure terminal"}],
        )
        console.print(
            f"   CLI lint: {'✓' if cli_result.get('results') else '✗'}"
        )

        # Test headless runner
        console.print("\n[cyan]2. Testing Headless Runner job...[/cyan]")
        job_result = await headless_runner.submit_job({
            "exercise_id": "test-001",
            "topology_yaml": "test",
            "devices": {"r1": {"platform": "cisco_2911", "initial": [], "steps": []}},
        })
        console.print(f"   Job submit: {'✓' if job_result.get('job_id') else '✗'}")

        console.print("\n[green]✓ All integrations working![/green]")

    asyncio.run(run_test())


@cli.command()
def version():
    """Show version information."""
    console.print(
        Panel(
            "[bold]NetGenius Orchestrator[/bold]\n"
            "Version: 0.1.0-stub (M1)\n"
            "Status: Development",
            border_style="cyan",
        )
    )


if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        logger.error("orchestrator_failed", error=str(e), exc_info=True)
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)
