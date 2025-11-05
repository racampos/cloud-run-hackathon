# Test Validation Example

This example demonstrates how to test the Validator agent (M3) with the headless-runner service.

## Overview

The validator agent:
1. Converts a DraftLabGuide to headless runner payload format
2. Submits a Cloud Run Job execution
3. Polls until completion
4. Fetches artifacts from GCS
5. Returns Go/No-Go decision based on validation results

## Prerequisites

- Headless-runner Cloud Run Job deployed to GCP (✓ completed)
- GCS bucket `netgenius-artifacts-dev` exists
- Service account with permissions:
  - `run.jobs.run` on Cloud Run Jobs
  - `storage.objects.get` on GCS bucket

## Test Scenarios

### Scenario 1: End-to-End with Orchestrator

Run the full pipeline including validation:

```bash
cd orchestrator
python main.py create \
  --prompt "Create a basic VLAN lab with 2 switches" \
  --output ./test-output
```

This will:
- Run Planner → Designer → Author → Validator
- Submit job to headless-runner
- Wait for completion (~30-60 seconds for basic lab)
- Download validation artifacts
- Show PASS/FAIL status

### Scenario 2: Dry-Run (Skip Validation)

Test agent pipeline without headless execution:

```bash
cd orchestrator
python main.py create \
  --prompt "Create a basic VLAN lab with 2 switches" \
  --output ./test-output \
  --dry-run
```

This skips the validator and only generates:
- exercise_spec.json
- design_output.json
- draft_lab_guide.md
- draft_lab_guide.json

### Scenario 3: Direct Validator Test

Test validator with pre-generated artifacts:

```python
import asyncio
from agents import validator
from schemas import DraftLabGuide, DeviceSection, CommandStep

async def test_validator():
    # Load draft guide from previous run
    import json
    with open("test-output/draft_lab_guide.json") as f:
        guide_data = json.load(f)

    draft_guide = DraftLabGuide(**guide_data)

    # Load design artifacts
    with open("test-output/design_output.json") as f:
        design_data = json.load(f)

    # Run validation
    result = await validator.validate_lab(
        draft_guide=draft_guide,
        topology_yaml=design_data["topology_yaml"],
        initial_configs=design_data["initial_configs"],
    )

    print(f"Validation: {result}")
    print(f"Success: {result.success}")
    print(f"Steps: {result.artifacts.passed_steps}/{result.artifacts.total_steps}")

asyncio.run(test_validator())
```

## Expected Output Structure

After validation completes, artifacts are saved to:

```
test-output/
├── exercise_spec.json
├── design_output.json
├── draft_lab_guide.md
├── draft_lab_guide.json
└── validation/
    ├── validation_summary.json    # Go/No-Go decision
    ├── validation_execution.log   # Full execution log
    └── devices/
        ├── SW1_output.txt         # Device command outputs
        ├── SW1_final_config.txt   # Final device config
        ├── SW2_output.txt
        └── SW2_final_config.txt
```

## Validation Summary Format

`validation_summary.json` contains:

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
      "hostname": "SW1",
      "steps_passed": 6,
      "steps_failed": 0
    },
    {
      "hostname": "SW2",
      "steps_passed": 6,
      "steps_failed": 0
    }
  ],
  "duration_seconds": 45.3
}
```

## Troubleshooting

### Job Submission Fails

```
Error: Failed to submit Cloud Run Job: 403 Permission denied
```

**Solution:** Ensure service account has `run.jobs.run` permission:

```bash
gcloud projects add-iam-policy-binding netgenius-hackathon \
  --member="serviceAccount:netgenius-runner@netgenius-hackathon.iam.gserviceaccount.com" \
  --role="roles/run.developer"
```

### Artifacts Not Found

```
Error: Summary not found in GCS: gs://netgenius-artifacts-dev/20250104-143022/summary.json
```

**Solution:** Check headless-runner logs:

```bash
gcloud run jobs executions logs 20250104-143022 \
  --region=us-central1 \
  --project=netgenius-hackathon
```

### Timeout

```
Error: Job polling timeout after 7200s
```

**Solution:** Check if job is stuck:

```bash
gcloud run jobs executions describe <execution-name> \
  --region=us-central1 \
  --project=netgenius-hackathon
```

## Next Steps

After M3 validation is working:
- **M4: Publisher** - Convert validated labs to final format and deploy
- **LLM Integration** - Replace template-based generation with Claude API calls
- **Iterative Refinement** - Auto-fix validation failures
