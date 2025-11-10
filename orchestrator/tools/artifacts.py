"""
GCS Artifact Tools

Handles reading validation artifacts from Google Cloud Storage after headless runner execution.
"""

import json
from typing import Optional
from google.cloud import storage
import logging

logger = logging.getLogger(__name__)


class ValidationArtifacts:
    """Container for validation artifacts from GCS"""

    def __init__(
        self,
        execution_id: str,
        summary: dict,
        logs: Optional[str] = None,
        device_outputs: Optional[dict] = None,
    ):
        self.execution_id = execution_id
        self.summary = summary
        self.logs = logs
        self.device_outputs = device_outputs or {}

    @property
    def success(self) -> bool:
        """Returns True if validation passed"""
        # Check both "status" field (old format) and "ok" field (current format)
        return self.summary.get("status") == "PASS" or self.summary.get("ok") is True

    @property
    def total_steps(self) -> int:
        return self.summary.get("stats", {}).get("total_steps", 0)

    @property
    def passed_steps(self) -> int:
        return self.summary.get("stats", {}).get("passed", 0)

    @property
    def failed_steps(self) -> int:
        return self.summary.get("stats", {}).get("failed", 0)


async def fetch_validation_artifacts(
    execution_id: str,
    bucket_name: str,
    project_id: str,
) -> ValidationArtifacts:
    """
    Fetch validation artifacts from GCS after headless runner completes.

    Args:
        execution_id: Unique ID for this validation run (timestamp-based)
        bucket_name: GCS bucket name (e.g., "netgenius-artifacts-dev")
        project_id: GCP project ID

    Returns:
        ValidationArtifacts with parsed summary, logs, and device outputs

    Expected GCS structure:
        {bucket}/{execution_id}/summary.json
        {bucket}/{execution_id}/execution.log
        {bucket}/{execution_id}/devices/{hostname}_output.txt
        {bucket}/{execution_id}/devices/{hostname}_final_config.txt
    """
    logger.info("artifacts_fetch_started", execution_id=execution_id, bucket=bucket_name)

    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)

    # Fetch results.json (required) - headless-runner writes results.json, not summary.json
    results_blob = bucket.blob(f"{execution_id}/results.json")
    if not results_blob.exists():
        raise FileNotFoundError(
            f"Results not found in GCS: gs://{bucket_name}/{execution_id}/results.json"
        )

    results_json = results_blob.download_as_text()
    summary = json.loads(results_json)
    logger.info("results_loaded", ok=summary.get("ok"), execution_id=execution_id)

    # Fetch execution.log (optional)
    logs = None
    log_blob = bucket.blob(f"{execution_id}/execution.log")
    if log_blob.exists():
        logs = log_blob.download_as_text()
        logger.info("logs_loaded", log_size=len(logs))

    # Fetch device outputs (optional)
    device_outputs = {}
    devices_prefix = f"{execution_id}/devices/"

    blobs = storage_client.list_blobs(bucket_name, prefix=devices_prefix)
    for blob in blobs:
        # Extract filename from path: {execution_id}/devices/{hostname}_output.txt
        filename = blob.name.split("/")[-1]
        if filename.endswith("_output.txt") or filename.endswith("_final_config.txt"):
            device_outputs[filename] = blob.download_as_text()

    logger.info(
        "artifacts_fetch_complete",
        execution_id=execution_id,
        device_files=len(device_outputs),
    )

    return ValidationArtifacts(
        execution_id=execution_id,
        summary=summary,
        logs=logs,
        device_outputs=device_outputs,
    )


async def save_artifacts_locally(
    artifacts: ValidationArtifacts,
    output_dir: str,
) -> None:
    """
    Save fetched artifacts to local filesystem for inspection.

    Args:
        artifacts: ValidationArtifacts from GCS
        output_dir: Local directory to save to
    """
    import os

    os.makedirs(output_dir, exist_ok=True)

    # Save summary
    summary_path = os.path.join(output_dir, "validation_summary.json")
    with open(summary_path, "w") as f:
        json.dump(artifacts.summary, f, indent=2)

    # Save logs if available
    if artifacts.logs:
        log_path = os.path.join(output_dir, "validation_execution.log")
        with open(log_path, "w") as f:
            f.write(artifacts.logs)

    # Save device outputs
    if artifacts.device_outputs:
        devices_dir = os.path.join(output_dir, "devices")
        os.makedirs(devices_dir, exist_ok=True)

        for filename, content in artifacts.device_outputs.items():
            device_path = os.path.join(devices_dir, filename)
            with open(device_path, "w") as f:
                f.write(content)

    logger.info("artifacts_saved_locally", output_dir=output_dir)
