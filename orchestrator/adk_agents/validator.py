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
        """Execute headless validation workflow.

        This is an async generator but yields nothing - just updates session state.
        """
        logger.info("validator_started")

        if not CLOUD_RUN_AVAILABLE:
            logger.error("cloud_run_not_available")
            raise ImportError(
                "Cloud Run libraries not available. Install with: "
                "pip install google-cloud-run google-auth"
            )

        # 1. Read inputs from session state or fallback to output files
        import json
        import re
        from pathlib import Path

        draft_guide = context.session.state.get("draft_lab_guide")
        design_output = context.session.state.get("design_output")

        # Fallback: Try reading from output files if not in session state
        output_dir = Path("./output")
        if not draft_guide:
            draft_file = output_dir / "draft_lab_guide.json"
            if draft_file.exists():
                try:
                    with open(draft_file) as f:
                        draft_guide = json.load(f)
                    logger.info("loaded_draft_guide_from_file", path=str(draft_file))
                except Exception as e:
                    logger.error("failed_to_load_draft_guide_from_file", error=str(e))

        if not design_output:
            design_file = output_dir / "design_output.json"
            if design_file.exists():
                try:
                    with open(design_file) as f:
                        design_output = json.load(f)
                    logger.info("loaded_design_output_from_file", path=str(design_file))
                except Exception as e:
                    logger.error("failed_to_load_design_output_from_file", error=str(e))

        if not draft_guide or not design_output:
            logger.warning(
                "missing_inputs_skipping_validation",
                has_draft_guide=bool(draft_guide),
                has_design_output=bool(design_output),
                state_keys=list(context.session.state.keys()),
                tried_file_fallback=True
            )
            # Skip validation if inputs are missing
            context.session.state["validation_result"] = {
                "execution_id": "skipped",
                "success": False,
                "summary": {
                    "error": "Validation skipped - missing required inputs (not in session state or output files)"
                },
                "skipped": True
            }
            return  # Exit early without yielding (satisfies async generator requirement)

        # Parse JSON strings if needed (agents may output JSON wrapped in markdown)
        if isinstance(draft_guide, str) and draft_guide.strip():
            try:
                # Strip markdown code fences if present
                if draft_guide.strip().startswith("```"):
                    lines = draft_guide.strip().split("\n")
                    draft_guide = "\n".join(lines[1:-1])
                draft_guide = json.loads(draft_guide)
                logger.info("parsed_draft_guide_from_string")
            except json.JSONDecodeError as e:
                logger.error("draft_guide_json_parse_error", error=str(e), content_preview=draft_guide[:200])
                # Skip validation if we can't parse
                context.session.state["validation_result"] = {
                    "execution_id": "skipped",
                    "success": False,
                    "summary": {"error": f"Failed to parse draft_guide JSON: {str(e)}"},
                    "skipped": True
                }
                return
        elif isinstance(draft_guide, dict):
            logger.info("draft_guide_already_dict")

        if isinstance(design_output, str) and design_output.strip():
            try:
                # Strip markdown code fences if present
                if design_output.strip().startswith("```"):
                    lines = design_output.strip().split("\n")
                    design_output = "\n".join(lines[1:-1])
                design_output = json.loads(design_output)
                logger.info("parsed_design_output_from_string")
            except json.JSONDecodeError as e:
                logger.error("design_output_json_parse_error", error=str(e), content_preview=design_output[:200])
                # Skip validation if we can't parse
                context.session.state["validation_result"] = {
                    "execution_id": "skipped",
                    "success": False,
                    "summary": {"error": f"Failed to parse design_output JSON: {str(e)}"},
                    "skipped": True
                }
                return
        elif isinstance(design_output, dict):
            logger.info("design_output_already_dict")

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
        logger.info("validator_polling", execution_id=execution_id)
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
        logger.info("validator_fetching_artifacts", execution_id=execution_id)
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

        # Must yield at least once to make this an async generator
        # Yield nothing to satisfy async generator requirement
        return
        yield  # This line is unreachable but makes this an async generator

    def _convert_payload(self, draft_guide: dict, design_output: dict) -> dict:
        """Convert lab guide and design to headless runner payload format.

        Args:
            draft_guide: DraftLabGuide dict from session state
            design_output: DesignOutput dict from session state

        Returns:
            Payload dict for headless runner API with flat steps array
        """
        import time

        exercise_id = f"val-{int(time.time())}"

        # Build flat steps array
        steps = []

        # Process each device section from draft guide
        for section in draft_guide.get("device_sections", []):
            device_name = section["device_name"]

            # Add initial config steps
            initial_commands = design_output.get("initial_configs", {}).get(device_name, [])
            for cmd in initial_commands:
                steps.append({
                    "type": "cli",
                    "device": device_name,
                    "text": cmd,
                    "trigger": "enter",
                    "non_interactive": True
                })

            # Add configuration steps (type="cmd")
            for step in section.get("steps", []):
                if step.get("type") == "cmd":
                    steps.append({
                        "type": "cli",
                        "device": device_name,
                        "text": step["value"],
                        "trigger": "enter",
                        "non_interactive": True
                    })

            # Add verification steps (type="verify")
            for step in section.get("steps", []):
                if step.get("type") == "verify":
                    steps.append({
                        "type": "cli",
                        "device": device_name,
                        "text": step["value"],
                        "trigger": "enter",
                        "non_interactive": True
                    })

        payload = {
            "lab_id": "validator",
            "run_id": exercise_id,
            "topology_yaml": design_output.get("topology_yaml", ""),
            "steps": steps,
            "artifact_prefix": f"gs://{self.bucket_name}/{exercise_id}"
        }

        # Store exercise_id separately for tracking
        payload["exercise_id"] = exercise_id

        return payload

    async def _submit_job(self, payload: dict):
        """Submit Cloud Run Job execution using gcloud CLI.

        The Cloud Run Jobs v2 API doesn't support execution-time env var overrides,
        so we use gcloud CLI which handles it differently.

        Args:
            payload: Headless runner payload

        Raises:
            Exception if job submission fails
        """
        from google.cloud import storage
        import json as json_lib
        import subprocess

        execution_id = payload["exercise_id"]

        # 1. Upload payload to GCS at the "pending/latest" location
        # The Cloud Run Job has SPEC_GCS_PATH=gs://bucket/pending/latest/spec.json
        credentials, _ = default()
        storage_client = storage.Client(credentials=credentials, project=self.project_id)
        bucket = storage_client.bucket(self.bucket_name)

        # Upload to both locations:
        # - pending/latest/spec.json (for the job to read)
        # - {execution_id}/spec.json (for archival/debugging)
        pending_path = "pending/latest/spec.json"
        archive_path = f"{execution_id}/spec.json"

        payload_json = json_lib.dumps(payload, indent=2)

        # Upload to pending (this is what the job will read)
        pending_blob = bucket.blob(pending_path)
        pending_blob.upload_from_string(payload_json, content_type="application/json")

        # Also archive it
        archive_blob = bucket.blob(archive_path)
        archive_blob.upload_from_string(payload_json, content_type="application/json")

        logger.info(
            "validator_payload_uploaded",
            execution_id=execution_id,
            pending_path=pending_path,
            archive_path=archive_path
        )

        # 2. Submit Cloud Run Job using gcloud CLI
        # The job definition now has SPEC_GCS_PATH permanently set to gs://bucket/pending/latest/spec.json
        # We just need to trigger the execution
        cmd = [
            "gcloud", "run", "jobs", "execute", self.job_name,
            "--region", self.region,
            "--format", "json"
        ]

        logger.info(
            "cloud_run_job_submitting",
            execution_id=execution_id,
            spec_location=f"gs://{self.bucket_name}/{pending_path}",
            command=" ".join(cmd)
        )

        # Execute gcloud command asynchronously (don't wait for completion)
        # Use asyncio.create_subprocess_exec to avoid blocking
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Wait for gcloud to submit the job (but not for job to complete)
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(
                "cloud_run_job_submit_failed",
                execution_id=execution_id,
                error=error_msg,
                returncode=process.returncode
            )
            raise Exception(f"Failed to submit Cloud Run Job: {error_msg}")

        logger.info(
            "cloud_run_job_started",
            job=self.job_name,
            execution_id=execution_id,
            spec_location=f"gs://{self.bucket_name}/{pending_path}"
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
