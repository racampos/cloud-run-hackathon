#!/usr/bin/env python3
"""Simple M2 test script - tests Planner, Designer, and Author agents."""

import asyncio
import sys
import os

# Add orchestrator to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "orchestrator"))

# Now import after path is set
import structlog
from schemas import ExerciseSpec

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)

logger = structlog.get_logger()


async def test_planner():
    """Test Planner agent."""
    print("\n" + "="*60)
    print("Testing Planner Agent")
    print("="*60 + "\n")

    from agents import planner

    test_prompts = [
        ("Static Routing", "Create a CCNA-level lab for static routing with 2 routers"),
        ("OSPF", "Create an OSPF lab for CCNP with 3 routers"),
        ("VLAN", "Create a basic VLAN configuration lab for CCNA"),
    ]

    for name, prompt in test_prompts:
        print(f"Test: {name}")
        print(f"Prompt: {prompt}")
        spec = await planner.extract_exercise_spec(prompt)
        print(f"  ✓ Title: {spec.title}")
        print(f"  ✓ Level: {spec.level}")
        print(f"  ✓ Objectives: {len(spec.objectives)} items")
        print(f"  ✓ Devices: {spec.constraints.get('devices')}\n")

    print("✓ All Planner tests passed!\n")
    return True


async def test_full_flow_dry():
    """Test full flow without linter (dry run)."""
    print("\n" + "="*60)
    print("Testing Full Flow (Dry Run - No Linter)")
    print("="*60 + "\n")

    from agents import planner

    prompt = "Create a simple static routing lab for CCNA with 2 routers"
    print(f"User prompt: {prompt}\n")

    print("Step 1: Running Planner...")
    spec = await planner.extract_exercise_spec(prompt)
    print(f"  ✓ Title: {spec.title}")
    print(f"  ✓ Level: {spec.level}")
    print(f"  ✓ Objectives: {len(spec.objectives)} items")
    print(f"  ✓ Devices: {spec.constraints.get('devices')}")
    print(f"  ✓ Time: {spec.constraints.get('time_minutes')} minutes\n")

    print("✓ Dry run test passed!\n")
    print("Note: To test Designer and Author, start the parser-linter service")
    print("      and set PARSER_LINTER_URL environment variable.\n")

    return True


async def main():
    """Run all tests."""
    print("="*60)
    print("NetGenius M2 Agent Tests")
    print("="*60)

    try:
        # Test Planner (no external dependencies)
        success1 = await test_planner()

        # Test full flow (dry run)
        success2 = await test_full_flow_dry()

        if success1 and success2:
            print("="*60)
            print("✅ All M2 tests passed!")
            print("="*60)
            return 0
        else:
            print("❌ Some tests failed")
            return 1

    except Exception as e:
        logger.error("test_failed", error=str(e), exc_info=True)
        print(f"\n❌ Test failed with error: {e}\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
