#!/usr/bin/env python3
"""Test the Interactive Planner Agent with multi-turn Q&A.

This script demonstrates the Deep Research-style interaction where the agent
asks clarifying questions before generating the complete ExerciseSpec.

Usage:
    python test_planner_interactive.py
"""

import os
import sys
import json
import time
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from adk_agents.planner import planner_agent

console = Console()


async def test_interactive_planner():
    """Test the interactive planner with multi-turn Q&A."""

    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        console.print("[red]Error: GOOGLE_API_KEY not found in .env file[/red]")
        console.print("Please add your Gemini API key to orchestrator/.env")
        console.print("Get your key from: https://aistudio.google.com/app/apikey")
        return

    console.print(
        Panel.fit(
            "[bold cyan]NetGenius Interactive Lab Planner[/bold cyan]\n"
            "Multi-Turn Q&A with ADK",
            border_style="cyan",
        )
    )

    # Initialize ADK session and runner
    # Use "adk_agents" as app_name to match the package structure
    app_name = "adk_agents"
    user_id = "instructor"
    session_id = f"planning_{int(time.time())}"

    session_service = InMemorySessionService()
    runner = Runner(
        agent=planner_agent,
        app_name=app_name,
        session_service=session_service
    )

    console.print("\n[dim]This agent will ask clarifying questions about your lab requirements.[/dim]\n")

    # Turn 1: Initial prompt
    initial_prompt = input("What lab would you like to create? ")

    console.print("\n[cyan]Agent is thinking...[/cyan]\n")

    try:
        # Create Content message from string
        message = types.Content(
            parts=[types.Part(text=initial_prompt)],
            role="user"
        )

        events = list(runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=message
        ))

        # Print agent's response (questions or ExerciseSpec)
        for event in events:
            if hasattr(event, 'content') and event.content:
                console.print(f"[green]Agent:[/green] {event.content}\n")

        # Check if ExerciseSpec is ready
        session = await session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )

        # Multi-turn loop
        max_turns = 5  # Prevent infinite loops
        turn_count = 0

        while "exercise_spec" not in session.state and turn_count < max_turns:
            turn_count += 1

            # Get user's answers
            user_response = input("\nYour answer: ")

            if not user_response.strip():
                console.print("[yellow]Please provide an answer to continue.[/yellow]")
                continue

            console.print("\n[cyan]Agent is thinking...[/cyan]\n")

            # Create message from user response
            message = types.Content(
                parts=[types.Part(text=user_response)],
                role="user"
            )

            # Continue conversation (session preserves history)
            events = list(runner.run(
                user_id=user_id,
                session_id=session_id,
                new_message=message
            ))

            # Print agent's response
            for event in events:
                if hasattr(event, 'content') and event.content:
                    console.print(f"[green]Agent:[/green] {event.content}\n")

            # Check if done
            session = await session_service.get_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id
            )

            if "exercise_spec" in session.state:
                console.print("\n[bold green]✓ Exercise specification complete![/bold green]\n")
                console.print(
                    Panel(
                        json.dumps(session.state["exercise_spec"], indent=2),
                        title="ExerciseSpec",
                        border_style="green"
                    )
                )
                break

        if turn_count >= max_turns and "exercise_spec" not in session.state:
            console.print("[yellow]Maximum turns reached. Ending conversation.[/yellow]")

        return session.state.get("exercise_spec")

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        import traceback
        console.print(traceback.format_exc())
        return None


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_interactive_planner())
