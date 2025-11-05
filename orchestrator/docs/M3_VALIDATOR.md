# M3: Validator Agent - Implementation Summary

## Overview

The Validator agent completes the lab validation workflow by executing student instructions in a headless Containerlab environment and determining Go/No-Go status.

## Architecture

```
DraftLabGuide (from Author)
    ↓
Validator Agent
    ↓
Cloud Run Job (headless-runner)
    ↓
GCS Artifacts (summary.json, logs, configs)
    ↓
ValidationResult (PASS/FAIL)
```

## Components Implemented

### 1. GCS Artifact Tools (`tools/artifacts.py`)

**Purpose:** Fetch validation results from Google Cloud Storage after headless execution.

**Key Functions:**
- `fetch_validation_artifacts()` - Downloads summary.json, logs, device outputs from GCS
- `save_artifacts_locally()` - Saves artifacts to local filesystem for inspection

**ValidationArtifacts Model:**
```python
class ValidationArtifacts:
    execution_id: str
    summary: dict           # From summary.json
    logs: str              # From execution.log
    device_outputs: dict   # Device-specific outputs

    @property
    def success(self) -> bool
    @property
    def total_steps(self) -> int
    @property
    def passed_steps(self) -> int
```

**GCS Bucket Structure:**
```
gs://netgenius-artifacts-dev/
└── {execution_id}/
    ├── summary.json              # Go/No-Go status
    ├── execution.log             # Full runner logs
    └── devices/
        ├── R1_output.txt         # Command outputs
        ├── R1_final_config.txt   # Final config
        ├── R2_output.txt
        └── R2_final_config.txt
```

### 2. Validator Agent (`agents/validator.py`)

**Purpose:** Orchestrate headless validation and evaluate results.

**Main Entry Point:**
```python
async def validate_lab(
    draft_guide: DraftLabGuide,
    topology_yaml: str,
    initial_configs: dict[str, str],
    project_id: str = "netgenius-hackathon",
    region: str = "us-central1",
    job_name: str = "headless-runner",
    bucket_name: str = "netgenius-artifacts-dev",
) -> ValidationResult
```

**Workflow:**
1. **Payload Conversion** - `_convert_to_runner_payload()`
   - Transforms DraftLabGuide to headless runner JSON format
   - Includes topology YAML, initial configs, per-device steps

2. **Job Submission** - `submit_validation_job()`
   - Creates Cloud Run Job execution via Jobs API
   - Passes payload via environment variable `VALIDATION_PAYLOAD`
   - Sets execution ID (timestamp-based) for artifact tracking

3. **Status Polling** - `poll_job_status()`
   - Polls Cloud Run Executions API every 10 seconds
   - Tracks succeeded/failed/running task counts
   - Timeout after 2 hours (configurable)

4. **Artifact Retrieval** - `fetch_validation_artifacts()`
   - Downloads summary.json from GCS
   - Fetches logs and device outputs

5. **Go/No-Go Evaluation**
   - Returns `ValidationResult` with success boolean
   - Success determined by `summary.json` status field

**ValidationResult Model:**
```python
class ValidationResult:
    execution_id: str
    success: bool
    artifacts: ValidationArtifacts
    job_name: str
    duration_seconds: float
```

### 3. CLI Integration (`main.py`)

**Updated Pipeline:**
```
User Prompt
    ↓
Planner (M1) → exercise_spec.json
    ↓
Designer (M2) → topology_yaml, configs
    ↓
Author (M2) → draft_lab_guide.md/json
    ↓
Validator (M3) → validation artifacts (PASS/FAIL)
```

**New Behavior:**
- By default: Runs full pipeline including validation
- With `--dry-run`: Skips validation step
- Saves validation artifacts to `{output}/validation/`

**Example Usage:**
```bash
# Full pipeline with validation
python main.py create \
  --prompt "Create a basic VLAN lab with 2 switches" \
  --output ./my-lab

# Skip validation
python main.py create \
  --prompt "Create a basic VLAN lab" \
  --output ./my-lab \
  --dry-run
```

## Cloud Run Jobs Integration

### Job Submission

Uses Google Cloud Run Jobs API:
```python
from google.cloud import run_v2

client = run_v2.JobsClient()
request = run_v2.RunJobRequest(
    name=f"projects/{project_id}/locations/{region}/jobs/{job_name}",
    overrides={
        "container_overrides": [{
            "env": [
                {"name": "EXECUTION_ID", "value": execution_id},
                {"name": "GCS_BUCKET", "value": bucket_name},
                {"name": "VALIDATION_PAYLOAD", "value": payload_json},
            ]
        }],
        "timeout": "7200s",
    },
)
operation = client.run_job(request=request)
```

### Status Monitoring

Polls Cloud Run Executions API:
```python
client = run_v2.ExecutionsClient()
request = run_v2.ListExecutionsRequest(
    parent=f"projects/{project_id}/locations/{region}/jobs/{job_name}"
)
executions = client.list_executions(request=request)

# Check latest execution
execution.succeeded_count  # Completed successfully
execution.failed_count     # Failed tasks
execution.running_count    # Still running
```

## Headless Runner Payload Format

The validator converts DraftLabGuide to this format:

```json
{
  "topology": "devices:\n  R1:\n    kind: cisco_2911\n...",
  "initial_configs": {
    "R1": "hostname R1\n...",
    "R2": "hostname R2\n..."
  },
  "devices": [
    {
      "hostname": "R1",
      "steps": [
        {
          "type": "cmd",
          "value": "configure terminal",
          "description": "Enter config mode"
        },
        {
          "type": "verify",
          "value": "show ip interface brief",
          "description": "Verify interfaces"
        }
      ]
    }
  ]
}
```

## Validation Summary Format

The headless runner produces this summary.json:

```json
{
  "status": "PASS",
  "execution_id": "20250104-143022",
  "stats": {
    "total_steps": 12,
    "passed": 12,
    "failed": 0
  },
  "devices": [
    {
      "hostname": "R1",
      "steps_passed": 6,
      "steps_failed": 0
    }
  ],
  "duration_seconds": 45.3,
  "errors": []
}
```

## Error Handling

**Job Submission Failures:**
- Missing permissions: Check service account has `run.jobs.run`
- Image not found: Verify headless-runner image in Artifact Registry
- Invalid payload: Check JSON serialization

**Polling Timeouts:**
- Default: 2 hours (7200s)
- Configurable via `max_wait_seconds` parameter
- Consider Cloud Run Jobs max timeout (24 hours)

**Artifact Retrieval:**
- Missing summary.json: Job may have failed, check logs
- GCS permissions: Service account needs `storage.objects.get`
- Malformed JSON: Headless runner bug, check execution logs

## Dependencies

**Python Packages:**
```
google-cloud-run
google-cloud-storage
pydantic
structlog
```

**GCP Resources:**
- Cloud Run Job: `headless-runner` (deployed in M1)
- GCS Bucket: `netgenius-artifacts-dev`
- Service Account: `netgenius-runner@{project}.iam.gserviceaccount.com`

**IAM Permissions:**
```
Service Account: netgenius-runner
- roles/run.developer (submit and monitor jobs)
- roles/storage.objectAdmin (write artifacts to GCS)

Orchestrator (local/Cloud Shell):
- roles/run.developer (submit jobs)
- roles/storage.objectViewer (read artifacts from GCS)
```

## Testing

See `examples/test-validation/README.md` for:
- End-to-end testing instructions
- Dry-run examples
- Direct validator API usage
- Troubleshooting common issues

## Known Limitations (MVP)

1. **No Retry Logic:** Failed validations are not automatically retried
2. **Single Job Tracking:** Assumes latest execution is the one we submitted
3. **Synchronous Polling:** Uses sleep-based polling instead of webhooks/Pub/Sub
4. **No Partial Success:** Validation is binary PASS/FAIL
5. **Template-Based Generation:** Parser-linter integration requires deployment

## Next Steps: M4 - Publisher

After validation passes:
- Convert validated lab to final student format
- Package artifacts for LMS/platform deployment
- Generate instructor notes with solution configs
- Publish to content repository

## Version

**Current:** 0.3.0-m3 (M3: Headless Validation)

**Agents Status:**
- Planner ✓
- Designer ✓
- Author ✓
- Validator ✓
- Publisher (pending)
