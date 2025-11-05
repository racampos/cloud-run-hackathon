"""Lab Guide Author Agent - Creates student-facing lab instructions with linting."""

import structlog
from typing import Optional
from schemas import DesignOutput, DraftLabGuide, DeviceSection, CommandStep
from tools import parser_linter

logger = structlog.get_logger()


AUTHOR_SYSTEM_PROMPT = """You are a technical writer specializing in hands-on networking lab guides for Cisco courses.

Your role is to:
1. Write clear, step-by-step instructions for students
2. Include verification steps to confirm correct configuration
3. Provide context and learning guidance
4. Format instructions in a consistent, professional style

Writing guidelines:
- Use numbered steps for sequential tasks
- Include expected command output for verification steps
- Add brief explanations of "why" for key concepts
- Use consistent formatting and terminology
- Interleave verification steps (show commands, ping tests)
- Assume students have basic CLI familiarity but need guidance

Verification best practices:
- After interface configuration: show ip interface brief
- After routing configuration: show ip route, show ip protocols
- After VLAN configuration: show vlan brief, show interfaces trunk
- For connectivity: ping tests between networks
- For protocol status: show ospf neighbor, show eigrp neighbors, etc.
"""


async def create_lab_guide(
    design: DesignOutput,
    exercise_spec=None,
    llm_client=None,
    max_retries: int = 2
) -> DraftLabGuide:
    """
    Create lab guide from network design.

    Args:
        design: Network topology and configurations
        exercise_spec: Optional learning objectives
        llm_client: Optional LLM client (for future integration)
        max_retries: Maximum number of lint-fix-retry cycles

    Returns:
        DraftLabGuide with markdown and structured sections

    Raises:
        Exception if linting fails after max retries
    """
    logger.info(
        "author_started",
        num_devices=len(design.platforms),
    )

    # For MVP: Use template-based generation
    # In production: Use LLM to generate contextual instructions
    markdown, device_sections = _generate_lab_guide_template(design)

    # Validate with linting
    for attempt in range(max_retries + 1):
        logger.info("author_validation_attempt", attempt=attempt + 1)

        lint_results = {}
        all_ok = True

        # Lint each device section
        for section in device_sections:
            commands_payload = [
                {"command": step.value}
                for step in section.steps
                if step.type == "cmd"  # Only lint commands, not verify steps
            ]

            if not commands_payload:
                continue

            cli_result = await parser_linter.lint_cli(
                device_type=section.platform,
                commands=commands_payload,
                sequence_mode="stateful",
                stop_on_error=False,
            )

            lint_results[section.device_name] = cli_result

            # Check if all commands passed
            failed_commands = [
                r for r in cli_result.get("results", []) if not r.get("ok")
            ]

            if failed_commands:
                all_ok = False
                logger.warning(
                    "author_cli_lint_failed",
                    device=section.device_name,
                    attempt=attempt + 1,
                    num_failed=len(failed_commands),
                    failed_commands=[r.get("command") for r in failed_commands],
                )

        if all_ok:
            logger.info("author_validation_passed", attempt=attempt + 1)
            break

        if attempt < max_retries:
            # Try to fix issues
            device_sections = _fix_author_issues(device_sections, lint_results)
            # Regenerate markdown from fixed sections
            markdown = _regenerate_markdown(device_sections)
        else:
            raise Exception(
                f"Lab guide validation failed after {max_retries} retries. "
                f"Failed devices: {[d for d, r in lint_results.items() if not all(x.get('ok') for x in r.get('results', []))]}"
            )

    # Determine title and time estimate
    title = "Network Configuration Lab"
    if exercise_spec:
        title = exercise_spec.title

    # Estimate based on device count and step complexity
    total_steps = sum(len(section.steps) for section in device_sections)
    estimated_time = max(20, min(60, total_steps * 2))  # 2 min per step, 20-60 min range

    guide = DraftLabGuide(
        title=title,
        markdown=markdown,
        device_sections=device_sections,
        estimated_time_minutes=estimated_time,
        lint_results=lint_results,
    )

    logger.info(
        "author_completed",
        title=title,
        num_devices=len(device_sections),
        estimated_time=estimated_time,
    )

    return guide


def _generate_lab_guide_template(design: DesignOutput) -> tuple[str, list[DeviceSection]]:
    """
    Generate lab guide from design using templates.

    Returns:
        (markdown_content, device_sections)
    """
    device_sections = []
    markdown_parts = []

    # Header
    markdown_parts.append("# Network Configuration Lab\n\n")
    markdown_parts.append("## Overview\n\n")
    markdown_parts.append(
        "In this lab, you will configure network devices to establish "
        "connectivity and implement the specified network design.\n\n"
    )

    # Topology section
    markdown_parts.append("## Topology\n\n")
    markdown_parts.append("```yaml\n")
    markdown_parts.append(design.topology_yaml)
    markdown_parts.append("```\n\n")

    # Device configuration sections
    for device_name in sorted(design.platforms.keys()):
        platform = design.platforms[device_name]
        initial_commands = design.initial_configs.get(device_name, [])
        target_commands = design.target_configs.get(device_name, [])

        markdown_parts.append(f"## Device {device_name.upper()}\n\n")
        markdown_parts.append(
            f"Configure {device_name} ({platform}) with the following steps:\n\n"
        )

        steps = []
        step_num = 1

        # Initial configuration steps
        markdown_parts.append("### Initial Configuration\n\n")
        for cmd in initial_commands:
            if cmd.strip() and not cmd.startswith("!"):
                markdown_parts.append(f"{step_num}. Execute: `{cmd}`\n")
                steps.append(
                    CommandStep(
                        type="cmd",
                        value=cmd,
                        description=f"Configure: {cmd}",
                    )
                )
                step_num += 1

        # Add verification after initial config
        markdown_parts.append(
            f"\n{step_num}. Verify interfaces: `show ip interface brief`\n"
        )
        steps.append(
            CommandStep(
                type="verify",
                value="show ip interface brief",
                description="Verify interface status",
            )
        )
        step_num += 1
        markdown_parts.append("\n")

        # Target configuration steps
        if target_commands:
            markdown_parts.append("### Lab Tasks\n\n")
            markdown_parts.append("Complete the following configuration:\n\n")
            for cmd in target_commands:
                if cmd.strip() and not cmd.startswith("!"):
                    markdown_parts.append(f"{step_num}. Execute: `{cmd}`\n")
                    steps.append(
                        CommandStep(
                            type="cmd",
                            value=cmd,
                            description=f"Configure: {cmd}",
                        )
                    )
                    step_num += 1

            # Add appropriate verification based on config type
            target_text = " ".join(target_commands).lower()
            if "router ospf" in target_text:
                markdown_parts.append(
                    f"\n{step_num}. Verify OSPF neighbors: `show ip ospf neighbor`\n"
                )
                steps.append(
                    CommandStep(
                        type="verify",
                        value="show ip ospf neighbor",
                        description="Verify OSPF adjacency",
                    )
                )
                step_num += 1
                markdown_parts.append(
                    f"{step_num}. Verify routing table: `show ip route ospf`\n"
                )
                steps.append(
                    CommandStep(
                        type="verify",
                        value="show ip route ospf",
                        description="Verify OSPF routes",
                    )
                )
                step_num += 1
            elif "router eigrp" in target_text:
                markdown_parts.append(
                    f"\n{step_num}. Verify EIGRP neighbors: `show ip eigrp neighbors`\n"
                )
                steps.append(
                    CommandStep(
                        type="verify",
                        value="show ip eigrp neighbors",
                        description="Verify EIGRP adjacency",
                    )
                )
                step_num += 1
            elif "ip route" in target_text:
                markdown_parts.append(
                    f"\n{step_num}. Verify routing table: `show ip route`\n"
                )
                steps.append(
                    CommandStep(
                        type="verify",
                        value="show ip route",
                        description="Verify static routes",
                    )
                )
                step_num += 1
            elif "vlan" in target_text:
                markdown_parts.append(
                    f"\n{step_num}. Verify VLANs: `show vlan brief`\n"
                )
                steps.append(
                    CommandStep(
                        type="verify",
                        value="show vlan brief",
                        description="Verify VLAN configuration",
                    )
                )
                step_num += 1
                markdown_parts.append(
                    f"{step_num}. Verify trunks: `show interfaces trunk`\n"
                )
                steps.append(
                    CommandStep(
                        type="verify",
                        value="show interfaces trunk",
                        description="Verify trunk configuration",
                    )
                )
                step_num += 1
            elif "access-list" in target_text:
                markdown_parts.append(
                    f"\n{step_num}. Verify ACL: `show access-lists`\n"
                )
                steps.append(
                    CommandStep(
                        type="verify",
                        value="show access-lists",
                        description="Verify ACL configuration",
                    )
                )
                step_num += 1

            markdown_parts.append("\n")

        # Create device section
        device_sections.append(
            DeviceSection(
                device_name=device_name,
                platform=platform,
                steps=steps,
            )
        )

    # Final verification section
    markdown_parts.append("## Final Verification\n\n")
    markdown_parts.append(
        "After completing all device configurations, verify end-to-end connectivity:\n\n"
    )
    markdown_parts.append(
        "1. Test connectivity between networks using ping\n"
    )
    markdown_parts.append(
        "2. Verify all routing protocols have established adjacencies\n"
    )
    markdown_parts.append(
        "3. Check running configurations with `show running-config`\n"
    )
    markdown_parts.append("\n")

    # Success criteria
    markdown_parts.append("## Success Criteria\n\n")
    markdown_parts.append(
        "Your lab is complete when:\n"
        "- All interfaces are up/up\n"
        "- All routing protocol adjacencies are established\n"
        "- End-to-end connectivity is verified\n"
        "- All verification commands show expected results\n"
    )

    markdown = "".join(markdown_parts)
    return markdown, device_sections


def _fix_author_issues(
    sections: list[DeviceSection],
    lint_results: dict,
) -> list[DeviceSection]:
    """
    Attempt to auto-fix common authoring issues.

    For MVP: Return unchanged (LLM would fix in production)
    """
    logger.warning("author_auto_fix_not_implemented")
    return sections


def _regenerate_markdown(sections: list[DeviceSection]) -> str:
    """Regenerate markdown from device sections after fixes."""
    markdown_parts = []

    markdown_parts.append("# Network Configuration Lab\n\n")
    markdown_parts.append("## Overview\n\n")
    markdown_parts.append(
        "In this lab, you will configure network devices.\n\n"
    )

    for section in sections:
        markdown_parts.append(f"## Device {section.device_name.upper()}\n\n")
        step_num = 1
        for step in section.steps:
            if step.type == "cmd":
                markdown_parts.append(f"{step_num}. Execute: `{step.value}`\n")
            else:
                markdown_parts.append(f"{step_num}. Verify: `{step.value}`\n")
            step_num += 1
        markdown_parts.append("\n")

    return "".join(markdown_parts)
