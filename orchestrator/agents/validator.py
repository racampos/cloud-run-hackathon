"""
Validator Agent

Submits lab exercises to headless runner for validation and processes results.

Responsibilities:
- Convert DraftLabGuide to headless runner payload format
- Submit Cloud Run Job execution
- Poll job status until completion
- Fetch artifacts from GCS
- Evaluate Go/No-Go based on validation results
"""

import json
import asyncio
import time
from typing import Optional
from datetime import datetime
from google.cloud import run_v2
from google.api_core import exceptions as gcp_exceptions

from schemas import DraftLabGuide, DeviceSection
from tools.artifacts import fetch_validation_artifacts, ValidationArtifacts
import logging

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of validation execution"""

    def __init__(
        self,
        execution_id: str,
        success: bool,
        artifacts: ValidationArtifacts,
        job_name: str,
        duration_seconds: float,
    ):
        self.execution_id = execution_id
        self.success = success
        self.artifacts = artifacts
        self.job_name = job_name
        self.duration_seconds = duration_seconds

    def __str__(self):
        status = "PASS ✓" if self.success else "FAIL ✗"
        return (
            f"Validation {status}\n"
            f"  Execution ID: {self.execution_id}\n"
            f"  Duration: {self.duration_seconds:.1f}s\n"
            f"  Steps: {self.artifacts.passed_steps}/{self.artifacts.total_steps} passed"
        )


def _convert_to_runner_payload(
    draft_guide: DraftLabGuide,
    topology_yaml: str,
    initial_configs: dict[str, str],
) -> dict:
    """
    Convert DraftLabGuide to headless runner payload format.

    Headless runner expects:
    {
      "topology": "...",  # YAML string
      "initial_configs": {"R1": "...", "R2": "..."},
      "devices": [
        {
          "hostname": "R1",
          "steps": [
            {"type": "cmd", "value": "conf t", "description": "..."},
            {"type": "verify", "value": "show ip route", "description": "..."}
          ]
        }
      ]
    }
    """
    logger.info("payload_conversion_started", devices=len(draft_guide.device_sections))

    devices_payload = []
    for section in draft_guide.device_sections:
        device_dict = {
            "hostname": section.hostname,
            "steps": [
                {
                    "type": step.type,
                    "value": step.value,
                    "description": step.description,
                }
                for step in section.steps
            ],
        }
        devices_payload.append(device_dict)

    payload = {
        "topology": topology_yaml,
        "initial_configs": initial_configs,
        "devices": devices_payload,
    }

    logger.info(
        "payload_conversion_complete",
        total_devices=len(devices_payload),
        total_steps=sum(len(d["steps"]) for d in devices_payload),
    )

    return payload


async def submit_validation_job(
    job_name: str,
    payload: dict,
    project_id: str,
    region: str,
    bucket_name: str,
    timeout_seconds: int = 7200,
) -> str:
    """
    Submit Cloud Run Job for validation.

    Args:
        job_name: Name of the Cloud Run Job (e.g., "headless-runner")
        payload: Validation payload dict
        project_id: GCP project ID
        region: GCP region (e.g., "us-central1")
        bucket_name: GCS bucket for artifacts
        timeout_seconds: Max execution time (default 2 hours)

    Returns:
        execution_id: Unique ID for this execution (timestamp-based)

    The job will:
    1. Receive payload via Cloud Run Job environment variable or stdin
    2. Execute validation steps in Containerlab
    3. Upload artifacts to GCS: gs://{bucket}/{execution_id}/...
    """
    execution_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    logger.info(
        "job_submission_started",
        job_name=job_name,
        execution_id=execution_id,
        project=project_id,
    )

    # Initialize Cloud Run Jobs client
    client = run_v2.JobsClient()
    job_path = f"projects/{project_id}/locations/{region}/jobs/{job_name}"

    # Serialize payload to JSON string for environment variable
    payload_json = json.dumps(payload)

    # Create execution request with overrides
    request = run_v2.RunJobRequest(
        name=job_path,
        overrides={
            "container_overrides": [
                {
                    "env": [
                        {"name": "EXECUTION_ID", "value": execution_id},
                        {"name": "GCS_BUCKET", "value": bucket_name},
                        {"name": "VALIDATION_PAYLOAD", "value": payload_json},
                    ]
                }
            ],
            "timeout": f"{timeout_seconds}s",
        },
    )

    try:
        # Execute job (this returns immediately, doesn't wait for completion)
        operation = client.run_job(request=request)
        logger.info(
            "job_submitted",
            execution_id=execution_id,
            operation_name=operation.name,
        )

        # Note: operation.result() would block until completion
        # We'll poll separately to provide progress updates

        return execution_id

    except gcp_exceptions.GoogleAPIError as e:
        logger.error("job_submission_failed", error=str(e))
        raise RuntimeError(f"Failed to submit Cloud Run Job: {e}")


async def poll_job_status(
    execution_id: str,
    job_name: str,
    project_id: str,
    region: str,
    poll_interval: int = 10,
    max_wait_seconds: int = 7200,
) -> bool:
    """
    Poll Cloud Run Job execution status until completion.

    Args:
        execution_id: Unique execution ID
        job_name: Cloud Run Job name
        project_id: GCP project ID
        region: GCP region
        poll_interval: Seconds between status checks
        max_wait_seconds: Maximum time to wait

    Returns:
        True if job succeeded, False if failed/timeout

    Note: For MVP, we poll the job executions API. In production, we could use
    Cloud Run Jobs webhook or Pub/Sub notifications for event-driven updates.
    """
    logger.info(
        "job_polling_started",
        execution_id=execution_id,
        poll_interval=poll_interval,
    )

    client = run_v2.ExecutionsClient()
    start_time = time.time()

    # List executions for this job to find our execution
    job_path = f"projects/{project_id}/locations/{region}/jobs/{job_name}"

    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait_seconds:
            logger.error("job_polling_timeout", execution_id=execution_id, elapsed=elapsed)
            return False

        try:
            # List recent executions
            request = run_v2.ListExecutionsRequest(parent=job_path)
            executions = client.list_executions(request=request)

            # Find most recent execution (Cloud Run creates execution names with timestamps)
            # For simplicity in MVP, we assume the most recent execution is ours
            latest_execution = None
            for execution in executions:
                if latest_execution is None or execution.create_time > latest_execution.create_time:
                    latest_execution = execution

            if latest_execution:
                # Check completion status
                # Execution.succeeded_count and failed_count are populated when done
                total_tasks = latest_execution.task_count
                succeeded = latest_execution.succeeded_count
                failed = latest_execution.failed_count
                running = latest_execution.running_count

                logger.info(
                    "job_status_check",
                    execution_id=execution_id,
                    succeeded=succeeded,
                    failed=failed,
                    running=running,
                    total=total_tasks,
                    elapsed=f"{elapsed:.1f}s",
                )

                # Job is complete when all tasks are done (succeeded or failed)
                if succeeded + failed == total_tasks:
                    success = failed == 0
                    logger.info(
                        "job_completed",
                        execution_id=execution_id,
                        success=success,
                        duration=f"{elapsed:.1f}s",
                    )
                    return success

            # Wait before next poll
            await asyncio.sleep(poll_interval)

        except gcp_exceptions.GoogleAPIError as e:
            logger.error("job_polling_error", error=str(e))
            await asyncio.sleep(poll_interval)


async def validate_lab(
    draft_guide: DraftLabGuide,
    topology_yaml: str,
    initial_configs: dict[str, str],
    project_id: str = "netgenius-hackathon",
    region: str = "us-central1",
    job_name: str = "headless-runner",
    bucket_name: str = "netgenius-artifacts-dev",
) -> ValidationResult:
    """
    Main validator agent entry point.

    Orchestrates the full validation workflow:
    1. Convert DraftLabGuide to runner payload
    2. Submit Cloud Run Job
    3. Poll until completion
    4. Fetch artifacts from GCS
    5. Return Go/No-Go result

    Args:
        draft_guide: Lab guide from Author agent
        topology_yaml: Network topology (from Designer)
        initial_configs: Device initial configs (from Designer)
        project_id: GCP project
        region: GCP region
        job_name: Cloud Run Job name
        bucket_name: GCS bucket for artifacts

    Returns:
        ValidationResult with success status and artifacts
    """
    logger.info("validator_started", lab_title=draft_guide.title)
    start_time = time.time()

    # Step 1: Convert to runner payload
    payload = _convert_to_runner_payload(draft_guide, topology_yaml, initial_configs)

    # Step 2: Submit job
    execution_id = await submit_validation_job(
        job_name=job_name,
        payload=payload,
        project_id=project_id,
        region=region,
        bucket_name=bucket_name,
    )

    # Step 3: Poll until completion
    job_success = await poll_job_status(
        execution_id=execution_id,
        job_name=job_name,
        project_id=project_id,
        region=region,
    )

    if not job_success:
        raise RuntimeError(f"Cloud Run Job failed for execution {execution_id}")

    # Step 4: Fetch artifacts from GCS
    artifacts = await fetch_validation_artifacts(
        execution_id=execution_id,
        bucket_name=bucket_name,
        project_id=project_id,
    )

    duration = time.time() - start_time

    # Step 5: Evaluate Go/No-Go
    result = ValidationResult(
        execution_id=execution_id,
        success=artifacts.success,
        artifacts=artifacts,
        job_name=job_name,
        duration_seconds=duration,
    )

    logger.info(
        "validator_complete",
        execution_id=execution_id,
        success=result.success,
        duration=f"{duration:.1f}s",
    )

    return result
