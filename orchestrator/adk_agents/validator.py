"""Validator Agent - ADK Custom Agent for Headless Validation.

This agent extends ADK's BaseAgent to integrate with Cloud Run Jobs for
headless network simulation validation.
"""

import os
import asyncio
import structlog
from google.adk.agents import BaseAgent, InvocationContext

# Cloud Run imports - only needed for full validation (not dry-run)
try:
    from google.cloud import run_v2
    from google.auth import default
    from tools.artifacts import fetch_validation_artifacts
    CLOUD_RUN_AVAILABLE = True
except ImportError:
    CLOUD_RUN_AVAILABLE = False

logger = structlog.get_logger()


class ValidatorAgent(BaseAgent):
    """Custom ADK agent for headless validation via Cloud Run Jobs.

    This agent:
    1. Reads draft_lab_guide and design_output from session state
    2. Converts to headless runner payload format
    3. Submits Cloud Run Job execution
    4. Polls for completion
    5. Fetches artifacts from GCS
    6. Writes validation_result to session state
    """

    def __init__(self):
        super().__init__(
            name="ValidatorAgent",
            description="Validates lab guides via headless Containerlab simulation"
        )
        # Store config as instance variables (not Pydantic fields)
        object.__setattr__(self, 'project_id', os.getenv("GCP_PROJECT_ID", "netgenius-hackathon"))
        object.__setattr__(self, 'region', os.getenv("REGION", "us-central1"))
        object.__setattr__(self, 'bucket_name', os.getenv("GCS_BUCKET", "netgenius-artifacts-dev"))
        object.__setattr__(self, 'job_name', "headless-runner")

    async def run_async(self, context: InvocationContext):
        """Execute headless validation workflow."""
        logger.info("validator_started")

        if not CLOUD_RUN_AVAILABLE:
            logger.error("cloud_run_not_available")
            raise ImportError(
                "Cloud Run libraries not available. Install with: "
                "pip install google-cloud-run google-auth"
            )

        # 1. Read inputs from session state
        draft_guide = context.session.state.get("draft_lab_guide")
        design_output = context.session.state.get("design_output")

        if not draft_guide or not design_output:
            raise ValueError(
                "Missing required inputs. Need draft_lab_guide and design_output in session state."
            )

        # 2. Convert to headless runner payload
        payload = self._convert_payload(draft_guide, design_output)
        execution_id = payload["exercise_id"]

        logger.info("validator_payload_created", execution_id=execution_id)

        # 3. Submit Cloud Run Job
        try:
            await self._submit_job(payload)
            logger.info("validator_job_submitted", execution_id=execution_id)
        except Exception as e:
            logger.error("validator_job_submit_failed", error=str(e))
            context.session.state["validation_result"] = {
                "execution_id": execution_id,
                "success": False,
                "summary": {"error": f"Job submission failed: {str(e)}"},
                "error": str(e)
            }
            return

        # 4. Poll for completion
        try:
            success = await self._poll_job(execution_id, max_wait_seconds=600)
            logger.info("validator_job_completed", execution_id=execution_id, success=success)
        except Exception as e:
            logger.error("validator_job_poll_failed", error=str(e))
            context.session.state["validation_result"] = {
                "execution_id": execution_id,
                "success": False,
                "summary": {"error": f"Job polling failed: {str(e)}"},
                "error": str(e)
            }
            return

        # 5. Fetch artifacts from GCS
        try:
            artifacts = await fetch_validation_artifacts(
                execution_id=execution_id,
                bucket_name=self.bucket_name,
                project_id=self.project_id
            )
            logger.info(
                "validator_artifacts_fetched",
                execution_id=execution_id,
                num_devices=len(artifacts.get("device_outputs", {}))
            )
        except Exception as e:
            logger.error("validator_artifacts_fetch_failed", error=str(e))
            context.session.state["validation_result"] = {
                "execution_id": execution_id,
                "success": False,
                "summary": {"error": f"Artifact fetch failed: {str(e)}"},
                "error": str(e)
            }
            return

        # 6. Write result to session state
        context.session.state["validation_result"] = {
            "execution_id": execution_id,
            "success": artifacts.get("summary", {}).get("success", False),
            "summary": artifacts.get("summary", {}),
            "device_outputs": artifacts.get("device_outputs", {}),
            "logs": artifacts.get("logs", "")
        }

        logger.info(
            "validator_completed",
            execution_id=execution_id,
            success=context.session.state["validation_result"]["success"]
        )

    def _convert_payload(self, draft_guide: dict, design_output: dict) -> dict:
        """Convert lab guide and design to headless runner payload format.

        Args:
            draft_guide: DraftLabGuide dict from session state
            design_output: DesignOutput dict from session state

        Returns:
            Payload dict for headless runner API
        """
        import time

        exercise_id = f"val-{int(time.time())}"

        # Extract device steps from draft guide
        devices = {}
        for section in draft_guide.get("device_sections", []):
            device_name = section["device_name"]
            platform = section["platform"]

            # Extract configuration commands (type="cmd")
            config_commands = [
                step["value"]
                for step in section.get("steps", [])
                if step.get("type") == "cmd"
            ]

            # Get initial config from design output
            initial_commands = design_output.get("initial_configs", {}).get(device_name, [])

            # Get verification commands (type="verify")
            verify_commands = [
                step["value"]
                for step in section.get("steps", [])
                if step.get("type") == "verify"
            ]

            devices[device_name] = {
                "platform": platform,
                "initial": initial_commands,
                "steps": config_commands,
                "verify": verify_commands
            }

        payload = {
            "exercise_id": exercise_id,
            "topology_yaml": design_output.get("topology_yaml", ""),
            "devices": devices,
            "options": {
                "cleanup": True,
                "timeout_seconds": 300
            }
        }

        return payload

    async def _submit_job(self, payload: dict):
        """Submit Cloud Run Job execution.

        Args:
            payload: Headless runner payload

        Raises:
            Exception if job submission fails
        """
        credentials, _ = default()
        client = run_v2.JobsAsyncClient(credentials=credentials)

        job_path = f"projects/{self.project_id}/locations/{self.region}/jobs/{self.job_name}"

        # Create execution request
        request = run_v2.RunJobRequest(name=job_path)

        # Execute job (non-blocking)
        operation = await client.run_job(request=request)

        logger.info(
            "cloud_run_job_started",
            job=self.job_name,
            execution_id=payload["exercise_id"]
        )

    async def _poll_job(self, execution_id: str, max_wait_seconds: int = 600) -> bool:
        """Poll for job completion by checking GCS artifacts.

        Args:
            execution_id: Execution ID to poll
            max_wait_seconds: Maximum time to wait

        Returns:
            True if job completed successfully, False otherwise
        """
        from google.cloud import storage

        credentials, _ = default()
        storage_client = storage.Client(credentials=credentials, project=self.project_id)
        bucket = storage_client.bucket(self.bucket_name)

        summary_path = f"{execution_id}/summary.json"

        poll_interval = 10  # seconds
        elapsed = 0

        while elapsed < max_wait_seconds:
            # Check if summary.json exists
            blob = bucket.blob(summary_path)
            if blob.exists():
                logger.info("validator_job_completed_detected", execution_id=execution_id)
                return True

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            logger.debug("validator_polling", execution_id=execution_id, elapsed=elapsed)

        logger.warning("validator_job_timeout", execution_id=execution_id)
        return False


# Create singleton instance for use in pipeline
validator_agent = ValidatorAgent()
