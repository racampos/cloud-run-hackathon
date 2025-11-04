"""Artifact management for GCS."""

import json
from pathlib import Path
from google.cloud import storage
import structlog

logger = structlog.get_logger()


class ArtifactWriter:
    """Writes execution artifacts to Google Cloud Storage."""

    def __init__(self, bucket_name: str, exercise_id: str, build_id: str):
        """
        Initialize artifact writer.

        Args:
            bucket_name: GCS bucket name
            exercise_id: Exercise identifier
            build_id: Build identifier
        """
        self.bucket_name = bucket_name
        self.exercise_id = exercise_id
        self.build_id = build_id
        self.base_path = f"artifacts/{exercise_id}/{build_id}"

        try:
            self.client = storage.Client()
            self.bucket = self.client.bucket(bucket_name)
            logger.info(
                "artifact_writer_initialized",
                bucket=bucket_name,
                base_path=self.base_path,
            )
        except Exception as e:
            logger.warning(
                "gcs_client_init_failed",
                error=str(e),
                message="Will write artifacts locally instead",
            )
            self.client = None
            self.bucket = None

    async def write_text(self, filename: str, content: str) -> None:
        """Write text content to GCS or local filesystem."""
        path = f"{self.base_path}/{filename}"

        if self.bucket:
            try:
                blob = self.bucket.blob(path)
                blob.upload_from_string(content, content_type="text/plain")
                logger.info("artifact_written", path=path, size=len(content))
            except Exception as e:
                logger.error("artifact_write_failed", path=path, error=str(e))
                self._write_local(filename, content)
        else:
            self._write_local(filename, content)

    async def write_json(self, filename: str, data: dict) -> None:
        """Write JSON data to GCS or local filesystem."""
        content = json.dumps(data, indent=2)
        await self.write_text(filename, content)

    async def write_log(self, log_content: str) -> None:
        """Write execution log."""
        await self.write_text("execution.log", log_content)

    def _write_local(self, filename: str, content: str) -> None:
        """Fallback: write to local filesystem."""
        local_dir = Path(f"/tmp/{self.base_path}")
        local_dir.mkdir(parents=True, exist_ok=True)
        local_file = local_dir / filename
        local_file.write_text(content)
        logger.info("artifact_written_locally", path=str(local_file))
