"""Pedagogy Planner Agent - Extracts learning objectives from instructor requirements."""

import structlog
from typing import Optional
from schemas import ExerciseSpec

logger = structlog.get_logger()


# Prompt templates for different lab types
PLANNER_SYSTEM_PROMPT = """You are a networking pedagogy expert and instructional designer specializing in hands-on lab exercises for Cisco networking courses.

Your role is to analyze instructor requirements and extract structured learning objectives for lab exercises.

When analyzing requirements, consider:
- Clear, measurable learning objectives
- Appropriate device count and topology complexity for the level
- Realistic time estimates
- Required prerequisites
- Alignment with certification levels (CCNA, CCNP, CCIE)

Lab types you should recognize:
- **Routing:** Static routes, RIP, EIGRP, OSPF, BGP
- **Switching:** VLANs, trunking, STP, port security
- **Security:** ACLs, NAT, firewall rules, VPNs
- **Services:** DHCP, DNS, NTP
- **Troubleshooting:** Diagnosing and fixing misconfigurations

Extract and structure the following information:
1. **Title:** Clear, concise lab title
2. **Objectives:** Specific, measurable learning goals (what students will configure/verify)
3. **Constraints:** Device count, estimated time, complexity level
4. **Level:** Target certification level (CCNA, CCNP, etc.)
5. **Prerequisites:** Required prior knowledge

Be specific and actionable. Avoid vague objectives like "understand routing" - prefer "configure OSPF area 0 on two routers and verify adjacency."
"""

PLANNER_EXTRACTION_PROMPT = """Based on the following instructor prompt, extract a structured lab exercise specification.

Instructor Prompt:
{user_prompt}

Please extract and return a JSON object with the following structure:
{{
  "title": "Clear, concise lab title",
  "objectives": ["Specific objective 1", "Specific objective 2", ...],
  "constraints": {{
    "devices": <number of devices>,
    "time_minutes": <estimated completion time>,
    "complexity": "low|medium|high"
  }},
  "level": "CCNA|CCNP|CCIE",
  "prerequisites": ["Prerequisite 1", "Prerequisite 2", ...]
}}

Ensure objectives are:
- Specific and measurable (e.g., "Configure OSPF adjacency between R1 and R2")
- Achievable within the time constraint
- Appropriate for the target level

Return ONLY the JSON object, no additional text.
"""

REFINEMENT_PROMPT = """Review the following lab specification for completeness and clarity:

{spec_json}

Issues to check:
1. Are objectives specific and measurable?
2. Is device count appropriate for objectives?
3. Is time estimate realistic?
4. Are prerequisites necessary and sufficient?
5. Does complexity match the objectives?

If there are issues, provide a refined version of the JSON.
If the specification is good, return it unchanged.

Return ONLY the JSON object, no additional text.
"""


async def extract_exercise_spec(user_prompt: str, llm_client=None) -> ExerciseSpec:
    """
    Extract ExerciseSpec from instructor prompt using LLM reasoning.

    Args:
        user_prompt: Instructor's description of the desired lab
        llm_client: Optional LLM client (for future integration)

    Returns:
        ExerciseSpec object

    Note: For M2 MVP, this uses a simplified extraction approach.
    Future versions will implement multi-turn Q&A with ADK.
    """
    logger.info("planner_started", prompt_length=len(user_prompt))

    # For MVP: Parse simple patterns from prompt
    # In production: Use LLM with the prompts defined above
    spec = _parse_prompt_simple(user_prompt)

    logger.info(
        "planner_completed",
        title=spec.title,
        num_objectives=len(spec.objectives),
        level=spec.level,
    )

    return spec


def _parse_prompt_simple(user_prompt: str) -> ExerciseSpec:
    """
    Simple pattern-based extraction for MVP.
    In production, this will be replaced with LLM-based extraction.
    """
    prompt_lower = user_prompt.lower()

    # Extract level
    level = "CCNA"  # default
    if "ccnp" in prompt_lower:
        level = "CCNP"
    elif "ccie" in prompt_lower:
        level = "CCIE"

    # Detect lab type and generate appropriate spec
    if "static" in prompt_lower and "rout" in prompt_lower:
        return _create_static_routing_spec(user_prompt, level)
    elif "ospf" in prompt_lower:
        return _create_ospf_spec(user_prompt, level)
    elif "vlan" in prompt_lower:
        return _create_vlan_spec(user_prompt, level)
    elif "eigrp" in prompt_lower:
        return _create_eigrp_spec(user_prompt, level)
    elif "acl" in prompt_lower or "access" in prompt_lower:
        return _create_acl_spec(user_prompt, level)
    else:
        # Generic routing lab
        return _create_generic_routing_spec(user_prompt, level)


def _create_static_routing_spec(prompt: str, level: str) -> ExerciseSpec:
    """Generate spec for static routing lab."""
    # Extract device count from prompt
    device_count = 2
    if "three" in prompt.lower() or "3" in prompt:
        device_count = 3
    elif "four" in prompt.lower() or "4" in prompt:
        device_count = 4

    return ExerciseSpec(
        title="Static Routing Lab",
        objectives=[
            "Configure IP addresses on router interfaces",
            "Configure static routes between networks",
            "Verify end-to-end connectivity with ping",
            "Use show ip route to verify routing table",
        ],
        constraints={
            "devices": device_count,
            "time_minutes": 30,
            "complexity": "low",
        },
        level=level,
        prerequisites=[
            "Basic router CLI navigation",
            "IP addressing fundamentals",
            "Subnet mask notation",
        ],
    )


def _create_ospf_spec(prompt: str, level: str) -> ExerciseSpec:
    """Generate spec for OSPF lab."""
    device_count = 2
    if "three" in prompt.lower() or "3" in prompt:
        device_count = 3
    elif "four" in prompt.lower() or "4" in prompt:
        device_count = 4

    return ExerciseSpec(
        title="OSPF Basics on Two Routers",
        objectives=[
            "Configure IP addresses on router interfaces",
            "Enable OSPF process on routers",
            "Configure OSPF network statements with correct area",
            "Verify OSPF neighbor adjacency",
            "Verify OSPF routes in routing table",
            "Test inter-LAN reachability",
        ],
        constraints={
            "devices": device_count,
            "time_minutes": 45,
            "complexity": "medium",
        },
        level=level,
        prerequisites=[
            "Static routing configuration",
            "Understanding of dynamic routing protocols",
            "IP addressing and subnetting",
        ],
    )


def _create_vlan_spec(prompt: str, level: str) -> ExerciseSpec:
    """Generate spec for VLAN lab."""
    device_count = 2  # Typically 2 switches
    if "three" in prompt.lower() or "3" in prompt:
        device_count = 3

    return ExerciseSpec(
        title="Basic VLAN Configuration",
        objectives=[
            "Create VLANs on switches",
            "Assign switch ports to VLANs",
            "Configure trunk ports between switches",
            "Verify VLAN membership",
            "Test VLAN isolation",
        ],
        constraints={
            "devices": device_count,
            "time_minutes": 35,
            "complexity": "low",
        },
        level=level,
        prerequisites=[
            "Basic switch CLI navigation",
            "Understanding of Layer 2 switching",
            "VLAN concepts",
        ],
    )


def _create_eigrp_spec(prompt: str, level: str) -> ExerciseSpec:
    """Generate spec for EIGRP lab."""
    device_count = 3
    if "two" in prompt.lower() or "2" in prompt:
        device_count = 2
    elif "four" in prompt.lower() or "4" in prompt:
        device_count = 4

    return ExerciseSpec(
        title="EIGRP Configuration and Verification",
        objectives=[
            "Configure IP addresses on router interfaces",
            "Enable EIGRP autonomous system",
            "Configure EIGRP network statements",
            "Verify EIGRP neighbor relationships",
            "Analyze EIGRP topology table",
            "Verify route metrics and successors",
        ],
        constraints={
            "devices": device_count,
            "time_minutes": 50,
            "complexity": "medium",
        },
        level=level,
        prerequisites=[
            "Understanding of routing protocols",
            "OSPF configuration experience",
            "IP addressing and subnetting",
        ],
    )


def _create_acl_spec(prompt: str, level: str) -> ExerciseSpec:
    """Generate spec for ACL lab."""
    return ExerciseSpec(
        title="Access Control Lists (ACL) Configuration",
        objectives=[
            "Configure standard ACLs to filter traffic",
            "Apply ACLs to router interfaces",
            "Test ACL rules with ping and telnet",
            "Verify ACL operation with show commands",
            "Understand ACL implicit deny",
        ],
        constraints={
            "devices": 2,
            "time_minutes": 40,
            "complexity": "medium",
        },
        level=level,
        prerequisites=[
            "Understanding of IP addressing",
            "Basic router configuration",
            "TCP/IP protocol knowledge",
        ],
    )


def _create_generic_routing_spec(prompt: str, level: str) -> ExerciseSpec:
    """Generate generic routing spec when type is unclear."""
    return ExerciseSpec(
        title="Network Routing Configuration",
        objectives=[
            "Configure IP addresses on network devices",
            "Implement routing between networks",
            "Verify connectivity between all networks",
            "Use troubleshooting commands",
        ],
        constraints={
            "devices": 2,
            "time_minutes": 35,
            "complexity": "low",
        },
        level=level,
        prerequisites=[
            "Basic CLI navigation",
            "IP addressing fundamentals",
        ],
    )
