# Quick Reference: Headless-Runner Fix

## TL;DR

The orchestrator validator is blocked because Cloud Run Jobs v2 API doesn't support passing command-line arguments. Fix: make headless-runner accept spec path from environment variable.

## The Change (1 line)

In `headless-runner/main.py`, change:

```python
# BEFORE
parser.add_argument('--spec', required=True, help='GCS path to spec.json')

# AFTER
parser.add_argument('--spec', default=os.getenv('SPEC_GCS_PATH'), help='GCS path to spec.json')
```

Then validate spec was provided:
```python
if not args.spec:
    parser.error('--spec required (via argument or SPEC_GCS_PATH env var)')
```

## Why This Works

- ✅ Backward compatible (--spec still works)
- ✅ Environment variables CAN be overridden via Cloud Run Jobs v2 API
- ✅ Command-line arguments CANNOT be overridden via Cloud Run Jobs v2 API

## Testing

```bash
# Test 1: Command-line (existing)
python main.py --spec gs://bucket/spec.json

# Test 2: Environment variable (new)
export SPEC_GCS_PATH="gs://bucket/spec.json"
python main.py

# Test 3: Cloud Run Job
gcloud run jobs execute headless-runner \
  --update-env-vars="SPEC_GCS_PATH=gs://bucket/spec.json"
```

## Test Data Already Available

There's a spec already uploaded for testing:
```
gs://netgenius-artifacts-dev/val-1762470624/spec.json
```

You can test immediately with:
```bash
export SPEC_GCS_PATH="gs://netgenius-artifacts-dev/val-1762470624/spec.json"
python main.py
```

## Full Documentation

- **Complete specification**: `HEADLESS_RUNNER_SPEC.md`
- **Problem analysis**: `VALIDATOR_STATUS.md`
- **Validator code**: `adk_agents/validator.py`

## Priority

**HIGH** - Blocking M5 completion for ADK orchestrator.
