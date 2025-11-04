"""ValidationResult data model - Output from Validator agent."""

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """Result of headless validation."""

    success: bool = Field(..., description="Whether validation passed")
    exercise_id: str = Field(..., description="Exercise identifier")
    build_id: str = Field(..., description="Build identifier")
    artifact_urls: dict[str, str] = Field(
        default_factory=dict, description="URLs to GCS artifacts"
    )
    error_summary: str | None = Field(
        None, description="Summary of errors if validation failed"
    )
    duration_seconds: float | None = Field(None, description="Validation duration")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "exercise_id": "ex-123",
                "build_id": "build-abc123",
                "artifact_urls": {
                    "summary": "gs://bucket/artifacts/ex-123/build-abc123/summary.json",
                    "execution_log": "gs://bucket/artifacts/ex-123/build-abc123/execution.log",
                },
                "error_summary": None,
                "duration_seconds": 45.2,
            }
        }
