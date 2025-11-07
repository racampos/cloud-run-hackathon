"""PatchPlan Schema - RCA output for targeted fixes."""

from pydantic import BaseModel, Field
from typing import Literal


class PatchPlan(BaseModel):
    """Patch plan from RCA agent for fixing validation failures.

    This schema captures the root cause analysis and routing information
    for targeted fixes to be applied by the appropriate agent.
    """

    root_cause_type: Literal["DESIGN", "INSTRUCTION", "OBJECTIVES"] = Field(
        ...,
        description="Classification of the root cause: DESIGN (topology/config), INSTRUCTION (lab guide), or OBJECTIVES (spec)"
    )

    analysis: str = Field(
        ...,
        description="Detailed explanation of what went wrong and why, including evidence from validation logs"
    )

    target_agent: Literal["designer", "author", "planner"] = Field(
        ...,
        description="Which agent should fix the issue: designer, author, or planner"
    )

    patch_instructions: str = Field(
        ...,
        description="Specific, actionable guidance for the target agent to fix the issue"
    )

    should_retry: bool = Field(
        ...,
        description="Whether to retry after patching (true) or escalate to human (false)"
    )

    confidence: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="Confidence level in the root cause analysis"
    )
