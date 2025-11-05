#!/usr/bin/env python3
"""Quick test to verify ADK setup is working."""

import os
import sys
from dotenv import load_dotenv
from rich.console import Console

console = Console()

def test_adk_setup():
    """Test ADK installation and configuration."""

    console.print("\n[cyan]Testing ADK Setup...[/cyan]\n")

    # Test 1: Load .env
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        console.print("[red]✗ GOOGLE_API_KEY not found in .env[/red]")
        console.print("  Please add your API key to orchestrator/.env")
        console.print("  Get it from: https://aistudio.google.com/app/apikey")
        return False
    elif api_key == "your-gemini-api-key-here":
        console.print("[yellow]⚠ GOOGLE_API_KEY is still the placeholder value[/yellow]")
        console.print("  Please replace with your actual API key")
        return False
    else:
        console.print(f"[green]✓ GOOGLE_API_KEY found (length: {len(api_key)})[/green]")

    # Test 2: Import ADK
    try:
        import google.adk
        console.print(f"[green]✓ google.adk imported successfully[/green]")
    except ImportError as e:
        console.print(f"[red]✗ Failed to import google.adk: {e}[/red]")
        return False

    # Test 3: Import ADK components
    try:
        from google.adk.agents import LlmAgent
        from google.adk.runner import Runner
        from google.adk.session import InMemorySessionService
        console.print("[green]✓ ADK components imported[/green]")
    except ImportError as e:
        console.print(f"[red]✗ Failed to import ADK components: {e}[/red]")
        return False

    # Test 4: Import our schemas
    try:
        from schemas import ExerciseSpec
        console.print("[green]✓ ExerciseSpec schema imported[/green]")
    except ImportError as e:
        console.print(f"[red]✗ Failed to import ExerciseSpec: {e}[/red]")
        return False

    # Test 5: Import planner agent
    try:
        from adk_agents.planner import planner_agent
        console.print(f"[green]✓ Planner agent loaded: {planner_agent.name}[/green]")
    except ImportError as e:
        console.print(f"[red]✗ Failed to import planner agent: {e}[/red]")
        return False

    console.print("\n[bold green]✓ All setup tests passed![/bold green]\n")
    console.print("[dim]You can now test the interactive planner with:[/dim]")
    console.print("[dim]  python test_planner_interactive.py[/dim]\n")

    return True


if __name__ == "__main__":
    success = test_adk_setup()
    sys.exit(0 if success else 1)
