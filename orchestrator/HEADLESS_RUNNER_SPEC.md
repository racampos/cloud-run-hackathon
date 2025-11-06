# Headless Runner Modification Specification

## Problem Statement

The orchestrator's Validator agent needs to pass a GCS spec path to the headless-runner Cloud Run Job, but the Cloud Run Jobs v2 API does not reliably support command-line argument overrides during execution.

The current implementation requires:
```bash
python main.py --spec gs://bucket-name/execution-id/spec.json
```

But when the orchestrator tries to pass this via the Cloud Run API, the argument doesn't get through, causing:
```
usage: main.py [-h] --spec SPEC
main.py: error: the following arguments are required: --spec
```

## Required Changes

### 1. Update Argument Parser to Support Environment Variable Fallback

**File**: `main.py` (or wherever argparse is configured)

**Current Code** (approximate):
```python
import argparse

parser = argparse.ArgumentParser(description='Headless runner for network lab validation')
parser.add_argument('--spec', required=True, help='GCS path to spec.json file')
args = parser.parse_args()
```

**Required Change**:
```python
import argparse
import os

parser = argparse.ArgumentParser(description='Headless runner for network lab validation')
parser.add_argument(
    '--spec',
    default=os.getenv('SPEC_GCS_PATH'),
    help='GCS path to spec.json file (can also be set via SPEC_GCS_PATH env var)'
)
args = parser.parse_args()

# Validate that spec was provided via either method
if not args.spec:
    parser.error('--spec is required (via argument or SPEC_GCS_PATH environment variable)')
```

### 2. Why This Solution Works

1. **Backward compatible**: Existing calls with `--spec` argument continue to work
2. **Environment variable support**: New calls can use `SPEC_GCS_PATH` env var
3. **Cloud Run Jobs compatibility**: Environment variables CAN be overridden via the v2 API
4. **Clear error message**: Users still get helpful error if neither is provided

### 3. Orchestrator Integration

Once this change is deployed, the orchestrator's validator will pass the spec via environment variable:

```python
# In validator.py
override = run_v2.RunJobRequest.Overrides()
container_override = run_v2.RunJobRequest.Overrides.ContainerOverride()

env_var = run_v2.EnvVar()
env_var.name = "SPEC_GCS_PATH"
env_var.value = f"gs://{bucket_name}/val-{execution_id}/spec.json"
container_override.env = [env_var]

override.container_overrides = [container_override]
```

### 4. Testing

#### Test Case 1: Command-line argument (existing behavior)
```bash
python main.py --spec gs://netgenius-artifacts-dev/test-123/spec.json
# Expected: Works as before
```

#### Test Case 2: Environment variable (new behavior)
```bash
export SPEC_GCS_PATH="gs://netgenius-artifacts-dev/test-123/spec.json"
python main.py
# Expected: Works, reads from environment variable
```

#### Test Case 3: Both provided (command-line takes precedence)
```bash
export SPEC_GCS_PATH="gs://bucket1/spec.json"
python main.py --spec gs://bucket2/spec.json
# Expected: Uses gs://bucket2/spec.json (command-line argument wins)
```

#### Test Case 4: Neither provided (error)
```bash
python main.py
# Expected: Error message about missing --spec
```

#### Test Case 5: Cloud Run Job execution
```bash
gcloud run jobs execute headless-runner \
  --region=us-central1 \
  --update-env-vars="SPEC_GCS_PATH=gs://netgenius-artifacts-dev/test-123/spec.json"
# Expected: Job runs successfully with spec from env var
```

### 5. Additional Context

#### Current Cloud Run Job Configuration
- **Job Name**: `headless-runner`
- **Region**: `us-central1`
- **Project**: `netgenius-hackathon`
- **Existing Environment Variables**:
  - `GCS_BUCKET=netgenius-artifacts-dev`
  - `REGION=us-central1`

#### Spec File Format
The spec.json file contains:
```json
{
  "exercise_id": "val-1234567890",
  "topology_yaml": "...",
  "devices": {
    "r1": {
      "platform": "cisco_ios",
      "initial": ["config commands..."],
      "steps": ["lab commands..."],
      "verify": ["verification commands..."]
    }
  },
  "options": {
    "cleanup": true,
    "timeout_seconds": 300
  }
}
```

### 6. Deployment Checklist

After making the change:
- [ ] Test locally with both command-line and environment variable
- [ ] Build new Docker image
- [ ] Push to `us-central1-docker.pkg.dev/netgenius-hackathon/netgenius/headless-runner:latest`
- [ ] Deploy to Cloud Run Job (auto-deploys with `:latest` tag on next execution)
- [ ] Test with orchestrator validator

### 7. Alternative Implementation (if needed)

If you prefer more explicit control, you can use this pattern:

```python
import argparse
import os
import sys

parser = argparse.ArgumentParser(description='Headless runner for network lab validation')
parser.add_argument(
    '--spec',
    help='GCS path to spec.json file'
)
args = parser.parse_args()

# Get spec from either argument or environment variable
spec_path = args.spec or os.getenv('SPEC_GCS_PATH')

if not spec_path:
    print("Error: --spec argument or SPEC_GCS_PATH environment variable is required", file=sys.stderr)
    print("", file=sys.stderr)
    print("Usage:", file=sys.stderr)
    print("  python main.py --spec gs://bucket/path/spec.json", file=sys.stderr)
    print("  or", file=sys.stderr)
    print("  SPEC_GCS_PATH=gs://bucket/path/spec.json python main.py", file=sys.stderr)
    sys.exit(1)

# Continue with spec_path...
```

### 8. Expected Behavior After Fix

Once deployed, the orchestrator's validator agent will:
1. ✅ Upload spec.json to GCS at `gs://netgenius-artifacts-dev/val-{execution_id}/spec.json`
2. ✅ Submit Cloud Run Job with `SPEC_GCS_PATH` environment variable override
3. ✅ Headless-runner reads spec from environment variable
4. ✅ Runs validation and uploads results to GCS
5. ✅ Validator polls for completion and retrieves results

### 9. Contact

If you have questions about this specification:
- **Orchestrator code**: `/Users/rcampos/prog/AI/cloud-run-hackathon/orchestrator/adk_agents/validator.py`
- **Documentation**: `/Users/rcampos/prog/AI/cloud-run-hackathon/orchestrator/VALIDATOR_STATUS.md`
- **Test execution ID**: `val-1762470624` (spec already in GCS for testing)

### 10. Priority

**HIGH** - This is blocking the M5 completion milestone for the ADK orchestrator pipeline.

The validator agent is complete and tested, but cannot proceed past the job submission step due to this limitation.
