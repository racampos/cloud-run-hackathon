# Validator Cloud Run Integration - Fixes Summary

## Date: 2025-11-07

##  Summary of Changes

This document summarizes all the fixes made to get the validator agent working with Cloud Run Jobs for headless network validation.

## Problem 1: Cloud Run Jobs Args with Shell Expansion

**Issue**: The Cloud Run Job definition had args with shell variable expansion syntax:
```json
"args": ["--spec", "${SPEC_GCS_PATH:-gs://netgenius-artifacts-dev/default/spec.json}"]
```

This doesn't work because container args are not processed through a shell.

**Fix**: Removed the args entirely from the job definition:
```bash
gcloud run jobs update headless-runner --region=us-central1 --args=""
```

Now the headless-runner uses its argparse default which reads from the `SPEC_GCS_PATH` environment variable.

## Problem 2: Missing Environment Variable in Job Definition

**Issue**: The Cloud Run Job needed the `SPEC_GCS_PATH` environment variable permanently set in the job definition.

**Fix**: Updated the job definition to include the environment variable:
```bash
gcloud run jobs update headless-runner --region=us-central1 \
  --set-env-vars="SPEC_GCS_PATH=gs://netgenius-artifacts-dev/pending/latest/spec.json"
```

## Problem 3: Missing Required Fields in Spec Payload

**Issue**: The headless-runner Pydantic model expects three required fields that the validator wasn't providing:
- `artifact_prefix`
- `run_id`
- `lab_id`

**Error**:
```
pydantic_core._pydantic_core.ValidationError: 3 validation errors for Spec
artifact_prefix
  Field required [type=missing]
run_id
  Field required [type=missing]
lab_id
  Field required [type=missing]
```

**Fix**: Updated `validator.py` `_convert_payload()` method to include these fields:
```python
payload = {
    "exercise_id": execution_id,
    "artifact_prefix": execution_id,  # Use execution_id as artifact prefix
    "run_id": execution_id,  # Use execution_id as run_id
    "lab_id": "validator",  # Fixed lab_id for validator runs
    "topology_yaml": design_output.get("topology_yaml", ""),
    "devices": devices,
    "options": {
        "cleanup": True,
        "timeout_seconds": 300
    }
}
```

## Problem 4: design_output Not in Session State

**Issue**: The validator agent needs `design_output` from session state, but ADK's `LlmAgent` with `output_key="design_output"` is not reliably writing it to session state before the validator runs.

**Root Cause**: The `design_output` is being extracted from event content in `main_adk.py` AFTER the entire pipeline completes, but the validator needs it DURING the pipeline execution.

**Temporary Fix**: Modified validator to skip validation gracefully if `design_output` is missing:
```python
if not draft_guide or not design_output:
    logger.warning("missing_session_state_skipping_validation", ...)
    context.session.state["validation_result"] = {
        "execution_id": "skipped",
        "success": False,
        "summary": {"error": "Validation skipped - missing required inputs"},
        "skipped": True
    }
    return
```

**Permanent Fix Needed**: Investigate why ADK's `output_key` is not working properly and ensure `design_output` is written to session state immediately after the designer agent completes.

## Problem 5: Validator Upload Location

**Issue**: The validator was uploading specs to dynamic paths like `gs://bucket/{execution_id}/spec.json`, but the job definition needed a fixed path.

**Fix**: Modified validator to upload to both locations:
- `pending/latest/spec.json` (for the job to read)
- `{execution_id}/spec.json` (for archival/debugging)

Updated in `validator.py`:
```python
pending_path = "pending/latest/spec.json"
archive_path = f"{execution_id}/spec.json"

# Upload to pending (this is what the job will read)
pending_blob = bucket.blob(pending_path)
pending_blob.upload_from_string(payload_json, content_type="application/json")

# Also archive it
archive_blob = bucket.blob(archive_path)
archive_blob.upload_from_string(payload_json, content_type="application/json")
```

## Problem 6: Unnecessary gcloud CLI Complexity

**Issue**: The validator was using `gcloud run jobs execute` with `--update-env-vars` flag, which is not needed since the env var is now in the job definition.

**Fix**: Simplified the gcloud command in `validator.py`:
```python
cmd = [
    "gcloud", "run", "jobs", "execute", self.job_name,
    "--region", self.region,
    "--format", "json"
]
```

## Current Status

### Working:
- ✅ Cloud Run Job definition has correct environment variable
- ✅ Cloud Run Job args removed (uses env var via argparse default)
- ✅ Validator uploads spec to fixed `pending/latest/spec.json` location
- ✅ Validator includes all required fields (`artifact_prefix`, `run_id`, `lab_id`)
- ✅ Validator gracefully skips if inputs are missing
- ✅ Job submission simplified (no --update-env-vars needed)

### Not Working Yet:
- ❌ `design_output` not reliably in session state when validator runs
- ❌ Validation is being skipped due to missing `design_output`
- ❌ Need to fix ADK `output_key` behavior or find alternative approach

## Next Steps

1. **Investigate ADK output_key behavior**: Understand why `LlmAgent` with `output_key="design_output"` is not writing to session state immediately.

2. **Test manual state injection**: Try explicitly writing `design_output` to session state in `main_adk.py` immediately after designer agent completes, before validator runs.

3. **Alternative approach**: Consider using `BaseAgent` for designer and author instead of `LlmAgent` to have full control over session state writes.

4. **End-to-end test**: Once `design_output` is reliably in session state, test the complete pipeline to verify validation runs successfully.

## Files Modified

1. `/Users/rcampos/prog/AI/cloud-run-hackathon/orchestrator/adk_agents/validator.py`
   - Updated `_convert_payload()` to include required fields
   - Updated `_submit_job()` to use fixed GCS location and simplified gcloud command
   - Added graceful skip if inputs missing

2. Cloud Run Job `headless-runner` (via gcloud):
   - Removed args
   - Set `SPEC_GCS_PATH` environment variable

## Testing Commands

Test Cloud Run Job manually:
```bash
gcloud run jobs execute headless-runner --region=us-central1 --wait
```

Test complete pipeline:
```bash
python main_adk.py create --prompt "Create a beginner lab to teach how to set passwords in a Cisco router, just enable and line console/vty password, include password encryption, 20 minutes"
```

Check job execution logs:
```bash
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=headless-runner" --limit=100 --format="value(textPayload,jsonPayload)"
```
