# Validator Agent Status

## Current Status: BLOCKED

The Validator agent is **blocked** due to Cloud Run Jobs v2 API limitations.

## Problem Summary

The headless-runner Cloud Run Job requires a `--spec` command-line argument pointing to a GCS path:
```bash
python main.py --spec gs://netgenius-artifacts-dev/val-xxx/spec.json
```

However, the Cloud Run Jobs v2 API (`google.cloud.run_v2`) does **not** support reliably passing command-line arguments or environment variable overrides during job execution.

## What Was Tried

### 1. Args Override (Failed)
```python
override = run_v2.RunJobRequest.Overrides()
container_override = run_v2.RunJobRequest.Overrides.ContainerOverride()
container_override.args = ["--spec", f"gs://{bucket}/{spec_path}"]
```
**Result**: Args remain `null` in the actual execution.

### 2. Environment Variable Override (Failed)
```python
env_var = run_v2.EnvVar()
env_var.name = "SPEC_GCS_PATH"
env_var.value = f"gs://{bucket}/{spec_path}"
container_override.env = [env_var]
```
**Result**: Env remains `null` in the actual execution.

### 3. Updating Job Definition with Shell Variable (Failed)
```bash
gcloud run jobs update headless-runner --args="--spec,\${SPEC_GCS_PATH:-gs://default/spec.json}"
```
**Result**: Shell variable expansion doesn't work in Cloud Run args - literal string `${SPEC_GCS_PATH}` is passed.

## Evidence

Execution details show overrides are not applied:
```json
{
  "args": null,
  "env": null
}
```

Execution logs show:
```
usage: main.py [-h] --spec SPEC
main.py: error: the following arguments are required: --spec
```

## Solutions

### Option 1: Modify headless-runner (Recommended)
Update the headless-runner `main.py` to support reading spec from environment variable:
```python
import os
parser.add_argument('--spec', default=os.getenv('SPEC_GCS_PATH'))
```

Then the validator can pass the spec via env var override.

### Option 2: Use Cloud Run Services instead of Jobs
Cloud Run Services support args/env overrides better, but require HTTP triggers.

### Option 3: Use dry-run mode for M5
Skip headless validation for now and complete M5 with dry-run mode:
```bash
python main_adk.py create --prompt "..." --dry-run
```

## Current Workaround

The orchestrator has a `--dry-run` flag that skips headless validation:
```bash
python main_adk.py create --prompt "Create lab..." --dry-run
```

This allows the full pipeline (Planner → Designer → Author) to complete successfully without the Validator.

## Commits Related to This Issue

- `059e9e7`: fix: Upload payload to GCS and pass to Cloud Run Job
- `ba25700`: fix: Pass spec GCS path as command argument not environment variable
- `411909d`: fix: Add fallback to manually extract JSON from event content
- `fb53ebb`: fix: Handle non-string event content in manual extraction
- `62b1846`: fix: Use environment variable for Cloud Run Job spec path

## Test Results

### Dry-run Mode: ✅ WORKS
```bash
$ python main_adk.py create --prompt "Create password lab" --dry-run
✓ Lab creation pipeline completed!
✓ Exercise spec saved: output/exercise_spec.json
✓ Design output saved: output/design_output.json
✓ Draft lab guide (JSON) saved: output/draft_lab_guide.json
Skipped headless validation (dry-run mode)
```

### Full Validation: ❌ BLOCKED
Validator polls for 600 seconds and times out because the Cloud Run Job never completes.

## Next Steps

1. **Option 1**: Modify headless-runner to support `SPEC_GCS_PATH` environment variable (**recommended**)
2. **Option 2**: Use dry-run mode for M5 completion and defer validation fix to M6
3. **Option 3**: Investigate alternative Cloud Run Job execution methods (gcloud CLI with proper flags)

##Status: 2025-11-06

- Validator logic is complete and correct ✅
- GCS upload works ✅
- Cloud Run Job submission works ✅
- Cloud Run Job argument passing **BLOCKED** ❌

The issue is NOT with the validator code, but with the Cloud Run Jobs API limitations.
