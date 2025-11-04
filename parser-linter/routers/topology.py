"""Topology linting router."""

from fastapi import APIRouter
from models.requests import LintTopologyRequest
from models.responses import LintTopologyResponse
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.post("/lint/topology", response_model=LintTopologyResponse)
async def lint_topology(request: LintTopologyRequest) -> LintTopologyResponse:
    """
    Validate network topology YAML structure.

    This is a stub implementation for M1. It always returns ok=True.
    Full implementation will validate:
    - YAML schema correctness
    - Device type validity
    - Interface naming consistency
    - Network connectivity graph
    """
    logger.info("lint_topology_called", topology_length=len(request.topology_yaml))

    # Stub: Always pass validation
    return LintTopologyResponse(ok=True, issues=[])
