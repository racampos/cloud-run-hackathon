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


def _write_step(f, step: dict, step_num: int = None):
    """Helper to write a step to markdown file."""
    step_type = step.get("type", "note")
    value = step.get("value", "")
    description = step.get("description", "")

    if step_type == "cmd":
        if step_num:
            f.write(f"{step_num}. **Command:** `{value}`\n")
        else:
            f.write(f"**Command:** `{value}`\n")
        if description:
            f.write(f"   - {description}\n\n")
        else:
            f.write("\n")
    elif step_type == "verify":
        if step_num:
            f.write(f"{step_num}. **Verify:** `{value}`\n")
        else:
            f.write(f"**Verify:** `{value}`\n")
        if description:
            f.write(f"   - {description}\n\n")
        else:
            f.write("\n")
    elif step_type == "output":
        f.write("**Expected Output:**\n```\n")
        f.write(value)
        f.write("\n```\n")
        if description:
            f.write(f"*{description}*\n\n")
        else:
            f.write("\n")
    elif step_type == "note":
        if step_num:
            f.write(f"{step_num}. **Note:** {value}\n\n")
        else:
            f.write(f"> **Note:** {value}\n\n")


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

        # Manual fallback: Extract missing outputs from events if not in session.state
        # This handles cases where LLMs wrap JSON in markdown despite instructions
        import re
        if "design_output" not in session.state or "exercise_spec" not in session.state:
            for event in events:
                if hasattr(event, 'content') and event.content:
                    text = event.content
                    # Try to find JSON in markdown code fences
                    json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
                    if json_match:
                        try:
                            parsed = json.loads(json_match.group(1))
                            # Detect which output this is by looking for key fields
                            if "topology_yaml" in parsed and "design_output" not in session.state:
                                session.state["design_output"] = parsed
                                logger.info("manual_extraction_design_output")
                            elif "title" in parsed and "objectives" in parsed and "constraints" in parsed:
                                if "exercise_spec" not in session.state:
                                    session.state["exercise_spec"] = parsed
                                    logger.info("manual_extraction_exercise_spec")
                        except json.JSONDecodeError:
                            pass

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
                        # Strip markdown code fences if present
                        if draft_guide.strip().startswith("```"):
                            lines = draft_guide.strip().split("\n")
                            # Remove first line (```json or ```) and last line (```)
                            draft_guide = "\n".join(lines[1:-1])
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

                # Generate markdown version from structured JSON
                if isinstance(draft_guide, dict):
                    guide_md_file = output_dir / "draft_lab_guide.md"
                    with open(guide_md_file, "w") as f:
                        # Title and metadata
                        f.write(f"# {draft_guide.get('title', 'Lab Guide')}\n\n")
                        f.write(f"**Estimated Time:** {draft_guide.get('estimated_time_minutes', 'N/A')} minutes\n\n")

                        # Objectives
                        if "objectives" in draft_guide:
                            f.write("## Learning Objectives\n\n")
                            for obj in draft_guide["objectives"]:
                                f.write(f"- {obj}\n")
                            f.write("\n")

                        # Prerequisites
                        if "prerequisites" in draft_guide:
                            f.write("## Prerequisites\n\n")
                            for prereq in draft_guide["prerequisites"]:
                                f.write(f"- {prereq}\n")
                            f.write("\n")

                        # Topology
                        if "topology_description" in draft_guide:
                            f.write("## Network Topology\n\n")
                            f.write(f"{draft_guide['topology_description']}\n\n")

                        # Initial Setup
                        if "initial_setup" in draft_guide:
                            f.write("## Initial Setup\n\n")
                            for step in draft_guide["initial_setup"]:
                                _write_step(f, step)
                            f.write("\n")

                        # Device Sections
                        if "device_sections" in draft_guide:
                            for device in draft_guide["device_sections"]:
                                f.write(f"## Device: {device.get('device_name', 'Unknown')}\n\n")
                                f.write(f"**Platform:** {device.get('platform', 'N/A')}  \n")
                                f.write(f"**Role:** {device.get('role', 'N/A')}\n\n")

                                # IP table
                                if device.get("ip_table"):
                                    f.write("### IP Addressing\n\n")
                                    f.write("| Interface | IP Address |\n")
                                    f.write("|-----------|------------|\n")
                                    for intf, ip in device["ip_table"].items():
                                        f.write(f"| {intf} | {ip} |\n")
                                    f.write("\n")

                                # Steps
                                if "steps" in device:
                                    f.write("### Configuration Steps\n\n")
                                    for i, step in enumerate(device["steps"], 1):
                                        _write_step(f, step, step_num=i)
                                    f.write("\n")

                        # Final Verification
                        if "final_verification" in draft_guide:
                            f.write("## Final Verification\n\n")
                            for step in draft_guide["final_verification"]:
                                _write_step(f, step)
                            f.write("\n")

                        # Troubleshooting
                        if "troubleshooting_tips" in draft_guide:
                            f.write("## Troubleshooting Tips\n\n")
                            for tip in draft_guide["troubleshooting_tips"]:
                                f.write(f"- {tip}\n")
                            f.write("\n")

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
