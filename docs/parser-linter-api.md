# Parser-Linter Service API Reference

**Service Type:** Cloud Run Service (Private)
**Base URL:** `https://parser-linter-{hash}-uc.a.run.app`
**Authentication:** OIDC (Cloud Run service-to-service)
**Version:** v1

## Overview

The Parser-Linter service provides fast, stateless validation of network topology definitions and CLI command sequences. It mirrors Cisco IOS CLI behavior to catch syntax errors, mode transition issues, and topology problems before expensive simulation runs.

## Authentication

All requests require an OIDC identity token in the Authorization header:

```bash
Authorization: Bearer {OIDC_TOKEN}
```

Only the `netgenius-orchestrator` service account is authorized to invoke this service.

## Endpoints

### Health Check

**GET** `/health`

Returns service health status.

**Response:**
```json
{
  "status": "healthy",
  "service": "parser-linter",
  "version": "1.0.0",
  "uptime_seconds": 3600
}
```

---

### Validate Topology

**POST** `/lint/topology`

Validates network topology YAML structure, device types, and connectivity.

**Request Body:**
```json
{
  "topology_yaml": "string"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `topology_yaml` | string | Yes | Raw YAML topology definition |

**Response:**
```json
{
  "ok": true,
  "issues": [],
  "metadata": {
    "device_count": 4,
    "link_count": 3,
    "validation_time_ms": 145
  }
}
```

**Response (with errors):**
```json
{
  "ok": false,
  "issues": [
    {
      "severity": "error",
      "message": "Unknown device type: cisco_3850",
      "line": 5,
      "device": "sw1"
    },
    {
      "severity": "warning",
      "message": "Interface GigabitEthernet0/24 not defined on device r1",
      "line": 12,
      "device": "r1"
    }
  ],
  "metadata": {
    "device_count": 4,
    "link_count": 3,
    "validation_time_ms": 89
  }
}
```

**Issue Object:**
| Field | Type | Description |
|-------|------|-------------|
| `severity` | string | `error`, `warning`, or `info` |
| `message` | string | Human-readable description |
| `line` | integer | Line number in YAML (if applicable) |
| `device` | string | Device name (if applicable) |

**Topology YAML Schema:**
```yaml
devices:
  <device_name>:
    type: router | switch | host
    platform: cisco_2911 | cisco_3750 | cisco_iosv | ubuntu_20_04

links:
  - [device1, interface1, device2, interface2]

networks:
  <network_name>:
    subnet: "10.0.0.0/24"
    devices:
      - device: <device_name>
        interface: <interface_name>
        ip: "10.0.0.1"
```

**Validation Rules:**
- Device types must be one of: `router`, `switch`, `host`
- Platform types must be supported (see list above)
- All devices referenced in links must be defined
- Interface names must match platform conventions
- No duplicate interface assignments
- Network subnets must be valid CIDR notation

---

### Validate CLI Commands

**POST** `/lint/cli`

Validates CLI command sequences with stateful or stateless mode tracking.

**Request Body:**
```json
{
  "device_type": "cisco_2911",
  "sequence_mode": "stateful",
  "start_mode": {
    "type": "privileged"
  },
  "commands": [
    {"command": "configure terminal"},
    {"command": "interface GigabitEthernet0/0"},
    {"command": "ip address 10.0.0.1 255.255.255.0"}
  ],
  "options": {
    "stop_on_error": false
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_type` | string | Yes | Platform type (e.g., `cisco_2911`) |
| `sequence_mode` | string | No | `stateful` (default) or `stateless` |
| `start_mode` | object | No | Starting CLI mode (default: privileged exec) |
| `commands` | array | Yes | List of command objects |
| `options` | object | No | Validation options |

**Command Object (Stateful Mode):**
```json
{
  "command": "configure terminal"
}
```

**Command Object (Stateless Mode):**
```json
{
  "command": "hostname R1",
  "mode": {
    "type": "global"
  }
}
```

**Mode Object:**
| Field | Type | Description |
|-------|------|-------------|
| `type` | string | `user`, `privileged`, `global`, `interface`, `router`, `line`, `vlan` |
| `name` | string | Context name (e.g., `GigabitEthernet0/0` for interface mode) |

**Options Object:**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `stop_on_error` | boolean | false | Stop validation on first error |

**Response:**
```json
{
  "results": [
    {
      "ok": true,
      "command": "configure terminal",
      "mode_before": {"type": "privileged"},
      "mode_after": {"type": "global"},
      "message": ""
    },
    {
      "ok": true,
      "command": "interface GigabitEthernet0/0",
      "mode_before": {"type": "global"},
      "mode_after": {"type": "interface", "name": "GigabitEthernet0/0"},
      "message": ""
    },
    {
      "ok": false,
      "command": "ip address 10.0.0.1",
      "mode_before": {"type": "interface", "name": "GigabitEthernet0/0"},
      "mode_after": {"type": "interface", "name": "GigabitEthernet0/0"},
      "message": "% Incomplete command."
    }
  ],
  "parser_version": "ng-parser-2025.11.01"
}
```

**Result Object:**
| Field | Type | Description |
|-------|------|-------------|
| `ok` | boolean | Whether command is valid |
| `command` | string | The command that was validated |
| `mode_before` | object | CLI mode before command execution (stateful) |
| `mode_after` | object | CLI mode after command execution (stateful) |
| `mode` | object | CLI mode for command (stateless) |
| `message` | string | Error message if validation failed |

---

## Supported Device Types

| Platform | Type | Description |
|----------|------|-------------|
| `cisco_2911` | Router | Cisco 2911 ISR (IOS) |
| `cisco_3750` | Switch | Cisco 3750 Switch (IOS) |
| `cisco_iosv` | Router | Cisco IOSv Virtual Router |
| `cisco_iosvl2` | Switch | Cisco IOSvL2 Virtual Switch |
| `cisco_csr1000v` | Router | Cisco CSR 1000v |

---

## CLI Mode Types

| Mode Type | Description | Prompt Example |
|-----------|-------------|----------------|
| `user` | User EXEC mode | `Router>` |
| `privileged` | Privileged EXEC mode | `Router#` |
| `global` | Global configuration mode | `Router(config)#` |
| `interface` | Interface configuration mode | `Router(config-if)#` |
| `router` | Router configuration mode | `Router(config-router)#` |
| `line` | Line configuration mode | `Router(config-line)#` |
| `vlan` | VLAN configuration mode | `Router(config-vlan)#` |

---

## Stateful vs. Stateless Validation

### Stateful Mode (Default)

The linter tracks mode transitions as commands execute sequentially:

```json
{
  "sequence_mode": "stateful",
  "commands": [
    {"command": "configure terminal"},
    {"command": "interface GigabitEthernet0/0"},
    {"command": "ip address 10.0.0.1 255.255.255.0"},
    {"command": "no shutdown"},
    {"command": "exit"},
    {"command": "exit"}
  ]
}
```

**Use cases:**
- Validating complete configuration scripts
- Checking InitialConfig sequences from Designer
- Validating Draft Lab Guide device sections from Author

### Stateless Mode

Each command is validated independently with explicit mode context:

```json
{
  "sequence_mode": "stateless",
  "commands": [
    {
      "command": "hostname R1",
      "mode": {"type": "global"}
    },
    {
      "command": "ip address 10.0.0.1 255.255.255.0",
      "mode": {"type": "interface", "name": "GigabitEthernet0/0"}
    }
  ]
}
```

**Use cases:**
- Validating individual commands from different contexts
- Granular error bucketing by mode type
- Parallel validation of independent command sets

---

## Error Handling

**HTTP Status Codes:**
- `200` - Validation completed (check `ok` field in response)
- `400` - Invalid request (malformed JSON, missing required fields)
- `401` - Unauthorized (invalid or missing OIDC token)
- `403` - Forbidden (service account not authorized)
- `500` - Internal server error

**Error Response:**
```json
{
  "error": "Invalid request",
  "detail": "Field 'device_type' is required",
  "code": "INVALID_REQUEST"
}
```

---

## Performance Characteristics

| Operation | Target | Typical |
|-----------|--------|---------|
| Topology validation | < 1s | ~200ms |
| CLI validation (50 cmds) | < 2s | ~500ms |
| CLI validation (200 cmds) | < 3s | ~1.5s |
| Cold start | < 5s | ~2s |

---

## Example Usage

### Python (with httpx)

```python
import httpx
from google.auth.transport.requests import Request
from google.oauth2 import id_token

# Get OIDC token
target_audience = "https://parser-linter-{hash}-uc.a.run.app"
token = id_token.fetch_id_token(Request(), target_audience)

# Validate topology
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"{target_audience}/lint/topology",
        json={"topology_yaml": topology_str},
        headers={"Authorization": f"Bearer {token}"}
    )
    result = response.json()
    print(f"Topology valid: {result['ok']}")

# Validate CLI commands
    response = await client.post(
        f"{target_audience}/lint/cli",
        json={
            "device_type": "cisco_2911",
            "sequence_mode": "stateful",
            "commands": [
                {"command": "configure terminal"},
                {"command": "hostname R1"}
            ]
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    result = response.json()
    errors = [r for r in result['results'] if not r['ok']]
    print(f"Found {len(errors)} errors")
```

### cURL

```bash
# Get OIDC token
TOKEN=$(gcloud auth print-identity-token)

# Validate topology
curl -X POST https://parser-linter-{hash}-uc.a.run.app/lint/topology \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topology_yaml": "devices:\n  r1:\n    type: router\n    platform: cisco_2911"
  }'

# Validate CLI
curl -X POST https://parser-linter-{hash}-uc.a.run.app/lint/cli \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_type": "cisco_2911",
    "commands": [{"command": "configure terminal"}]
  }'
```

---

## Rate Limits

- **Requests per minute:** 300 per service account
- **Concurrent requests:** 50 per service account
- **Payload size:** Max 1MB per request
- **Commands per request:** Max 500 commands

---

## Best Practices

1. **Use stateful mode for sequences:** When validating complete configuration scripts, use stateful mode to catch mode transition errors.

2. **Batch commands:** Send up to 200-300 commands per request for optimal performance.

3. **Set stop_on_error=false:** Surface all issues in one pass rather than iterating.

4. **Cache results:** Lint results for identical command sequences can be cached.

5. **Handle partial failures gracefully:** A linting error doesn't necessarily mean the lab is broken - use the severity field to determine if it's blocking.

---

## Changelog

### v1.0.0 (2025-11-04)
- Initial API release
- Stateful and stateless CLI validation
- Topology validation
- Support for Cisco IOS devices
