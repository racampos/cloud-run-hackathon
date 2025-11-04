# Headless Runner Service API Reference

**Service Type:** Cloud Run Job (Private)
**Invocation:** gcloud CLI or Cloud Run Jobs API
**Authentication:** Service Account (netgenius-orchestrator)
**Version:** v1

## Overview

The Headless Runner executes network lab simulations in an isolated, ephemeral environment. It applies configurations, runs student steps, executes verification commands, and captures complete device histories. All artifacts are written to Google Cloud Storage.

## Architecture

The Headless Runner is deployed as a **Cloud Run Job** (not a service), meaning:
- No inbound HTTP traffic
- Invoked via Cloud Run Jobs API or gcloud CLI
- Runs to completion and exits
- One execution per job instance (no concurrency)
- 2-hour maximum timeout

## Job Configuration

```yaml
Name: headless-runner
Region: us-central1
Container Image: {REGION}-docker.pkg.dev/{PROJECT}/netgenius/headless-runner:latest
Service Account: netgenius-runner@{PROJECT}.iam.gserviceaccount.com
Resources:
  Memory: 2 GiB
  CPU: 1 vCPU
  Timeout: 2h
Environment Variables:
  GCS_BUCKET: netgenius-artifacts-{env}
  REGION: us-central1
```

---

## Invocation Methods

### Method 1: Cloud Run Jobs API (Recommended for Orchestrator)

```python
from google.cloud import run_v2
import json

client = run_v2.JobsClient()

# Create execution request
request = run_v2.RunJobRequest(
    name=f"projects/{project_id}/locations/{region}/jobs/headless-runner",
    overrides=run_v2.RunJobRequest.Overrides(
        container_overrides=[
            run_v2.RunJobRequest.Overrides.ContainerOverride(
                env=[
                    run_v2.EnvVar(
                        name="PAYLOAD_JSON",
                        value=json.dumps(payload)
                    )
                ]
            )
        ]
    )
)

# Execute job
operation = client.run_job(request=request)

# Wait for completion
response = operation.result()

# Get execution name
execution_name = response.name
# Example: projects/PROJECT/locations/REGION/jobs/headless-runner/executions/EXEC_ID
```

### Method 2: gcloud CLI

```bash
# Create payload file
cat > payload.json <<EOF
{
  "exercise_id": "ex-123",
  "topology_yaml": "...",
  "devices": {...}
}
EOF

# Execute job with payload
gcloud run jobs execute headless-runner \
  --region=us-central1 \
  --set-env-vars=PAYLOAD_JSON="$(cat payload.json)" \
  --wait

# Or via args
gcloud run jobs execute headless-runner \
  --region=us-central1 \
  --args="--payload-file=/app/payload.json" \
  --wait
```

---

## Input: Job Payload

The job accepts a JSON payload via environment variable `PAYLOAD_JSON` or command-line argument.

### Payload Schema

```json
{
  "exercise_id": "ex-123",
  "build_id": "build-abc123",
  "topology_yaml": "<YAML string>",
  "devices": {
    "r1": {
      "platform": "cisco_2911",
      "initial": ["configure terminal", "hostname R1", "end"],
      "steps": [
        {"type": "cmd", "value": "configure terminal"},
        {"type": "cmd", "value": "interface GigabitEthernet0/0"},
        {"type": "cmd", "value": "ip address 10.0.0.1 255.255.255.0"},
        {"type": "verify", "value": "show ip interface brief"}
      ]
    },
    "r2": {
      "platform": "cisco_2911",
      "initial": [...],
      "steps": [...]
    }
  },
  "options": {
    "non_interactive": true,
    "timeout_seconds": 3600,
    "capture_packet_traces": false
  }
}
```

### Payload Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `exercise_id` | string | Yes | Unique exercise identifier |
| `build_id` | string | No | Build identifier (auto-generated if not provided) |
| `topology_yaml` | string | Yes | Network topology definition |
| `devices` | object | Yes | Device configurations and steps |
| `options` | object | No | Execution options |

### Device Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `platform` | string | Yes | Device platform (e.g., `cisco_2911`) |
| `initial` | array[string] | Yes | Initial configuration commands |
| `steps` | array[Step] | Yes | Lab execution steps |

### Step Object

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | `cmd` (configuration) or `verify` (verification) |
| `value` | string | Command to execute |
| `expect` | string | (Optional) Expected output pattern for verify steps |
| `timeout_seconds` | integer | (Optional) Per-step timeout (default: 30s) |

### Options Object

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `non_interactive` | boolean | true | Run without user interaction |
| `timeout_seconds` | integer | 3600 | Overall execution timeout |
| `capture_packet_traces` | boolean | false | Capture PCAP files |
| `save_snapshots` | boolean | false | Save device state snapshots |
| `continue_on_error` | boolean | false | Continue execution if a step fails |

---

## Output: Execution Artifacts

All artifacts are written to GCS at:
```
gs://{GCS_BUCKET}/artifacts/{exercise_id}/{build_id}/
```

### Artifact Structure

```
artifacts/
└── {exercise_id}/
    └── {build_id}/
        ├── summary.json              # Execution summary
        ├── execution.log             # Complete job log
        ├── topology.yaml             # Topology definition
        ├── device_histories.json     # Per-device command histories
        ├── initial_config/
        │   ├── r1.txt
        │   └── r2.txt
        ├── final_config/
        │   ├── r1.txt
        │   └── r2.txt
        └── pcap/                     # (if capture_packet_traces=true)
            ├── r1-gi0-0.pcap
            └── link-r1-r2.pcap
```

### summary.json

```json
{
  "success": true,
  "exercise_id": "ex-123",
  "build_id": "build-abc123",
  "duration_seconds": 45.2,
  "devices": ["r1", "r2"],
  "steps_executed": 24,
  "steps_passed": 24,
  "steps_failed": 0,
  "started_at": "2025-11-04T10:00:00Z",
  "completed_at": "2025-11-04T10:00:45Z",
  "simulator_version": "netgenius-sim-2.1.0",
  "errors": []
}
```

**Summary Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Overall execution success |
| `exercise_id` | string | Exercise identifier |
| `build_id` | string | Build identifier |
| `duration_seconds` | float | Total execution time |
| `devices` | array[string] | List of devices |
| `steps_executed` | integer | Total steps run |
| `steps_passed` | integer | Steps that succeeded |
| `steps_failed` | integer | Steps that failed |
| `started_at` | string (ISO 8601) | Execution start time |
| `completed_at` | string (ISO 8601) | Execution end time |
| `simulator_version` | string | Simulator version |
| `errors` | array[Error] | List of errors (if any) |

**Error Object:**
```json
{
  "device": "r1",
  "step_index": 5,
  "command": "ip address 10.0.0.1",
  "message": "% Incomplete command.",
  "severity": "error",
  "timestamp": "2025-11-04T10:00:23Z"
}
```

### device_histories.json

Complete timeline of all commands executed on each device:

```json
{
  "r1": [
    {
      "type": "initial_config",
      "command": "configure terminal",
      "output": "Enter configuration commands, one per line. End with CNTL/Z.",
      "mode_before": "privileged",
      "mode_after": "global",
      "timestamp": "2025-11-04T10:00:05.123Z",
      "duration_ms": 12
    },
    {
      "type": "cmd",
      "command": "interface GigabitEthernet0/0",
      "output": "",
      "mode_before": "global",
      "mode_after": "interface",
      "timestamp": "2025-11-04T10:00:15.456Z",
      "duration_ms": 8
    },
    {
      "type": "verify",
      "command": "show ip interface brief",
      "output": "Interface              IP-Address      OK? Method Status                Protocol\nGigabitEthernet0/0     10.0.0.1        YES manual up                    up",
      "timestamp": "2025-11-04T10:00:30.789Z",
      "duration_ms": 45
    }
  ],
  "r2": [...]
}
```

**History Entry Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | `initial_config`, `cmd`, or `verify` |
| `command` | string | Command executed |
| `output` | string | Device output |
| `mode_before` | string | CLI mode before command |
| `mode_after` | string | CLI mode after command |
| `timestamp` | string (ISO 8601) | Execution timestamp |
| `duration_ms` | integer | Command execution time |
| `success` | boolean | Whether command succeeded |

### execution.log

Structured JSON log of the entire job execution:

```
{"timestamp":"2025-11-04T10:00:00Z","level":"info","message":"job_started","exercise_id":"ex-123","build_id":"build-abc123"}
{"timestamp":"2025-11-04T10:00:01Z","level":"info","message":"topology_loaded","devices":2,"links":1}
{"timestamp":"2025-11-04T10:00:02Z","level":"info","message":"simulator_started","version":"netgenius-sim-2.1.0"}
{"timestamp":"2025-11-04T10:00:05Z","level":"info","message":"device_initialized","device":"r1","platform":"cisco_2911"}
...
{"timestamp":"2025-11-04T10:00:45Z","level":"info","message":"job_completed","success":true,"duration":45.2}
```

### initial_config/ and final_config/

Plain text configuration files for each device:

**initial_config/r1.txt:**
```
!
! Initial configuration for r1
! Generated: 2025-11-04T10:00:00Z
!
version 15.5
!
hostname R1
!
interface GigabitEthernet0/0
 ip address 10.0.0.1 255.255.255.252
 no shutdown
!
end
```

**final_config/r1.txt:**
```
!
! Final configuration for r1
! Captured: 2025-11-04T10:00:45Z
!
[Output of 'show running-config']
```

---

## Exit Codes

| Exit Code | Meaning | Description |
|-----------|---------|-------------|
| 0 | Success | All steps completed successfully |
| 1 | Execution failure | One or more steps failed |
| 2 | Configuration error | Invalid payload or topology |
| 3 | Simulator error | Simulator crashed or failed to start |
| 4 | Timeout | Execution exceeded timeout limit |
| 5 | Resource error | Insufficient resources (memory, CPU) |

---

## Monitoring Job Execution

### Get Execution Status

```python
from google.cloud import run_v2

client = run_v2.ExecutionsClient()

# Get execution details
execution = client.get_execution(
    name="projects/PROJECT/locations/REGION/jobs/headless-runner/executions/EXEC_ID"
)

# Check status
print(f"Status: {execution.completion_status}")
print(f"Started: {execution.start_time}")
print(f"Completed: {execution.completion_time}")
```

### Stream Logs

```bash
# Get execution ID from job execution
EXEC_ID=$(gcloud run jobs executions list \
  --job=headless-runner \
  --region=us-central1 \
  --limit=1 \
  --format="value(name)")

# Stream logs
gcloud logging read "resource.type=cloud_run_job
  AND resource.labels.job_name=headless-runner
  AND resource.labels.execution_name=$EXEC_ID" \
  --format=json \
  --order=asc
```

---

## Example Workflows

### Basic Execution

```python
import json
from google.cloud import run_v2, storage

# 1. Prepare payload
payload = {
    "exercise_id": "static-routing-001",
    "topology_yaml": topology_str,
    "devices": {
        "r1": {
            "platform": "cisco_2911",
            "initial": ["configure terminal", "hostname R1", "end"],
            "steps": [
                {"type": "cmd", "value": "configure terminal"},
                {"type": "cmd", "value": "ip route 192.168.2.0 255.255.255.0 10.0.0.2"},
                {"type": "verify", "value": "show ip route"}
            ]
        }
    }
}

# 2. Execute job
client = run_v2.JobsClient()
request = run_v2.RunJobRequest(
    name="projects/PROJECT/locations/REGION/jobs/headless-runner",
    overrides=run_v2.RunJobRequest.Overrides(
        container_overrides=[
            run_v2.RunJobRequest.Overrides.ContainerOverride(
                env=[run_v2.EnvVar(name="PAYLOAD_JSON", value=json.dumps(payload))]
            )
        ]
    )
)

operation = client.run_job(request=request)
response = operation.result()  # Blocks until completion

# 3. Extract build_id from execution name
execution_name = response.name
# execution_name format: projects/{project}/locations/{region}/jobs/{job}/executions/{exec_id}

# 4. Fetch artifacts
storage_client = storage.Client()
bucket = storage_client.bucket("netgenius-artifacts-dev")

summary_blob = bucket.blob(f"artifacts/{payload['exercise_id']}/{build_id}/summary.json")
summary = json.loads(summary_blob.download_as_text())

print(f"Success: {summary['success']}")
print(f"Duration: {summary['duration_seconds']}s")
```

### With Verification

```python
# Payload with verification steps
payload = {
    "exercise_id": "ospf-basic-001",
    "devices": {
        "r1": {
            "platform": "cisco_2911",
            "initial": [...],
            "steps": [
                {"type": "cmd", "value": "router ospf 1"},
                {"type": "cmd", "value": "network 10.0.0.0 0.255.255.255 area 0"},
                {"type": "verify", "value": "show ip ospf neighbor", "expect": "FULL"},
                {"type": "verify", "value": "show ip route ospf"}
            ]
        }
    },
    "options": {
        "continue_on_error": false  # Stop on first failed verify
    }
}
```

---

## Performance Characteristics

| Metric | Target | Typical |
|--------|--------|---------|
| Cold start (container init) | < 30s | ~15s |
| Simulator initialization | < 10s | ~5s |
| Device boot (per device) | < 5s | ~2s |
| Command execution | < 1s | ~100ms |
| Verify command | < 2s | ~500ms |
| Total (2-device simple lab) | < 2min | ~45s |
| Total (4-device complex lab) | < 5min | ~3min |

---

## Resource Limits

| Resource | Limit | Recommendation |
|----------|-------|----------------|
| Devices per topology | 20 | Use ≤ 10 for faster execution |
| Steps per device | 500 | Break into smaller labs if > 200 |
| Initial config commands | 1000 | Keep focused on lab objectives |
| Job timeout | 2 hours | Alert if > 10 minutes |
| Memory | 2 GiB | Request increase for > 10 devices |
| CPU | 1 vCPU | Sufficient for most topologies |

---

## Error Scenarios

### Topology Errors

```json
{
  "success": false,
  "errors": [
    {
      "message": "Invalid topology YAML: Unknown device type 'cisco_9000'",
      "severity": "error",
      "timestamp": "2025-11-04T10:00:02Z"
    }
  ]
}
```

### Configuration Errors

```json
{
  "success": false,
  "errors": [
    {
      "device": "r1",
      "step_index": 3,
      "command": "ip address 10.0.0.1",
      "message": "% Incomplete command.",
      "severity": "error"
    }
  ]
}
```

### Simulator Errors

```json
{
  "success": false,
  "errors": [
    {
      "message": "Simulator process crashed during device r2 initialization",
      "severity": "critical",
      "timestamp": "2025-11-04T10:00:15Z"
    }
  ]
}
```

---

## Best Practices

1. **Always validate with Parser-Linter first:** Catch syntax errors before expensive simulation runs.

2. **Use descriptive exercise_ids:** Include lab type and version (e.g., `ospf-basic-v2-001`).

3. **Keep initial configs minimal:** Only configure what's essential for the lab objective.

4. **Add verification steps:** Interleave `verify` steps to catch issues early.

5. **Set appropriate timeouts:** Complex labs may need > 1 hour for full execution.

6. **Monitor GCS costs:** Old artifacts are auto-deleted after 30 days (lifecycle policy).

7. **Handle failures gracefully:** Parse `summary.json` to determine if errors are blocking.

8. **Use continue_on_error cautiously:** Only for non-critical verification steps.

---

## Integration with Orchestrator

The Validator agent in the orchestrator should:

1. Submit job via Cloud Run Jobs API
2. Poll execution status or wait for completion
3. Fetch `summary.json` from GCS
4. Parse success/failure and route accordingly:
   - Success → Publisher agent
   - Failure → RCA agent for analysis

Example integration code is in `orchestrator/tools/headless_runner.py`.

---

## Changelog

### v1.0.0 (2025-11-04)
- Initial release
- Support for Cisco IOS devices
- GCS artifact storage
- Command and verification steps
- Device history capture
