"""ExerciseSpec data model - Output from Pedagogy Planner."""

from pydantic import BaseModel, Field


class ExerciseSpec(BaseModel):
    """Specification for a lab exercise from the Pedagogy Planner."""

    title: str = Field(..., description="Lab title")
    objectives: list[str] = Field(..., description="Learning objectives")
    constraints: dict = Field(
        ..., description="Time, device count, and complexity limits"
    )
    level: str = Field(..., description="Target level (CCNA, CCNP, etc.)")
    prerequisites: list[str] = Field(
        default_factory=list, description="Required prior knowledge"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "OSPF basics on two routers",
                "objectives": [
                    "enable OSPF",
                    "adjacency up",
                    "inter-LAN reachability",
                ],
                "constraints": {"devices": 4, "time_minutes": 45},
                "level": "CCNA",
                "prerequisites": ["basic router configuration", "IP addressing"],
            }
        }
