"""Tools for Headless Runner job integration."""

import os
import subprocess
import json
import structlog

logger = structlog.get_logger()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "netgenius-hackathon")
REGION = os.getenv("REGION", "us-central1")
JOB_NAME = "headless-runner"


async def submit_job(payload: dict) -> dict:
    """
    Submit a headless runner Cloud Run Job.

    Args:
        payload: Runner payload with exercise_id, topology_yaml, devices, etc.

    Returns:
        dict with 'job_id' and 'status_url'
    """
    logger.info(
        "submitting_headless_job",
        exercise_id=payload.get("exercise_id"),
        num_devices=len(payload.get("devices", {})),
    )

    try:
        # For stub, we'll just log what we would do
        # In production, use Cloud Run Jobs API or gcloud

        # Simulated job submission
        job_id = f"job-{payload['exercise_id']}-stub"
        status_url = f"https://console.cloud.google.com/run/jobs/{job_id}"

        logger.info("job_submitted_stub", job_id=job_id)

        return {
            "job_id": job_id,
            "status_url": status_url,
            "status": "STUB - would execute in production",
        }

        # Production code (commented out for stub):
        # payload_json = json.dumps(payload)
        # cmd = [
        #     "gcloud", "run", "jobs", "execute", JOB_NAME,
        #     f"--region={REGION}",
        #     f"--project={PROJECT_ID}",
        #     "--wait",
        #     f"--set-env-vars=PAYLOAD_JSON={payload_json}",
        #     "--format=json",
        # ]
        #
        # result = subprocess.run(cmd, capture_output=True, text=True)
        # if result.returncode != 0:
        #     raise Exception(f"Job execution failed: {result.stderr}")
        #
        # job_info = json.loads(result.stdout)
        # return {
        #     "job_id": job_info.get("metadata", {}).get("name"),
        #     "status_url": f"https://console.cloud.google.com/run/jobs/...",
        # }

    except Exception as e:
        logger.error("job_submission_failed", error=str(e))
        return {"error": str(e), "job_id": None}


async def get_job_status(job_id: str) -> dict:
    """
    Get status of a running or completed job.

    Args:
        job_id: Job identifier

    Returns:
        dict with status information
    """
    logger.info("checking_job_status", job_id=job_id)

    # Stub: return completed
    return {
        "job_id": job_id,
        "status": "COMPLETED",
        "stub": True,
    }
