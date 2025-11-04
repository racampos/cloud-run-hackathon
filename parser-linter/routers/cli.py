"""CLI command linting router."""

from fastapi import APIRouter
from models.requests import LintCLIRequest
from models.responses import LintCLIResponse, CommandResult
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.post("/lint/cli", response_model=LintCLIResponse)
async def lint_cli(request: LintCLIRequest) -> LintCLIResponse:
    """
    Validate CLI command sequences.

    This is a stub implementation for M1. It always returns ok=True for all commands.
    Full implementation will validate:
    - Command syntax per device type
    - Mode transitions (stateful mode)
    - Context-aware validation
    """
    logger.info(
        "lint_cli_called",
        device_type=request.device_type,
        sequence_mode=request.sequence_mode,
        num_commands=len(request.commands),
    )

    # Stub: Return success for all commands
    results = []
    for cmd_spec in request.commands:
        result = CommandResult(
            ok=True,
            command=cmd_spec.command,
            mode_before={"type": "privileged"} if request.sequence_mode == "stateful" else None,
            mode_after={"type": "privileged"} if request.sequence_mode == "stateful" else None,
            mode=cmd_spec.mode.model_dump() if cmd_spec.mode else None,
            message="",
        )
        results.append(result)

    return LintCLIResponse(results=results, parser_version="ng-parser-2025.11.01-stub")
