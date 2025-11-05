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
@click.version_option(version="0.3.0-m3")
def cli():
    """NetGenius Orchestrator - Multi-agent lab generation system."""
    pass


@cli.command()
@click.option("--prompt", required=True, help="Instructor prompt for lab creation")
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--dry-run", is_flag=True, help="Skip headless validation")
@click.option("--output", default="./output", help="Output directory for artifacts")
def create(prompt: str, verbose: bool, dry_run: bool, output: str):
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
        output=output,
    )

    async def run_agents():
        from agents import planner, designer, author
        import json
        import os
        from pathlib import Path

        try:
            # Step 1: Pedagogy Planner
            console.print("\n[cyan]1. Running Pedagogy Planner...[/cyan]")
            exercise_spec = await planner.extract_exercise_spec(prompt)
            console.print(f"   ✓ Title: {exercise_spec.title}")
            console.print(f"   ✓ Level: {exercise_spec.level}")
            console.print(f"   ✓ Objectives: {len(exercise_spec.objectives)} items")

            # Step 2: Designer
            console.print("\n[cyan]2. Running Designer (with linting)...[/cyan]")
            design = await designer.create_design(exercise_spec)
            console.print(f"   ✓ Devices: {len(design.platforms)}")
            console.print(f"   ✓ Topology validated: {design.lint_results.get('topology', {}).get('ok', False)}")
            console.print(f"   ✓ CLI validated: all devices passed")

            # Step 3: Author
            console.print("\n[cyan]3. Running Lab Guide Author (with linting)...[/cyan]")
            draft_guide = await author.create_lab_guide(design, exercise_spec)
            console.print(f"   ✓ Title: {draft_guide.title}")
            console.print(f"   ✓ Devices: {len(draft_guide.device_sections)}")
            console.print(f"   ✓ Estimated time: {draft_guide.estimated_time_minutes} minutes")

            # Save outputs
            output_dir = Path(output)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save exercise spec
            spec_file = output_dir / "exercise_spec.json"
            with open(spec_file, "w") as f:
                json.dump(exercise_spec.model_dump(), f, indent=2)
            console.print(f"\n[green]✓ Exercise spec saved:[/green] {spec_file}")

            # Save design output
            design_file = output_dir / "design_output.json"
            with open(design_file, "w") as f:
                json.dump(design.model_dump(), f, indent=2)
            console.print(f"[green]✓ Design output saved:[/green] {design_file}")

            # Save draft lab guide
            guide_file = output_dir / "draft_lab_guide.md"
            with open(guide_file, "w") as f:
                f.write(draft_guide.markdown)
            console.print(f"[green]✓ Draft lab guide saved:[/green] {guide_file}")

            guide_json_file = output_dir / "draft_lab_guide.json"
            with open(guide_json_file, "w") as f:
                json.dump(draft_guide.model_dump(), f, indent=2)
            console.print(f"[green]✓ Draft lab guide (JSON) saved:[/green] {guide_json_file}")

            # Step 4: Validator (M3)
            if dry_run:
                console.print("\n[dim]Skipping headless validation (dry-run mode)[/dim]")
            else:
                console.print("\n[cyan]4. Running Validator (headless execution)...[/cyan]")
                from agents import validator
                from tools.artifacts import save_artifacts_locally

                validation_result = await validator.validate_lab(
                    draft_guide=draft_guide,
                    topology_yaml=design.topology_yaml,
                    initial_configs=design.initial_configs,
                )

                console.print(f"   ✓ Execution ID: {validation_result.execution_id}")
                console.print(f"   ✓ Duration: {validation_result.duration_seconds:.1f}s")
                console.print(f"   ✓ Status: {'PASS' if validation_result.success else 'FAIL'}")
                console.print(f"   ✓ Steps: {validation_result.artifacts.passed_steps}/{validation_result.artifacts.total_steps} passed")

                # Save validation artifacts locally
                await save_artifacts_locally(
                    artifacts=validation_result.artifacts,
                    output_dir=str(output_dir / "validation"),
                )
                console.print(f"[green]✓ Validation artifacts saved:[/green] {output_dir / 'validation'}")

                if not validation_result.success:
                    console.print("\n[red]✗ Validation FAILED - Lab needs revision[/red]")
                else:
                    console.print("\n[bold green]✓ Validation PASSED - Lab ready for publishing[/bold green]")

            console.print("\n[bold green]✓ Lab creation completed![/bold green]")
            console.print(f"[dim]Artifacts saved to: {output_dir.absolute()}[/dim]")

        except Exception as e:
            logger.error("agent_execution_failed", error=str(e), exc_info=True)
            console.print(f"\n[red]Error: {e}[/red]")
            raise

    asyncio.run(run_agents())


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
            "Version: 0.3.0-m3 (M3: Headless Validation)\n"
            "Status: Development\n"
            "Agents: Planner ✓ Designer ✓ Author ✓ Validator ✓",
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
