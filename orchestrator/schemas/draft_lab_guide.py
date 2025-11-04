"""DraftLabGuide data model - Output from Lab Guide Author agent."""

from pydantic import BaseModel, Field


class CommandStep(BaseModel):
    """A single command or verification step."""

    type: str = Field(..., description="Step type: 'cmd' or 'verify'")
    value: str = Field(..., description="The command to execute")
    description: str = Field(default="", description="Human-readable description")


class DeviceSection(BaseModel):
    """Structured commands for a single device."""

    device_name: str = Field(..., description="Device identifier")
    platform: str = Field(..., description="Platform type (e.g., cisco_2911)")
    steps: list[CommandStep] = Field(..., description="Ordered command sequence")


class DraftLabGuide(BaseModel):
    """Draft lab guide with student instructions and structured device sections."""

    title: str = Field(..., description="Lab title")
    markdown: str = Field(..., description="Full lab guide in Markdown format")
    device_sections: list[DeviceSection] = Field(
        ..., description="Parsed per-device command sequences"
    )
    estimated_time_minutes: int = Field(
        ..., description="Estimated completion time"
    )
    lint_results: dict = Field(
        default_factory=dict, description="CLI linting results for each device"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Static Routing Lab",
                "markdown": "# Static Routing Lab\n\n## Device R1\n1. Configure interface...",
                "device_sections": [
                    {
                        "device_name": "r1",
                        "platform": "cisco_2911",
                        "steps": [
                            {
                                "type": "cmd",
                                "value": "configure terminal",
                                "description": "Enter configuration mode",
                            },
                            {
                                "type": "verify",
                                "value": "show ip interface brief",
                                "description": "Verify interfaces",
                            },
                        ],
                    }
                ],
                "estimated_time_minutes": 30,
                "lint_results": {"r1": {"ok": True, "results": []}},
            }
        }
