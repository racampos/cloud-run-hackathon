#!/usr/bin/env python3
"""Simple non-interactive test of the Planner agent."""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from adk_agents.planner import planner_agent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


async def main():
    """Test the planner with a complete prompt."""

    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY not found in .env file")
        return 1

    print("Testing ADK Planner Agent...")
    print("=" * 50)

    # Create a complete prompt (so agent doesn't need to ask questions)
    prompt = """Create an intermediate static routing lab with 3 routers.
Include floating static routes for redundancy.
Difficulty: Intermediate
Time: 45 minutes
Students should learn to configure static routes, default routes, and verify connectivity."""

    print(f"\nPrompt: {prompt}\n")

    # Initialize session service
    session_service = InMemorySessionService()

    # Create session first
    app_name = "adk_agents"
    user_id = "test_user"
    session_id = "test_session_1"

    print(f"Creating session: app_name={app_name}, user_id={user_id}, session_id={session_id}")

    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )

    print(f"Session created: {session}")

    # Create runner
    runner = Runner(
        agent=planner_agent,
        app_name=app_name,
        session_service=session_service
    )

    print("Runner created")

    # Create message
    message = types.Content(
        parts=[types.Part(text=prompt)],
        role="user"
    )

    print("Running agent...")

    try:
        # Run agent
        events = list(runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=message
        ))

        print(f"\nReceived {len(events)} events")

        # Print events
        for i, event in enumerate(events):
            print(f"\nEvent {i}: {type(event).__name__}")
            if hasattr(event, 'content'):
                print(f"Content: {event.content}")

        # Get session state
        session = await session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )

        print(f"\nSession state keys: {list(session.state.keys())}")

        if "exercise_spec" in session.state:
            print("\n✓ Exercise spec created!")
            import json
            print(json.dumps(session.state["exercise_spec"], indent=2))
        else:
            print("\n✗ No exercise_spec in session state")
            print(f"State: {session.state}")

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
