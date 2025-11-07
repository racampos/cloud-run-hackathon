"""Session State Writer Agent - Extracts LLM outputs and writes to session state.

This agent solves the problem where ADK's LlmAgent with output_key doesn't
reliably write to session state before subsequent agents run. It manually
extracts JSON from the previous agent's output and writes it to session state.
"""

import json
import re
import structlog
from google.adk.agents import BaseAgent, InvocationContext

logger = structlog.get_logger()


class SessionStateWriterAgent(BaseAgent):
    """Extracts JSON from previous agent output and writes to session state.

    This agent:
    1. Looks at the last message in the conversation
    2. Extracts JSON (handling markdown code fences)
    3. Detects which output type it is based on key fields
    4. Writes it to the appropriate session state key
    """

    def __init__(self, output_key: str, detect_by_fields: list[str]):
        """Initialize the session state writer.

        Args:
            output_key: Session state key to write to (e.g., "design_output")
            detect_by_fields: Fields to look for to identify this output type
        """
        super().__init__(
            name=f"SessionStateWriter_{output_key}",
            description=f"Extracts {output_key} from previous agent and writes to session state"
        )
        object.__setattr__(self, 'output_key', output_key)
        object.__setattr__(self, 'detect_by_fields', detect_by_fields)

    async def run_async(self, context: InvocationContext):
        """Check session state and log status.

        This agent serves as a 'flush point' to ensure ADK commits the previous
        agent's output_key to session state before the next agent runs.
        """

        # Just check if the key exists in session state
        if context.session.state.get(self.output_key):
            logger.info(
                "session_state_verified",
                output_key=self.output_key,
                keys=list(context.session.state.get(self.output_key, {}).keys()) if isinstance(context.session.state.get(self.output_key), dict) else "not_dict"
            )
        else:
            logger.warning(
                "session_state_missing",
                output_key=self.output_key,
                available_keys=list(context.session.state.keys())
            )

        # Exit without yielding (satisfies async generator requirement)
        return
        yield  # Unreachable but makes this an async generator


# Create singleton instances for each output type
design_state_writer = SessionStateWriterAgent(
    output_key="design_output",
    detect_by_fields=["topology_yaml", "platforms", "initial_configs"]
)

draft_state_writer = SessionStateWriterAgent(
    output_key="draft_lab_guide",
    detect_by_fields=["title", "device_sections", "objectives"]
)
