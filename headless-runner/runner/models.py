"""Data models for Headless Runner."""

from typing import Literal
from pydantic import BaseModel, Field


class StepSpec(BaseModel):
    """A single step in the lab execution."""
    type: Literal["cmd", "verify"] = Field(..., description="Step type")
    value: str = Field(..., description="Command or verify statement")


class DeviceSpec(BaseModel):
    """Specification for a single device."""
    platform: str = Field(..., description="Device platform (e.g., cisco_2911)")
    initial: list[str] = Field(
        default_factory=list, description="Initial configuration commands"
    )
    steps: list[StepSpec] = Field(
        default_factory=list, description="Lab execution steps"
    )


class RunnerPayload(BaseModel):
    """Complete payload for headless runner job."""
    exercise_id: str = Field(..., description="Unique exercise identifier")
    topology_yaml: str = Field(..., description="Network topology YAML")
    devices: dict[str, DeviceSpec] = Field(..., description="Device configurations")
    options: dict = Field(
        default_factory=dict, description="Additional options (e.g., non_interactive)"
    )


class ExecutionSummary(BaseModel):
    """Summary of job execution."""
    success: bool = Field(..., description="Whether execution succeeded")
    exercise_id: str = Field(..., description="Exercise identifier")
    build_id: str = Field(..., description="Build identifier")
    duration_seconds: float | None = Field(None, description="Execution duration")
    devices: list[str] = Field(default_factory=list, description="List of devices")
    error: str | None = Field(None, description="Error message if failed")
