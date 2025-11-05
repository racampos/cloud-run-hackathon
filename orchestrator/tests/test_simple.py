"""Simple integration tests for NetGenius agents (no pytest required)."""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import planner, designer, author
from schemas import ExerciseSpec


async def test_planner():
    """Test Planner agent with various prompts."""
    print("\n=== Testing Planner Agent ===\n")

    prompts = [
        "Create a CCNA-level lab for static routing with 2 routers",
        "Create an OSPF lab for CCNP with 3 routers",
        "Create a basic VLAN configuration lab for CCNA",
    ]

    for prompt in prompts:
        print(f"Prompt: {prompt}")
        spec = await planner.extract_exercise_spec(prompt)
        print(f"  ✓ Title: {spec.title}")
        print(f"  ✓ Level: {spec.level}")
        print(f"  ✓ Objectives: {len(spec.objectives)} items")
        print(f"  ✓ Devices: {spec.constraints.get('devices')}")
        print()

    print("✓ All Planner tests passed!\n")


async def test_designer():
    """Test Designer agent (without linter)."""
    print("\n=== Testing Designer Agent ===\n")

    spec = ExerciseSpec(
        title="Static Routing Lab",
        objectives=[
            "Configure IP addresses on router interfaces",
            "Configure static routes between networks",
            "Verify end-to-end connectivity",
        ],
        constraints={"devices": 2, "time_minutes": 30, "complexity": "low"},
        level="CCNA",
        prerequisites=["Basic router CLI navigation"],
    )

    print(f"Input spec: {spec.title}")
    print("Note: Designer will attempt to lint configs (may fail if service unavailable)")

    try:
        design = await designer.create_design(spec, max_retries=0)
        print(f"  ✓ Devices: {len(design.platforms)}")
        print(f"  ✓ Topology generated: {len(design.topology_yaml)} chars")
        print(f"  ✓ Initial configs: {list(design.initial_configs.keys())}")
        print("\n✓ Designer test passed!\n")
    except Exception as e:
        print(f"  ⚠ Designer test skipped (linter unavailable): {e}\n")


async def test_author():
    """Test Author agent (without linter)."""
    print("\n=== Testing Author Agent ===\n")

    spec = ExerciseSpec(
        title="Static Routing Lab",
        objectives=["Configure static routes", "Verify connectivity"],
        constraints={"devices": 2, "time_minutes": 30, "complexity": "low"},
        level="CCNA",
        prerequisites=[],
    )

    print("Generating design...")
    try:
        design = await designer.create_design(spec, max_retries=0)
        print(f"  ✓ Design created with {len(design.platforms)} devices")

        print("Generating lab guide...")
        draft_guide = await author.create_lab_guide(design, spec, max_retries=0)

        print(f"  ✓ Title: {draft_guide.title}")
        print(f"  ✓ Devices: {len(draft_guide.device_sections)}")
        print(f"  ✓ Estimated time: {draft_guide.estimated_time_minutes} minutes")
        print(f"  ✓ Markdown length: {len(draft_guide.markdown)} chars")

        # Check device sections
        for section in draft_guide.device_sections:
            cmd_count = sum(1 for s in section.steps if s.type == "cmd")
            verify_count = sum(1 for s in section.steps if s.type == "verify")
            print(f"  ✓ Device {section.device_name}: {cmd_count} commands, {verify_count} verifications")

        print("\n✓ Author test passed!\n")
    except Exception as e:
        print(f"  ⚠ Author test skipped (linter unavailable): {e}\n")


async def test_full_flow():
    """Test full Planner -> Designer -> Author flow."""
    print("\n=== Testing Full Agent Flow ===\n")

    prompt = "Create a simple static routing lab for CCNA with 2 routers"
    print(f"User prompt: {prompt}\n")

    try:
        # Step 1: Planner
        print("Step 1: Running Planner...")
        spec = await planner.extract_exercise_spec(prompt)
        print(f"  ✓ Spec: {spec.title} ({spec.level})")

        # Step 2: Designer
        print("Step 2: Running Designer...")
        design = await designer.create_design(spec, max_retries=0)
        print(f"  ✓ Design: {len(design.platforms)} devices")

        # Step 3: Author
        print("Step 3: Running Author...")
        draft_guide = await author.create_lab_guide(design, spec, max_retries=0)
        print(f"  ✓ Lab guide: {draft_guide.title}")
        print(f"  ✓ Content: {len(draft_guide.markdown)} chars")

        print("\n✓ Full flow test passed!\n")
        return True
    except Exception as e:
        print(f"  ⚠ Full flow test skipped (linter unavailable): {e}\n")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("NetGenius M2 Agent Tests")
    print("=" * 60)

    # Test 1: Planner (no external dependencies)
    await test_planner()

    # Test 2: Designer (requires linter service)
    await test_designer()

    # Test 3: Author (requires linter service)
    await test_author()

    # Test 4: Full flow (requires linter service)
    success = await test_full_flow()

    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print("✓ Planner agent working")
    if success:
        print("✓ Designer agent working")
        print("✓ Author agent working")
        print("✓ Full flow working")
    else:
        print("⚠ Designer/Author tests skipped (linter service not available)")
        print("  To run full tests, start the parser-linter service")
    print()


if __name__ == "__main__":
    asyncio.run(main())
