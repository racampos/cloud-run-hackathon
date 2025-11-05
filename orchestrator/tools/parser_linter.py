"""Tools for Parser-Linter service integration."""

import os
import httpx
import structlog

logger = structlog.get_logger()

PARSER_LINTER_URL = os.getenv(
    "PARSER_LINTER_URL", "http://localhost:8080"
)


async def lint_topology(topology_yaml: str) -> dict:
    """
    Validate network topology YAML structure.

    Args:
        topology_yaml: Raw YAML topology definition

    Returns:
        dict with 'ok' (bool) and 'issues' (list)
    """
    logger.info("calling_lint_topology", topology_length=len(topology_yaml))

    # Mock mode: Parser-linter service is not deployed yet
    if os.getenv("MOCK_LINTER", "true").lower() == "true":
        logger.info("lint_topology_mocked", mode="mock")
        # Simple validation: check if it's valid YAML
        try:
            import yaml
            yaml.safe_load(topology_yaml)
            return {"ok": True, "issues": []}
        except Exception as e:
            return {"ok": False, "issues": [{"severity": "error", "message": f"Invalid YAML: {str(e)}"}]}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{PARSER_LINTER_URL}/lint/topology",
                json={"topology_yaml": topology_yaml},
                # TODO: Add OIDC token for authentication
                # headers={"Authorization": f"Bearer {get_oidc_token()}"}
            )
            response.raise_for_status()
            result = response.json()
            logger.info("lint_topology_result", ok=result.get("ok"))
            return result
    except Exception as e:
        logger.error("lint_topology_failed", error=str(e))
        return {"ok": False, "issues": [{"severity": "error", "message": str(e)}]}


async def lint_cli(
    device_type: str,
    commands: list[dict],
    sequence_mode: str = "stateful",
    stop_on_error: bool = False,
) -> dict:
    """
    Validate CLI command sequences.

    Args:
        device_type: Device platform type (e.g., cisco_2911)
        commands: List of command dicts with 'command' key
        sequence_mode: 'stateful' or 'stateless'
        stop_on_error: Whether to stop on first error

    Returns:
        dict with 'results' (list) and 'parser_version' (str)
    """
    logger.info(
        "calling_lint_cli",
        device_type=device_type,
        sequence_mode=sequence_mode,
        num_commands=len(commands),
    )

    # Mock mode: Parser-linter service is not deployed yet
    if os.getenv("MOCK_LINTER", "true").lower() == "true":
        logger.info("lint_cli_mocked", mode="mock", num_commands=len(commands))
        # Mock: all commands pass
        return {
            "results": [{"ok": True, "command": cmd.get("command", ""), "message": "Mocked - OK"} for cmd in commands],
            "parser_version": "mock-1.0.0",
        }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{PARSER_LINTER_URL}/lint/cli",
                json={
                    "device_type": device_type,
                    "sequence_mode": sequence_mode,
                    "commands": commands,
                    "options": {"stop_on_error": stop_on_error},
                },
                # TODO: Add OIDC token for authentication
                # headers={"Authorization": f"Bearer {get_oidc_token()}"}
            )
            response.raise_for_status()
            result = response.json()

            num_ok = sum(1 for r in result.get("results", []) if r.get("ok"))
            logger.info(
                "lint_cli_result",
                total=len(result.get("results", [])),
                passed=num_ok,
            )
            return result
    except Exception as e:
        logger.error("lint_cli_failed", error=str(e))
        return {
            "results": [{"ok": False, "command": "", "message": str(e)}],
            "parser_version": "error",
        }
