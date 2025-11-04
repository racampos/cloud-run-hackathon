"""DesignOutput data model - Output from Designer agent."""

from pydantic import BaseModel, Field


class DesignOutput(BaseModel):
    """Network topology and configuration design from Designer agent."""

    topology_yaml: str = Field(..., description="Network topology in YAML format")
    initial_configs: dict[str, list[str]] = Field(
        ..., description="Initial config commands per device"
    )
    target_configs: dict[str, list[str]] = Field(
        ..., description="Target/expected final config commands per device"
    )
    platforms: dict[str, str] = Field(
        ..., description="Platform type per device (e.g., cisco_2911)"
    )
    lint_results: dict = Field(
        default_factory=dict, description="Results from topology and CLI linting"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "topology_yaml": "devices:\n  r1:\n    type: router\n",
                "initial_configs": {
                    "r1": ["configure terminal", "hostname R1", "end"],
                    "r2": ["configure terminal", "hostname R2", "end"],
                },
                "target_configs": {
                    "r1": ["router ospf 1", "network 10.0.0.0 0.255.255.255 area 0"],
                    "r2": ["router ospf 1", "network 10.0.1.0 0.255.255.255 area 0"],
                },
                "platforms": {"r1": "cisco_2911", "r2": "cisco_2911"},
                "lint_results": {"topology": {"ok": True}, "cli": {"ok": True}},
            }
        }
