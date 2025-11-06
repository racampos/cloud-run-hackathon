#!/usr/bin/env python3
"""NetGenius Orchestrator - ADK Pipeline Entry Point.

This is the new ADK-based orchestrator using Google ADK for multi-agent
lab creation with intelligent reasoning and validation.
"""

import os
import sys
import json
import click
import structlog
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Load environment variables
load_dotenv()

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
@click.version_option(version="0.3.0-adk")
def cli():
    """NetGenius Orchestrator - ADK-powered multi-agent lab generation."""
    pass


@cli.command()
@click.option("--prompt", help="Initial lab prompt (interactive if not provided)")
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--dry-run", is_flag=True, help="Skip headless validation")
@click.option("--output", default="./output", help="Output directory for artifacts")
def create(prompt: str, verbose: bool, dry_run: bool, output: str):
    """Create a new lab using ADK pipeline with multi-turn Q&A."""
    import asyncio
    asyncio.run(_create_async(prompt, verbose, dry_run, output))


async def _create_async(prompt: str, verbose: bool, dry_run: bool, output: str):
    """Async implementation of create command."""

    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        console.print("[red]Error: GOOGLE_API_KEY not found in .env file[/red]")
        console.print("Please add your Gemini API key to orchestrator/.env")
        console.print("Get your key from: https://aistudio.google.com/app/apikey")
        sys.exit(1)

    console.print(
        Panel.fit(
            f"[bold cyan]NetGenius ADK Orchestrator[/bold cyan]\n"
            f"Multi-Agent Lab Creation Pipeline",
            border_style="cyan",
        )
    )

    logger.info(
        "adk_orchestrator_started",
        has_prompt=bool(prompt),
        verbose=verbose,
        dry_run=dry_run,
        output=output,
    )

    # Import and create pipeline
    from adk_agents.pipeline import create_lab_pipeline

    # Create pipeline based on dry-run flag
    pipeline = create_lab_pipeline(include_validation=not dry_run)

    # Initialize ADK session and runner
    app_name = "adk_agents"
    user_id = "instructor"
    import time
    session_id = f"lab_{int(time.time())}"

    session_service = InMemorySessionService()

    # Create session first (required before running)
    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )

    runner = Runner(
        agent=pipeline,
        app_name=app_name,
        session_service=session_service
    )

    # Interactive mode if no prompt provided
    if not prompt:
        console.print("\n[cyan]Interactive Lab Creation[/cyan]")
        console.print("[dim]The agent will ask clarifying questions about your lab requirements.[/dim]\n")
        prompt = input("What lab would you like to create? ")

    console.print("\n[cyan]Starting lab creation pipeline...[/cyan]\n")

    # Run pipeline
    try:
        # Create initial message
        message = types.Content(
            parts=[types.Part(text=prompt)],
            role="user"
        )

        # Initial run
        events = list(runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=message
        ))

        # Display agent responses
        for event in events:
            if hasattr(event, 'content') and event.content:
                console.print(f"\n[green]{event.content}[/green]\n")

        # Get final session state
        session = await session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )

        # Pipeline completed - check what was generated
        if session.state:
            console.print("\n[bold green]✓ Lab creation pipeline completed![/bold green]\n")

            # Save outputs
            output_dir = Path(output)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save exercise spec
            if "exercise_spec" in session.state:
                spec_file = output_dir / "exercise_spec.json"
                with open(spec_file, "w") as f:
                    json.dump(session.state["exercise_spec"], f, indent=2)
                console.print(f"[green]✓ Exercise spec saved:[/green] {spec_file}")

            # Save design output
            if "design_output" in session.state:
                design_file = output_dir / "design_output.json"
                with open(design_file, "w") as f:
                    json.dump(session.state["design_output"], f, indent=2)
                console.print(f"[green]✓ Design output saved:[/green] {design_file}")

            # Save draft lab guide
            if "draft_lab_guide" in session.state:
                draft_guide = session.state["draft_lab_guide"]

                # Parse if it's a JSON string
                if isinstance(draft_guide, str):
                    try:
                        draft_guide = json.loads(draft_guide)
                    except json.JSONDecodeError:
                        # It's text but not JSON, save as-is
                        pass

                guide_json_file = output_dir / "draft_lab_guide.json"
                with open(guide_json_file, "w") as f:
                    if isinstance(draft_guide, dict):
                        json.dump(draft_guide, f, indent=2)
                    else:
                        f.write(str(draft_guide))
                console.print(f"[green]✓ Draft lab guide (JSON) saved:[/green] {guide_json_file}")

                # Save markdown version if available
                if isinstance(draft_guide, dict):
                    guide_md = draft_guide.get("markdown", "")
                    if guide_md:
                        guide_md_file = output_dir / "draft_lab_guide.md"
                        with open(guide_md_file, "w") as f:
                            f.write(guide_md)
                        console.print(f"[green]✓ Draft lab guide (Markdown) saved:[/green] {guide_md_file}")

            # Save validation result
            if "validation_result" in session.state:
                val_file = output_dir / "validation_result.json"
                with open(val_file, "w") as f:
                    json.dump(session.state["validation_result"], f, indent=2)
                console.print(f"[green]✓ Validation result saved:[/green] {val_file}")

                # Display validation summary
                val_result = session.state["validation_result"]
                if val_result.get("success"):
                    console.print("\n[bold green]✓ Headless validation PASSED[/bold green]")
                else:
                    console.print("\n[bold red]✗ Headless validation FAILED[/bold red]")
                    console.print(f"[red]Error: {val_result.get('summary', {}).get('error', 'Unknown error')}[/red]")
            elif dry_run:
                console.print("\n[dim]Skipped headless validation (dry-run mode)[/dim]")

            console.print(f"\n[dim]Artifacts saved to: {output_dir.absolute()}[/dim]")

        else:
            console.print("[yellow]Pipeline did not complete. Check logs for details.[/yellow]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        logger.error("adk_pipeline_failed", error=str(e), exc_info=True)
        console.print(f"\n[red]Error: {e}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
def version():
    """Show version information."""
    console.print(
        Panel(
            "[bold]NetGenius ADK Orchestrator[/bold]\n"
            "Version: 0.3.0-adk (M0-M5: ADK Pipeline Complete)\n"
            "Status: Development\n"
            "Agents: Planner ✓ Designer ✓ Author ✓ Validator ✓\n"
            "Pipeline: SequentialAgent ✓",
            border_style="cyan",
        )
    )


if __name__ == "__main__":
    try:
        cli()
    except Exception as e:
        logger.error("orchestrator_failed", error=str(e), exc_info=True)
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)
