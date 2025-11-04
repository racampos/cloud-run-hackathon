"""Response models for Parser-Linter API."""

from pydantic import BaseModel, Field


class Issue(BaseModel):
    """An issue found during validation."""
    severity: str = Field(..., description="Severity level (error, warning, info)")
    message: str = Field(..., description="Human-readable issue description")
    line: int | None = Field(None, description="Line number if applicable")


class LintTopologyResponse(BaseModel):
    """Response model for topology linting."""
    ok: bool = Field(..., description="True if validation passed")
    issues: list[Issue] = Field(default_factory=list, description="List of issues found")


class CommandResult(BaseModel):
    """Result of validating a single command."""
    ok: bool = Field(..., description="True if command is valid")
    command: str = Field(..., description="The command that was validated")
    mode_before: dict | None = Field(None, description="Mode before command execution")
    mode_after: dict | None = Field(None, description="Mode after command execution")
    mode: dict | None = Field(None, description="Mode for stateless validation")
    message: str = Field("", description="Error or warning message")


class LintCLIResponse(BaseModel):
    """Response model for CLI command linting."""
    results: list[CommandResult] = Field(
        ..., description="Results for each command"
    )
    parser_version: str = Field(
        default="ng-parser-2025.11.01", description="Version of the parser engine"
    )
