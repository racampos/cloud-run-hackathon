"""Lab Creation Pipeline - ADK SequentialAgent Orchestration.

This module defines the complete lab creation workflow using ADK's
SequentialAgent to orchestrate Planner → Designer → Author → Validator.
"""

from google.adk.agents import SequentialAgent, LlmAgent, LoopAgent
from adk_agents.planner import planner_agent
from adk_agents.designer import designer_agent
from adk_agents.author import author_agent
from adk_agents.validator import validator_agent, ValidatorAgent
from adk_agents.session_state_writer import design_state_writer, draft_state_writer, SessionStateWriterAgent
from adk_agents.rca import rca_agent, patch_router_agent


def create_generation_pipeline(include_validation: bool = True, mock_mode: str = None) -> SequentialAgent:
    """Create a generation pipeline that starts from Designer.

    This pipeline assumes exercise_spec already exists in session.state
    (created by Planner in a separate interaction).

    Args:
        include_validation: If True, includes Validator agent. If False, stops after Author.
        mock_mode: Mock validation failure mode: "design", "instruction", "objectives", or None for real validation.

    Returns:
        SequentialAgent pipeline: Designer → Author → Validator (optional)
    """
    # Create validator instance (mock or real)
    validator = ValidatorAgent(mock_mode=mock_mode) if mock_mode else validator_agent

    if include_validation:
        return SequentialAgent(
            name="GenerationPipeline",
            description="Lab generation from existing exercise_spec: Designer → Author → Validator",
            sub_agents=[
                designer_agent,       # Reads exercise_spec → design_output (with linting)
                design_state_writer,  # Verify design_output in session state (flush point)
                author_agent,         # Reads exercise_spec + design_output → draft_lab_guide (with linting)
                draft_state_writer,   # Verify draft_lab_guide in session state (flush point)
                validator             # Reads draft_lab_guide + design_output → validation_result
            ]
        )
    else:
        return SequentialAgent(
            name="GenerationPipelineNoValidation",
            description="Lab generation without headless validation: Designer → Author",
            sub_agents=[
                designer_agent,
                design_state_writer,
                author_agent,
                draft_state_writer
            ]
        )


def create_lab_pipeline(include_validation: bool = True, include_rca: bool = False, mock_mode: str = None) -> SequentialAgent:
    """Create a lab creation pipeline.

    Args:
        include_validation: If True, includes Validator agent. If False, stops after Author.
        include_rca: If True, includes RCA retry loop for validation failures. Requires include_validation=True.
        mock_mode: Mock validation failure mode: "design", "instruction", "objectives", or None for real validation.

    Returns:
        SequentialAgent pipeline
    """
    # Create validator instance (mock or real)
    validator = ValidatorAgent(mock_mode=mock_mode) if mock_mode else validator_agent

    if include_validation and include_rca:
        # Create separate state writer instances for the retry loop
        # (agents can only have one parent, so we need new instances)
        retry_design_writer = SessionStateWriterAgent(
            output_key="design_output",
            detect_by_fields=["topology_yaml", "platforms", "initial_configs"]
        )
        retry_draft_writer = SessionStateWriterAgent(
            output_key="draft_lab_guide",
            detect_by_fields=["title", "device_sections", "objectives"]
        )

        # Create RCA retry loop: Validator → RCA → (Designer|Author) → Validator
        retry_loop = LoopAgent(
            name="ValidationRetryLoop",
            description="Validates lab and retries with targeted fixes on failure",
            sub_agents=[
                validator,            # Run validation → validation_result
                rca_agent,            # Analyze failure → patch_plan
                patch_router_agent,   # Route patch and trigger re-generation (or ESCALATE)
                retry_design_writer,  # Flush design_output if Designer was called
                retry_draft_writer    # Flush draft_lab_guide if Author was called
            ],
            max_iterations=3,         # Max 3 retry attempts
        )

        return SequentialAgent(
            name="LabCreationPipelineWithRCA",
            description="End-to-end lab creation with RCA retry: Planner → Designer → Author → Validator+RCA Loop",
            sub_agents=[
                planner_agent,        # Interactive Q&A → exercise_spec
                designer_agent,       # Reads exercise_spec → design_output (with linting)
                design_state_writer,  # Verify design_output in session state (flush point)
                author_agent,         # Reads exercise_spec + design_output → draft_lab_guide (with linting)
                draft_state_writer,   # Verify draft_lab_guide in session state (flush point)
                retry_loop            # Validation with RCA retry on failure
            ]
        )
    elif include_validation:
        return SequentialAgent(
            name="LabCreationPipeline",
            description="End-to-end lab creation: Planner → Designer → Author → Validator",
            sub_agents=[
                planner_agent,        # Interactive Q&A → exercise_spec
                designer_agent,       # Reads exercise_spec → design_output (with linting)
                design_state_writer,  # Verify design_output in session state (flush point)
                author_agent,         # Reads exercise_spec + design_output → draft_lab_guide (with linting)
                draft_state_writer,   # Verify draft_lab_guide in session state (flush point)
                validator             # Reads draft_lab_guide + design_output → validation_result
            ]
        )
    else:
        return SequentialAgent(
            name="LabCreationPipelineNoValidation",
            description="Lab creation without headless validation: Planner → Designer → Author",
            sub_agents=[
                planner_agent,
                designer_agent,
                design_state_writer,
                author_agent,
                draft_state_writer
            ]
        )
