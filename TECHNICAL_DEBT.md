# Technical Debt

## Testing & Validation

### Mock Validation Output Format Mismatch
**Priority:** Medium
**Component:** `orchestrator/adk_agents/validator.py`

**Issue:**
The mock validation failure modes (`--mock-design-error`, `--mock-instruction-error`, `--mock-objectives-error`) use a hardcoded output format that doesn't match the real headless-runner output:

**Mock format (current):**
```json
{
  "success": false,
  "summary": {
    "error": "Mock INSTRUCTION validation failure",
    "details": "Lab guide contains incorrect command syntax..."
  },
  "device_outputs": {...},
  "mock": true
}
```

**Real headless-runner format:**
```json
{
  "status": "PASS" | "FAIL",
  "stats": {
    "total_steps": 10,
    "passed": 7,
    "failed": 3
  },
  "step_results": [...],
  "error_details": [...]
}
```

**Impact:**
- Mock tests don't accurately simulate real validation failures
- RCA agent may behave differently with real failures vs mocks
- Integration testing doesn't validate the full data flow

**Recommended Fix:**
Update `validator.py` lines 75-151 to generate mock failures that match the real `results.json` schema from headless-runner, including:
- Use `"status": "FAIL"` instead of `"success": false`
- Include realistic `stats` object with step counts
- Provide raw `step_results` array instead of interpreted error messages
- Let the RCA agent do the interpretation (as it does in production)

**References:**
- Real schema: `orchestrator/tools/artifacts.py:48-115`
- Mock implementation: `orchestrator/adk_agents/validator.py:75-151`
- Headless-runner results: `gs://{bucket}/{execution_id}/results.json`
