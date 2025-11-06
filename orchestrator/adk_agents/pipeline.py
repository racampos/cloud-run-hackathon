"""Lab Creation Pipeline - ADK SequentialAgent Orchestration.

This module defines the complete lab creation workflow using ADK's
SequentialAgent to orchestrate Planner → Designer → Author → Validator.
"""

from google.adk.agents import SequentialAgent, LlmAgent
from adk_agents.planner import planner_agent
from adk_agents.designer import designer_agent
from adk_agents.author import author_agent
from adk_agents.validator import validator_agent


def create_lab_pipeline(include_validation: bool = True) -> SequentialAgent:
    """Create a lab creation pipeline.

    Args:
        include_validation: If True, includes Validator agent. If False, stops after Author.

    Returns:
        SequentialAgent pipeline
    """
    if include_validation:
        return SequentialAgent(
            name="LabCreationPipeline",
            description="End-to-end lab creation: Planner → Designer → Author → Validator",
            sub_agents=[
                planner_agent,      # Interactive Q&A → exercise_spec
                designer_agent,     # Reads exercise_spec → design_output (with linting)
                author_agent,       # Reads exercise_spec + design_output → draft_lab_guide (with linting)
                validator_agent     # Reads draft_lab_guide + design_output → validation_result
            ]
        )
    else:
        return SequentialAgent(
            name="LabCreationPipelineNoValidation",
            description="Lab creation without headless validation: Planner → Designer → Author",
            sub_agents=[
                planner_agent,
                designer_agent,
                author_agent
            ]
        )
