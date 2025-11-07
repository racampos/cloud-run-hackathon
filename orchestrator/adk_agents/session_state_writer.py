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
        """Extract and write to session state."""

        # Skip if already in session state
        if context.session.state.get(self.output_key):
            logger.info(
                "session_state_already_exists",
                output_key=self.output_key
            )
            return  # Already there, nothing to do

        # Get input from the previous agent (this is the previous agent's output)
        if not context.input:
            logger.warning("no_input_from_previous_agent", output_key=self.output_key)
            return

        # Extract text from context.input
        text = None
        if hasattr(context.input, 'parts') and context.input.parts:
            for part in context.input.parts:
                if hasattr(part, 'text') and part.text:
                    text = part.text
                    break
        elif isinstance(context.input, str):
            text = context.input

        if not text:
            logger.warning("no_text_in_input", output_key=self.output_key)
            return

        # Try to extract JSON (handle markdown code fences)
        try:
            # First try direct JSON parse
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                # Try extracting from markdown code fence
                json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
                if json_match:
                    parsed = json.loads(json_match.group(1))
                else:
                    logger.warning("no_json_found", output_key=self.output_key)
                    return

            # Verify this is the right output type by checking for expected fields
            has_required_fields = all(field in parsed for field in self.detect_by_fields)

            if has_required_fields:
                context.session.state[self.output_key] = parsed
                logger.info(
                    "session_state_written",
                    output_key=self.output_key,
                    keys=list(parsed.keys())
                )
            else:
                logger.warning(
                    "json_missing_required_fields",
                    output_key=self.output_key,
                    expected_fields=self.detect_by_fields,
                    found_fields=list(parsed.keys())
                )

        except Exception as e:
            logger.error(
                "session_state_extraction_failed",
                output_key=self.output_key,
                error=str(e)
            )

        return  # Exit without yielding (satisfies async generator requirement)
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
