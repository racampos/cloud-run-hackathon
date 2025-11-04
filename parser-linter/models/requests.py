"""Request models for Parser-Linter API."""

from typing import Any, Literal
from pydantic import BaseModel, Field


class LintTopologyRequest(BaseModel):
    """Request model for topology linting."""
    topology_yaml: str = Field(..., description="Raw YAML topology definition")


class ModeSpec(BaseModel):
    """Specification for a CLI mode."""
    type: Literal["user", "privileged", "global", "interface", "router", "line"] = Field(
        ..., description="Type of CLI mode"
    )
    name: str | None = Field(None, description="Context name (e.g., interface name)")


class CommandSpec(BaseModel):
    """Specification for a single CLI command."""
    command: str = Field(..., description="The CLI command to validate")
    mode: ModeSpec | None = Field(None, description="Explicit mode (for stateless mode)")


class LintCLIRequest(BaseModel):
    """Request model for CLI command linting."""
    device_type: str = Field(..., description="Device platform type (e.g., cisco_2911)")
    sequence_mode: Literal["stateful", "stateless"] = Field(
        "stateful", description="Validation mode: stateful or stateless"
    )
    start_mode: ModeSpec | None = Field(
        None, description="Starting mode for stateful validation"
    )
    commands: list[CommandSpec] = Field(..., description="List of commands to validate")
    options: dict[str, Any] = Field(
        default_factory=dict, description="Additional options (e.g., stop_on_error)"
    )
