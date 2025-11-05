"""Designer Agent - Creates network topology and configurations with linting."""

import structlog
from typing import Optional
from schemas import ExerciseSpec, DesignOutput
from tools import parser_linter

logger = structlog.get_logger()


DESIGNER_SYSTEM_PROMPT = """You are a network design expert specializing in creating lab topologies and configurations for Cisco networking courses.

Your role is to:
1. Design network topologies (YAML format) based on learning objectives
2. Create initial configurations (baseline setup before student work)
3. Create target configurations (expected state after lab completion)
4. Ensure all configurations are syntactically correct and will execute properly

Design principles:
- Keep topologies simple and focused on the learning objectives
- Use realistic IP addressing schemes (RFC 1918 private addresses)
- Include appropriate interface types for the platform
- Ensure initial configs establish baseline connectivity
- Target configs should demonstrate the objectives being met

Platform types:
- cisco_2911: Router with GigabitEthernet interfaces
- cisco_3560: Layer 2/3 switch
- cisco_asa: Firewall/security appliance
"""


async def create_design(
    exercise_spec: ExerciseSpec,
    llm_client=None,
    max_retries: int = 2
) -> DesignOutput:
    """
    Create network design from exercise specification.

    Args:
        exercise_spec: Learning objectives and constraints
        llm_client: Optional LLM client (for future integration)
        max_retries: Maximum number of lint-fix-retry cycles

    Returns:
        DesignOutput with topology and configs

    Raises:
        Exception if linting fails after max retries
    """
    logger.info(
        "designer_started",
        title=exercise_spec.title,
        level=exercise_spec.level,
        devices=exercise_spec.constraints.get("devices", 2),
    )

    # For MVP: Use template-based generation
    # In production: Use LLM to generate based on objectives
    topology_yaml, initial_configs, target_configs, platforms = _generate_design_template(
        exercise_spec
    )

    # Validate with linting
    for attempt in range(max_retries + 1):
        logger.info("designer_validation_attempt", attempt=attempt + 1)

        # Lint topology
        topology_result = await parser_linter.lint_topology(topology_yaml)

        if not topology_result.get("ok"):
            logger.warning(
                "topology_lint_failed",
                attempt=attempt + 1,
                issues=topology_result.get("issues", []),
            )
            if attempt < max_retries:
                # In production: Use LLM to fix issues
                # For MVP: Try to auto-fix common issues
                topology_yaml = _fix_topology_issues(topology_yaml, topology_result)
                continue
            else:
                raise Exception(
                    f"Topology validation failed after {max_retries} retries: "
                    f"{topology_result.get('issues')}"
                )

        # Lint initial configs for each device
        cli_results = {}
        all_ok = True

        for device_name, commands in initial_configs.items():
            platform = platforms[device_name]
            commands_payload = [{"command": cmd} for cmd in commands]

            cli_result = await parser_linter.lint_cli(
                device_type=platform,
                commands=commands_payload,
                sequence_mode="stateful",
                stop_on_error=False,
            )

            cli_results[device_name] = cli_result

            # Check if all commands passed
            failed_commands = [
                r for r in cli_result.get("results", []) if not r.get("ok")
            ]

            if failed_commands:
                all_ok = False
                logger.warning(
                    "cli_lint_failed",
                    device=device_name,
                    attempt=attempt + 1,
                    num_failed=len(failed_commands),
                )

        if all_ok:
            logger.info("designer_validation_passed", attempt=attempt + 1)
            break

        if attempt < max_retries:
            # Try to fix CLI issues
            initial_configs = _fix_cli_issues(
                initial_configs, cli_results, platforms
            )
        else:
            raise Exception(
                f"CLI validation failed after {max_retries} retries. "
                f"Failed devices: {[d for d, r in cli_results.items() if not all(x.get('ok') for x in r.get('results', []))]}"
            )

    design = DesignOutput(
        topology_yaml=topology_yaml,
        initial_configs=initial_configs,
        target_configs=target_configs,
        platforms=platforms,
        lint_results={
            "topology": topology_result,
            "cli": cli_results,
        },
    )

    logger.info(
        "designer_completed",
        num_devices=len(platforms),
        topology_ok=topology_result.get("ok"),
    )

    return design


def _generate_design_template(spec: ExerciseSpec) -> tuple[str, dict, dict, dict]:
    """
    Generate topology and configs from specification using templates.

    Returns:
        (topology_yaml, initial_configs, target_configs, platforms)
    """
    objectives_text = " ".join(spec.objectives).lower()
    device_count = spec.constraints.get("devices", 2)

    # Determine lab type
    if "ospf" in objectives_text:
        return _generate_ospf_design(device_count)
    elif "vlan" in objectives_text:
        return _generate_vlan_design(device_count)
    elif "eigrp" in objectives_text:
        return _generate_eigrp_design(device_count)
    elif "static" in objectives_text and "route" in objectives_text:
        return _generate_static_routing_design(device_count)
    elif "acl" in objectives_text or "access" in objectives_text:
        return _generate_acl_design()
    else:
        return _generate_static_routing_design(device_count)


def _generate_static_routing_design(device_count: int) -> tuple[str, dict, dict, dict]:
    """Generate static routing lab design."""
    if device_count == 2:
        topology_yaml = """devices:
  r1:
    type: router
    platform: cisco_2911
    interfaces:
      - name: GigabitEthernet0/0
        network: net1
      - name: GigabitEthernet0/1
        network: link1
  r2:
    type: router
    platform: cisco_2911
    interfaces:
      - name: GigabitEthernet0/0
        network: link1
      - name: GigabitEthernet0/1
        network: net2

networks:
  net1:
    subnet: 10.1.1.0/24
  link1:
    subnet: 10.0.12.0/30
  net2:
    subnet: 10.2.2.0/24
"""

        initial_configs = {
            "r1": [
                "configure terminal",
                "hostname R1",
                "interface GigabitEthernet0/0",
                "ip address 10.1.1.1 255.255.255.0",
                "no shutdown",
                "exit",
                "interface GigabitEthernet0/1",
                "ip address 10.0.12.1 255.255.255.252",
                "no shutdown",
                "exit",
                "end",
            ],
            "r2": [
                "configure terminal",
                "hostname R2",
                "interface GigabitEthernet0/0",
                "ip address 10.0.12.2 255.255.255.252",
                "no shutdown",
                "exit",
                "interface GigabitEthernet0/1",
                "ip address 10.2.2.1 255.255.255.0",
                "no shutdown",
                "exit",
                "end",
            ],
        }

        target_configs = {
            "r1": [
                "ip route 10.2.2.0 255.255.255.0 10.0.12.2",
            ],
            "r2": [
                "ip route 10.1.1.0 255.255.255.0 10.0.12.1",
            ],
        }

        platforms = {"r1": "cisco_2911", "r2": "cisco_2911"}

        return topology_yaml, initial_configs, target_configs, platforms

    else:
        # For 3+ devices, create linear topology
        # TODO: Implement multi-device topologies
        return _generate_static_routing_design(2)


def _generate_ospf_design(device_count: int) -> tuple[str, dict, dict, dict]:
    """Generate OSPF lab design."""
    topology_yaml = """devices:
  r1:
    type: router
    platform: cisco_2911
    interfaces:
      - name: GigabitEthernet0/0
        network: net1
      - name: GigabitEthernet0/1
        network: link1
  r2:
    type: router
    platform: cisco_2911
    interfaces:
      - name: GigabitEthernet0/0
        network: link1
      - name: GigabitEthernet0/1
        network: net2

networks:
  net1:
    subnet: 192.168.1.0/24
  link1:
    subnet: 10.0.12.0/30
  net2:
    subnet: 192.168.2.0/24
"""

    initial_configs = {
        "r1": [
            "configure terminal",
            "hostname R1",
            "interface GigabitEthernet0/0",
            "ip address 192.168.1.1 255.255.255.0",
            "no shutdown",
            "exit",
            "interface GigabitEthernet0/1",
            "ip address 10.0.12.1 255.255.255.252",
            "no shutdown",
            "exit",
            "end",
        ],
        "r2": [
            "configure terminal",
            "hostname R2",
            "interface GigabitEthernet0/0",
            "ip address 10.0.12.2 255.255.255.252",
            "no shutdown",
            "exit",
            "interface GigabitEthernet0/1",
            "ip address 192.168.2.1 255.255.255.0",
            "no shutdown",
            "exit",
            "end",
        ],
    }

    target_configs = {
        "r1": [
            "router ospf 1",
            "network 192.168.1.0 0.0.0.255 area 0",
            "network 10.0.12.0 0.0.0.3 area 0",
        ],
        "r2": [
            "router ospf 1",
            "network 10.0.12.0 0.0.0.3 area 0",
            "network 192.168.2.0 0.0.0.255 area 0",
        ],
    }

    platforms = {"r1": "cisco_2911", "r2": "cisco_2911"}

    return topology_yaml, initial_configs, target_configs, platforms


def _generate_vlan_design(device_count: int) -> tuple[str, dict, dict, dict]:
    """Generate VLAN lab design."""
    topology_yaml = """devices:
  sw1:
    type: switch
    platform: cisco_3560
    interfaces:
      - name: GigabitEthernet0/1
        mode: access
      - name: GigabitEthernet0/2
        mode: access
      - name: GigabitEthernet0/3
        mode: trunk
  sw2:
    type: switch
    platform: cisco_3560
    interfaces:
      - name: GigabitEthernet0/1
        mode: access
      - name: GigabitEthernet0/2
        mode: access
      - name: GigabitEthernet0/3
        mode: trunk

vlans:
  - id: 10
    name: Sales
  - id: 20
    name: Engineering
"""

    initial_configs = {
        "sw1": [
            "configure terminal",
            "hostname SW1",
            "end",
        ],
        "sw2": [
            "configure terminal",
            "hostname SW2",
            "end",
        ],
    }

    target_configs = {
        "sw1": [
            "vlan 10",
            "name Sales",
            "exit",
            "vlan 20",
            "name Engineering",
            "exit",
            "interface GigabitEthernet0/1",
            "switchport mode access",
            "switchport access vlan 10",
            "exit",
            "interface GigabitEthernet0/2",
            "switchport mode access",
            "switchport access vlan 20",
            "exit",
            "interface GigabitEthernet0/3",
            "switchport mode trunk",
        ],
        "sw2": [
            "vlan 10",
            "name Sales",
            "exit",
            "vlan 20",
            "name Engineering",
            "exit",
            "interface GigabitEthernet0/1",
            "switchport mode access",
            "switchport access vlan 10",
            "exit",
            "interface GigabitEthernet0/2",
            "switchport mode access",
            "switchport access vlan 20",
            "exit",
            "interface GigabitEthernet0/3",
            "switchport mode trunk",
        ],
    }

    platforms = {"sw1": "cisco_3560", "sw2": "cisco_3560"}

    return topology_yaml, initial_configs, target_configs, platforms


def _generate_eigrp_design(device_count: int) -> tuple[str, dict, dict, dict]:
    """Generate EIGRP lab design."""
    # Similar to OSPF but with EIGRP
    topology_yaml = """devices:
  r1:
    type: router
    platform: cisco_2911
    interfaces:
      - name: GigabitEthernet0/0
        network: net1
      - name: GigabitEthernet0/1
        network: link1
  r2:
    type: router
    platform: cisco_2911
    interfaces:
      - name: GigabitEthernet0/0
        network: link1
      - name: GigabitEthernet0/1
        network: net2

networks:
  net1:
    subnet: 172.16.1.0/24
  link1:
    subnet: 10.0.12.0/30
  net2:
    subnet: 172.16.2.0/24
"""

    initial_configs = {
        "r1": [
            "configure terminal",
            "hostname R1",
            "interface GigabitEthernet0/0",
            "ip address 172.16.1.1 255.255.255.0",
            "no shutdown",
            "exit",
            "interface GigabitEthernet0/1",
            "ip address 10.0.12.1 255.255.255.252",
            "no shutdown",
            "exit",
            "end",
        ],
        "r2": [
            "configure terminal",
            "hostname R2",
            "interface GigabitEthernet0/0",
            "ip address 10.0.12.2 255.255.255.252",
            "no shutdown",
            "exit",
            "interface GigabitEthernet0/1",
            "ip address 172.16.2.1 255.255.255.0",
            "no shutdown",
            "exit",
            "end",
        ],
    }

    target_configs = {
        "r1": [
            "router eigrp 100",
            "network 172.16.1.0 0.0.0.255",
            "network 10.0.12.0 0.0.0.3",
            "no auto-summary",
        ],
        "r2": [
            "router eigrp 100",
            "network 10.0.12.0 0.0.0.3",
            "network 172.16.2.0 0.0.0.255",
            "no auto-summary",
        ],
    }

    platforms = {"r1": "cisco_2911", "r2": "cisco_2911"}

    return topology_yaml, initial_configs, target_configs, platforms


def _generate_acl_design() -> tuple[str, dict, dict, dict]:
    """Generate ACL lab design."""
    topology_yaml = """devices:
  r1:
    type: router
    platform: cisco_2911
    interfaces:
      - name: GigabitEthernet0/0
        network: internal
      - name: GigabitEthernet0/1
        network: external

networks:
  internal:
    subnet: 192.168.10.0/24
  external:
    subnet: 203.0.113.0/24
"""

    initial_configs = {
        "r1": [
            "configure terminal",
            "hostname R1",
            "interface GigabitEthernet0/0",
            "ip address 192.168.10.1 255.255.255.0",
            "no shutdown",
            "exit",
            "interface GigabitEthernet0/1",
            "ip address 203.0.113.1 255.255.255.0",
            "no shutdown",
            "exit",
            "ip route 0.0.0.0 0.0.0.0 203.0.113.254",
            "end",
        ],
    }

    target_configs = {
        "r1": [
            "access-list 10 permit 192.168.10.0 0.0.0.255",
            "interface GigabitEthernet0/1",
            "ip access-group 10 out",
        ],
    }

    platforms = {"r1": "cisco_2911"}

    return topology_yaml, initial_configs, target_configs, platforms


def _fix_topology_issues(topology_yaml: str, lint_result: dict) -> str:
    """
    Attempt to auto-fix common topology issues.

    For MVP: Return unchanged (LLM would fix in production)
    """
    logger.warning("topology_auto_fix_not_implemented")
    return topology_yaml


def _fix_cli_issues(
    configs: dict[str, list[str]],
    lint_results: dict,
    platforms: dict,
) -> dict[str, list[str]]:
    """
    Attempt to auto-fix common CLI issues.

    For MVP: Return unchanged (LLM would fix in production)
    """
    logger.warning("cli_auto_fix_not_implemented")
    return configs
