# NetGenius Implementation Plan

**Version:** 1.0
**Date:** 2025-11-04
**Status:** Ready for Implementation
**Timeline:** 7 days (Hackathon cadence)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Milestone Breakdown](#4-milestone-breakdown)
5. [Component Implementation Details](#5-component-implementation-details)
6. [Data Flow & Integration](#6-data-flow--integration)
7. [Deployment Strategy](#7-deployment-strategy)
8. [Testing Strategy](#8-testing-strategy)
9. [Risk Mitigation](#9-risk-mitigation)
10. [Success Metrics](#10-success-metrics)

---

## 1. Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Orchestrator (ADK)                         │
│  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌──────────────┐     │
│  │ Planner  │→ │ Designer │→ │ Author │→ │  Validator   │→    │
│  └──────────┘  └──────────┘  └────────┘  └──────────────┘│    │
│                      ↓            ↓              ↓         │    │
│                 ┌────────────────────────────────┐        │    │
│                 │     Tool Registry              │        │    │
│                 │  - parser_linter.topology      │        │    │
│                 │  - parser_linter.cli           │        │    │
│                 │  - headless_runner.submit_job  │        │    │
│                 │  - artifacts.read              │        │    │
│                 │  - publisher.publish           │        │    │
│                 └────────────────────────────────┘        │    │
│                      ↓                    ↓               │    │
└──────────────────────┼────────────────────┼───────────────┘    │
                       │                    │                     │
         ┌─────────────┘                    └──────────────┐     │
         ↓                                                  ↓     │
┌─────────────────────┐                        ┌──────────────────┐
│ Parser-Linter Svc   │                        │ Headless Runner  │
│  (Cloud Run)        │                        │  (Cloud Run Job) │
│  - /lint/topology   │                        │  - Simulator IPC │
│  - /lint/cli        │                        │  - GCS Artifacts │
│  PRIVATE            │                        │  PRIVATE         │
└─────────────────────┘                        └──────────────────┘
         ↑                                                  ↓
         │                                     ┌──────────────────┐
         │                                     │   GCS Bucket     │
         │                                     │   Artifacts      │
         │                                     └──────────────────┘
         │
    OIDC Auth
```

### 1.2 Component Responsibilities

| Component | Purpose | Deployment | Visibility |
|-----------|---------|------------|------------|
| Orchestrator | Multi-agent coordination via ADK | Container/Local | Public (open-source) |
| Parser-Linter | Fast CLI/topology validation | Cloud Run Service | Private (closed-source) |
| Headless Runner | Execute lab simulation | Cloud Run Job | Private (closed-source) |
| Publisher | Generate final lab guides | Part of Orchestrator | Public (open-source) |
| Simulator | Proprietary network simulator | Bundled with Runner | Private (proprietary) |

---

## 2. Technology Stack

### 2.1 Core Technologies

| Layer | Technology | Justification |
|-------|------------|---------------|
| Agent Framework | Google ADK (Agent Development Kit) | Multi-agent orchestration, tool integration |
| Runtime | Python 3.11 | ADK compatibility, rich ecosystem |
| Cloud Platform | Google Cloud Platform | Cloud Run, Cloud Run Jobs, GCS |
| Container Registry | Artifact Registry | Native GCP integration |
| Storage | Google Cloud Storage | Artifact persistence |
| Authentication | OIDC | Service-to-service security |
| CI/CD | GitHub Actions | Automated deployment pipeline |

### 2.2 Key Dependencies

```
# Core
google-adk>=0.1.0
google-cloud-run>=0.9.0
google-cloud-storage>=2.10.0
google-auth>=2.23.0

# Web Framework (Parser-Linter)
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.5.0

# Utilities
pyyaml>=6.0.1
jinja2>=3.1.2
httpx>=0.25.0
structlog>=23.2.0
```

---

## 3. Project Structure

### This Repository (Public - cloud-run-hackathon)

```
cloud-run-hackathon/
├── PRD.md                          # Product Requirements Document
├── IMPLEMENTATION_PLAN.md          # This document
├── README.md                       # Project overview
├── .github/
│   └── workflows/
│       └── ci.yml                  # Lint and test orchestrator
├── orchestrator/                   # ADK-based orchestration (PUBLIC)
│   ├── main.py                     # Entry point
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── planner.py              # Pedagogy Planner agent (M2)
│   │   ├── designer.py             # Topology/Config Designer (M2)
│   │   ├── author.py               # Lab Guide Author (M2)
│   │   ├── validator.py            # Headless Runner orchestrator (M3)
│   │   ├── rca.py                  # Root Cause Analysis (M4)
│   │   └── publisher.py            # Final Lab Guide publisher (M4)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── parser_linter.py        # Tool wrapper for linter service
│   │   ├── headless_runner.py      # Tool wrapper for runner job
│   │   └── artifacts.py            # GCS artifact reader (M3)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── exercise_spec.py        # ExerciseSpec data model
│   │   ├── design_output.py        # DesignOutput data model
│   │   ├── draft_lab_guide.py      # DraftLabGuide model (M2)
│   │   └── validation_result.py    # Validation results
│   ├── Dockerfile
│   ├── requirements.txt
│   └── tests/
├── docs/                           # API documentation for all services
│   ├── parser-linter-api.md        # Complete API contract
│   └── headless-runner-api.md      # Complete job specification
├── infra/                          # Infrastructure automation
│   ├── terraform/                  # IaC (coming in M3)
│   └── scripts/
│       ├── setup-gcp.sh            # GCP project setup
│       ├── deploy-parser-linter.sh # Deploy from private image
│       └── deploy-headless-runner.sh # Deploy from private image
├── examples/                       # Sample labs for testing
│   ├── static-routing/
│   │   ├── README.md
│   │   └── payload.json
│   ├── vlan-basic/                 # (M2)
│   └── ospf-two-router/            # (M2)
└── .pre-commit-config.yaml         # Code quality hooks
```

### Private Repositories (Not in this repo)

**netgenius-parser-linter** (Separate private repository)
```
netgenius-parser-linter/
├── main.py                         # FastAPI app
├── routers/
│   ├── topology.py                 # POST /lint/topology
│   └── cli.py                      # POST /lint/cli
├── linter/
│   ├── topology_validator.py       # YAML schema validation
│   ├── cli_parser_stateful.py      # Stateful mode tracking
│   ├── cli_parser_stateless.py     # Stateless per-line validation
│   └── cisco_syntax.py             # Command syntax rules
├── models/
│   ├── requests.py                 # Pydantic request models
│   └── responses.py                # Pydantic response models
├── Dockerfile
└── requirements.txt
```

**netgenius-headless-runner** (Separate private repository)
```
netgenius-headless-runner/
├── main.py                         # Job entry point
├── runner/
│   ├── executor.py                 # Simulation execution
│   ├── parser.py                   # Payload parsing
│   └── artifacts.py                # GCS writer
├── simulator/                      # Proprietary simulator integration
│   ├── manager.py                  # SimulationManager wrapper
│   └── ipc.py                      # Device IPC handling
├── Dockerfile
└── requirements.txt
```

---

## 4. Milestone Breakdown

### M1: Foundation (Days 1-2)

**Goal:** Set up repository structure, create API contracts, prepare infrastructure

**Note:** Parser-Linter and Headless Runner are implemented in separate private repositories. This milestone focuses on the public orchestrator and API documentation.

#### Tasks

1. **Repository & Project Setup**
   - ✅ Initialize public repo structure (orchestrator only)
   - ✅ Set up Python virtual environments
   - ✅ Configure pre-commit hooks (black, mypy, flake8, isort)
   - ✅ Create .gitignore for Python/GCP/Docker
   - ✅ Create base Dockerfile for orchestrator

2. **API Documentation (for Private Services)**
   - ✅ Document Parser-Linter API contract (`docs/parser-linter-api.md`)
     - POST /lint/topology endpoint specification
     - POST /lint/cli endpoint specification (stateful/stateless)
     - Request/response schemas
     - Authentication (OIDC) requirements
     - Error handling and examples
   - ✅ Document Headless Runner API contract (`docs/headless-runner-api.md`)
     - Cloud Run Job invocation methods
     - Payload schema for simulation jobs
     - Artifact structure and GCS paths
     - Exit codes and monitoring
     - Performance characteristics

3. **GCP Infrastructure Automation**
   - ✅ Create setup script (`infra/scripts/setup-gcp.sh`):
     - Enable required GCP APIs
     - Create Artifact Registry repository
     - Create GCS bucket with lifecycle policy
     - Create service accounts (orchestrator, parser-linter, runner)
     - Configure IAM bindings
   - ✅ Create deployment scripts:
     - `deploy-parser-linter.sh` (deploys from private image)
     - `deploy-headless-runner.sh` (deploys from private image)
   - ⏳ **Manual step required:** Run `infra/scripts/setup-gcp.sh` to create GCP resources

4. **Orchestrator (Skeleton)**
   - ✅ Create data schemas:
     - ExerciseSpec (Planner → Designer)
     - DesignOutput (Designer → Author)
     - ValidationResult (Validator output)
   - ✅ Create tool wrappers:
     - `parser_linter.py` (API client for linter service)
     - `headless_runner.py` (API client for runner job)
   - ✅ Create CLI entry point:
     - `create` command (skeleton)
     - `test-integration` command
     - `version` command
     - Rich console UI

5. **Examples & Testing**
   - ✅ Create static routing example lab with payload.json
   - ✅ Set up CI/CD workflow (GitHub Actions)
     - Linting for orchestrator
     - Documentation validation
     - Example payload validation

**Deliverables:**
- ✅ Public repository with orchestrator skeleton
- ✅ Complete API documentation for private services
- ✅ GCP infrastructure automation scripts
- ✅ Deployment scripts for private services
- ✅ Example lab payload
- ✅ CI/CD pipeline
- ⏳ GCP project setup (manual execution required)

---

### M2: Core Agents + Linting Integration (Days 3-4)

**Goal:** Implement Planner, Designer, and Author agents in the orchestrator with Parser-Linter API integration

**Note:** Parser-Linter service is implemented separately in private repository. This milestone focuses on orchestrator agents that consume the Parser-Linter API.

**Prerequisites:**
- Parser-Linter service deployed and accessible (implemented in private repo)
- Service URL configured in orchestrator environment variables

#### Tasks

1. **Pedagogy Planner Agent**
   - Multi-turn Q&A with instructor using LLM
   - Extract: title, objectives, constraints, level, prerequisites
   - Validate extracted data completeness
   - Output: ExerciseSpec JSON
   - No external tool calls (pure LLM reasoning)
   - Add prompt templates for different lab types (routing, switching, security)

2. **Designer Agent**
   - **Input:** ExerciseSpec (objectives, constraints, level)
   - **Process:**
     - Use LLM to generate topology YAML (devices, interfaces, networks)
     - Generate InitialConfig (base configs for all devices)
     - Generate TargetConfig (expected final state after lab completion)
     - Use LLM to reason about network connectivity and addressing
   - **Validation (via Parser-Linter API):**
     - Call `POST /lint/topology` with generated YAML
     - Call `POST /lint/cli` (stateful) for each device's InitialConfig
     - Parse lint results and retry if errors found (max 2 iterations)
     - Log all validation results for debugging
   - **Output:** DesignOutput JSON with lint results attached
   - **Tool calls:** `parser_linter.lint_topology()`, `parser_linter.lint_cli()`

3. **Lab Guide Author Agent**
   - **Input:** DesignOutput (topology, configs)
   - **Process:**
     - Generate step-by-step student instructions in Markdown
     - Interleave verification steps (`show ip interface brief`, `ping`, etc.)
     - Format per-device sections with clear numbering
     - Add pedagogical guidance (hints, learning objectives, expected outputs)
     - Include difficulty estimates per step
   - **Validation (via Parser-Linter API):**
     - Parse Draft Lab Guide into per-device command sequences
     - Call `POST /lint/cli` (stateful) for each device section
     - Retry authoring if linting fails (max 2 iterations)
   - **Output:** DraftLabGuide (Markdown + structured device sections)
   - **Tool calls:** `parser_linter.lint_cli()`

4. **DraftLabGuide Schema**
   - Create `schemas/draft_lab_guide.py`
   - Define structure for parsed lab guide sections
   - Include device name, command sequences, verification steps

5. **Integration Testing**
   - Test Planner → Designer flow with mock linter responses
   - Test Designer → Author flow with mock linter responses
   - Test end-to-end with real Parser-Linter service (if deployed)
   - Verify error handling and retry logic
   - Test with 2-3 different lab types (routing, VLAN, ACL)

6. **Additional Examples**
   - Create VLAN basic example payload
   - Create OSPF two-router example payload
   - Update examples/README.md with descriptions

**Deliverables:**
- ✅ Planner agent implementation
- ✅ Designer agent with linting integration
- ✅ Author agent with linting integration
- ✅ DraftLabGuide schema
- ✅ Integration tests
- ✅ 2 additional example labs
- Parser-Linter service (implemented separately in private repo)

---

### M3: Headless Validation (Day 5)

**Goal:** Implement Validator agent and artifact handling in orchestrator

**Note:** Headless Runner service is implemented separately in private repository. This milestone focuses on orchestrator components that invoke and consume the runner.

**Prerequisites:**
- Headless Runner service deployed as Cloud Run Job (implemented in private repo)
- GCS bucket configured for artifacts
- Service account permissions configured

#### Tasks

1. **Validator Agent** (in orchestrator)
   - **Input:** DraftLabGuide
   - **Process:**
     - Parse Markdown into runner payload format
     - Map device sections to `devices` JSON
     - Map inline verifies to `{"type": "verify", "value": "..."}`
     - Generate unique `exercise_id` and `build_id`
     - Submit Cloud Run Job via `gcloud run jobs execute` or Jobs API
     - Poll job status until completion (timeout: 15 min)
     - Fetch artifacts from GCS once job completes
     - Parse `summary.json` to determine Go/No-Go
   - **Output:** ValidationResult (pass/fail, artifacts URLs, error summary)
   - **Tool calls:** `headless_runner.submit_job`, `artifacts.read`

3. **Artifacts Tool**
   - Implement `artifacts.read({ job_id, path })` function
   - Stream files from GCS
   - Support both text and binary artifact types

4. **End-to-End Testing**
   - Create test case: Static routing lab (2 routers, 2 networks)
   - Run full flow: Planner → Designer → Author → Validator
   - Verify artifacts are generated correctly
   - Test failure cases (intentional config errors)

**Deliverables:**
- ✅ Validator agent implementation in orchestrator
- ✅ Artifacts tool for GCS reading
- ✅ Cloud Run Jobs API integration
- ✅ End-to-end smoke test (Planner → Validator)
- ✅ Negative test case handling
- Headless Runner service (implemented separately in private repo)

---

### M4: RCA + Publisher + Polish (Day 6)

**Goal:** Complete the feedback loop, publish final labs, polish UX

#### Tasks

1. **Root-Cause Analysis (RCA) Agent**
   - **Input:** ValidationResult (failure case)
   - **Process:**
     - Analyze `summary.json`, `execution.log`, `device_histories.json`
     - Classify failure:
       - **Design issue:** Topology or InitialConfig problem → route to Designer
       - **Instruction issue:** Lab Guide steps incorrect → route to Author
       - **Objective issue:** Unrealistic constraints → route to Planner
     - Generate PatchPlan with specific fix recommendations
   - **Output:** RoutingDecision (agent_to_fix, patch_plan, context)
   - **Tool calls:** `artifacts.read`

2. **Routing Logic in Orchestrator**
   - On validation failure, invoke RCA agent
   - Route PatchPlan to designated agent (Designer/Author/Planner)
   - Limit retry loops to 2 iterations per agent
   - Escalate to human review if retries exhausted

3. **Publisher Agent**
   - **Input:** ValidationResult (success case), DraftLabGuide, Metadata
   - **Process:**
     - Convert Draft Lab Guide to Final Lab Guide (Markdown)
     - Add metadata header (exercise_id, build_id, version, timestamp)
     - Remove inline linting annotations
     - Add links to GCS artifacts (execution logs, configs)
     - Optionally render to PDF/HTML
   - **Output:** PublishedLab (URL, version, metadata)
   - **Tool calls:** `publisher.publish` (writes to GCS or external system)

4. **Orchestrator Graph Finalization**
   - Connect all agents in ADK graph
   - Implement conditional edges (success → Publisher, failure → RCA)
   - Add logging and telemetry at each node
   - Implement graceful error handling

5. **CLI Interface Polish**
   - Add `--verbose` flag for detailed logging
   - Add `--dry-run` mode (skip headless validation)
   - Add `--output` flag to specify artifact directory
   - Pretty-print agent progress with status indicators
   - Display artifact URLs on completion

6. **Testing & Bug Fixes**
   - Run end-to-end tests for all 3 example labs:
     - Static routing (simple)
     - VLAN basic (medium)
     - OSPF two-router (complex)
   - Fix any issues discovered
   - Add golden test cases

**Deliverables:**
- Complete agent graph with RCA and Publisher
- Polished CLI interface
- All example labs passing
- Comprehensive test suite
- Documentation updated

---

### M5: Demo Preparation (Day 7)

**Goal:** Prepare demo materials, finalize documentation

#### Tasks

1. **Demo Script**
   - Prepare 3 example labs (5-10 min each):
     - Live demo: Static routing (quick win)
     - Pre-recorded: VLAN basic (medium complexity)
     - Artifacts showcase: OSPF two-router (complex)
   - Script talking points for each phase (Planner → Publisher)
   - Highlight key differentiators (headless validation, multi-agent graph)

2. **Documentation**
   - Complete API reference (`docs/api-reference.md`)
   - Write deployment guide (`docs/deployment-guide.md`)
   - Document agent architecture (`docs/agent-architecture.md`)
   - Update README with quick start guide

3. **Performance Tuning**
   - Optimize linter response times (<3s)
   - Reduce headless job cold start (<30s)
   - Tune Cloud Run autoscaling settings

4. **Security Review**
   - Verify OIDC auth configured correctly
   - Check least-privilege IAM policies
   - Ensure no secrets in logs or artifacts

5. **Final Testing**
   - Run full test suite
   - Test from clean GCP project (reproducibility)
   - Verify CI/CD pipeline works end-to-end

**Deliverables:**
- Demo-ready system
- Complete documentation
- Reproducible deployment process
- Presentation deck

---

## 5. Component Implementation Details

### 5.1 Orchestrator (ADK)

#### 5.1.1 Agent Graph Structure

```python
# orchestrator/graph.py
from google.adk import Agent, Graph, Edge, Tool

# Define agents
planner = Agent(
    name="pedagogy_planner",
    instructions="Extract learning objectives from instructor requirements",
    tools=[]
)

designer = Agent(
    name="designer",
    instructions="Create network topology and initial/target configs",
    tools=[parser_linter_topology_tool, parser_linter_cli_tool]
)

author = Agent(
    name="lab_guide_author",
    instructions="Write step-by-step lab instructions with inline verification",
    tools=[parser_linter_cli_tool]
)

validator = Agent(
    name="validator",
    instructions="Execute headless validation and collect artifacts",
    tools=[headless_runner_submit_tool, artifacts_read_tool]
)

rca = Agent(
    name="rca",
    instructions="Analyze validation failures and route to appropriate agent",
    tools=[artifacts_read_tool]
)

publisher = Agent(
    name="publisher",
    instructions="Generate final lab guide and publish artifacts",
    tools=[publisher_publish_tool]
)

# Define graph
graph = Graph()
graph.add_edge(Edge(planner, designer))
graph.add_edge(Edge(designer, author))
graph.add_edge(Edge(author, validator))
graph.add_edge(Edge.conditional(
    validator,
    {
        "success": publisher,
        "failure": rca
    }
))
graph.add_edge(Edge.conditional(
    rca,
    {
        "route_to_designer": designer,
        "route_to_author": author,
        "route_to_planner": planner
    }
))
```

#### 5.1.2 Tool Definitions

```python
# orchestrator/tools/parser_linter.py
from google.adk import Tool
import httpx

@Tool
async def lint_topology(topology_yaml: str) -> dict:
    """Validates network topology YAML structure and references."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PARSER_LINTER_URL}/lint/topology",
            json={"topology_yaml": topology_yaml},
            headers={"Authorization": f"Bearer {get_oidc_token()}"}
        )
        response.raise_for_status()
        return response.json()

@Tool
async def lint_cli(
    device_type: str,
    commands: list[dict],
    sequence_mode: str = "stateful",
    stop_on_error: bool = False
) -> dict:
    """Validates CLI command syntax and mode transitions."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PARSER_LINTER_URL}/lint/cli",
            json={
                "device_type": device_type,
                "sequence_mode": sequence_mode,
                "commands": commands,
                "options": {"stop_on_error": stop_on_error}
            },
            headers={"Authorization": f"Bearer {get_oidc_token()}"}
        )
        response.raise_for_status()
        return response.json()
```

```python
# orchestrator/tools/headless_runner.py
from google.adk import Tool
from google.cloud import run_v2

@Tool
async def submit_headless_job(payload: dict) -> dict:
    """Submits a headless runner job and returns job ID."""
    client = run_v2.JobsAsyncClient()

    request = run_v2.RunJobRequest(
        name=f"projects/{PROJECT_ID}/locations/{REGION}/jobs/headless-runner",
        overrides=run_v2.RunJobRequest.Overrides(
            container_overrides=[
                run_v2.RunJobRequest.Overrides.ContainerOverride(
                    env=[
                        run_v2.EnvVar(name="PAYLOAD_JSON", value=json.dumps(payload))
                    ]
                )
            ]
        )
    )

    operation = await client.run_job(request=request)
    return {
        "job_id": operation.name,
        "status_url": f"https://console.cloud.google.com/run/jobs/executions/{operation.name}"
    }
```

#### 5.1.3 Data Schemas

```python
# orchestrator/schemas/exercise_spec.py
from pydantic import BaseModel, Field

class ExerciseSpec(BaseModel):
    """Output from Pedagogy Planner agent."""
    title: str = Field(..., description="Lab title")
    objectives: list[str] = Field(..., description="Learning objectives")
    constraints: dict = Field(..., description="Time, device, complexity limits")
    level: str = Field(..., description="CCNA, CCNP, etc.")
    prerequisites: list[str] = Field(default_factory=list)
```

```python
# orchestrator/schemas/design_output.py
from pydantic import BaseModel

class DesignOutput(BaseModel):
    """Output from Designer agent."""
    topology_yaml: str
    initial_configs: dict[str, list[str]]  # device_name -> command list
    target_configs: dict[str, list[str]]
    platforms: dict[str, str]  # device_name -> platform type
    lint_results: dict  # Results from topology and CLI linting
```

### 5.2 Parser-Linter Service

#### 5.2.1 CLI Linter (Stateful Mode)

```python
# parser-linter/linter/cli_parser_stateful.py
from enum import Enum
from dataclasses import dataclass

class ModeType(Enum):
    USER = "user"
    PRIVILEGED = "privileged"
    GLOBAL = "global"
    INTERFACE = "interface"
    ROUTER = "router"
    LINE = "line"

@dataclass
class Mode:
    type: ModeType
    context: dict = None  # e.g., {"name": "GigabitEthernet0/0"}

class StatefulCLIParser:
    def __init__(self, device_type: str):
        self.device_type = device_type
        self.current_mode = Mode(ModeType.PRIVILEGED)
        self.config_stack = []

    def parse_command(self, command: str) -> dict:
        """Parse command in current mode context."""
        mode_before = self.current_mode

        # Mode transition commands
        if command.strip() == "configure terminal":
            if self.current_mode.type != ModeType.PRIVILEGED:
                return {
                    "ok": False,
                    "command": command,
                    "mode_before": mode_before,
                    "mode_after": self.current_mode,
                    "message": "% Must be in privileged mode"
                }
            self.current_mode = Mode(ModeType.GLOBAL)
            return {"ok": True, "command": command, "mode_before": mode_before, "mode_after": self.current_mode}

        if command.startswith("interface "):
            if self.current_mode.type != ModeType.GLOBAL:
                return {"ok": False, "message": "% Must be in global config mode"}
            interface_name = command.split(None, 1)[1]
            self.current_mode = Mode(ModeType.INTERFACE, {"name": interface_name})
            return {"ok": True, "command": command, "mode_before": mode_before, "mode_after": self.current_mode}

        # Validate command syntax in current mode
        return self._validate_command_in_mode(command, mode_before)

    def _validate_command_in_mode(self, command: str, mode: Mode) -> dict:
        """Validate command syntax for current mode."""
        # Load syntax rules from cisco_syntax.py
        rules = get_syntax_rules(self.device_type, mode.type)

        for rule in rules:
            if rule.matches(command):
                return {
                    "ok": True,
                    "command": command,
                    "mode_before": mode,
                    "mode_after": self.current_mode
                }

        return {
            "ok": False,
            "command": command,
            "mode_before": mode,
            "mode_after": mode,
            "message": f"% Invalid input detected at '^' marker.\n{command}\n^"
        }
```

#### 5.2.2 API Endpoints

```python
# parser-linter/routers/cli.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class LintCLIRequest(BaseModel):
    device_type: str
    sequence_mode: str = "stateful"
    commands: list[dict]
    options: dict = {"stop_on_error": False}

@router.post("/lint/cli")
async def lint_cli(request: LintCLIRequest):
    """Validate CLI command sequences."""
    if request.sequence_mode == "stateful":
        parser = StatefulCLIParser(request.device_type)
        results = []

        for cmd_obj in request.commands:
            result = parser.parse_command(cmd_obj["command"])
            results.append(result)

            if not result["ok"] and request.options.get("stop_on_error", False):
                break

        return {
            "results": results,
            "parser_version": "ng-parser-2025.11.01"
        }

    elif request.sequence_mode == "stateless":
        # Stateless validation (each command with explicit mode)
        results = []
        for cmd_obj in request.commands:
            validator = StatelessCLIValidator(request.device_type, cmd_obj["mode"])
            result = validator.validate(cmd_obj["command"])
            results.append(result)

        return {"results": results, "parser_version": "ng-parser-2025.11.01"}

    else:
        raise HTTPException(status_code=400, detail="Invalid sequence_mode")
```

### 5.3 Headless Runner

#### 5.3.1 Main Execution Logic

```python
# headless-runner/runner/executor.py
import json
import logging
from pathlib import Path
from simulator.manager import SimulationManager
from .artifacts import ArtifactWriter

class HeadlessExecutor:
    def __init__(self, payload: dict, gcs_bucket: str):
        self.payload = payload
        self.exercise_id = payload["exercise_id"]
        self.build_id = generate_build_id()
        self.artifacts = ArtifactWriter(gcs_bucket, self.exercise_id, self.build_id)
        self.logger = logging.getLogger(__name__)

    async def execute(self) -> dict:
        """Execute full simulation and return summary."""
        self.logger.info(f"Starting execution for {self.exercise_id}/{self.build_id}")

        try:
            # Initialize simulator
            sim_manager = SimulationManager(self.payload["topology_yaml"])
            await sim_manager.start()

            # Apply initial configs
            for device_name, initial_cmds in self.payload["devices"].items():
                device = sim_manager.get_device(device_name)
                await self._apply_commands(device, initial_cmds["initial"])

            # Execute student steps
            device_histories = {}
            for device_name, device_config in self.payload["devices"].items():
                device = sim_manager.get_device(device_name)
                history = await self._execute_steps(device, device_config["steps"])
                device_histories[device_name] = history

            # Capture final configs
            final_configs = {}
            for device_name in self.payload["devices"].keys():
                device = sim_manager.get_device(device_name)
                final_configs[device_name] = await device.execute("show running-config")

            # Write artifacts
            await self.artifacts.write_log(self.logger.handlers[0].stream.getvalue())
            await self.artifacts.write_json("device_histories.json", device_histories)
            await self.artifacts.write_text("topology.yaml", self.payload["topology_yaml"])

            for device_name, config in final_configs.items():
                await self.artifacts.write_text(f"final_config/{device_name}.txt", config)

            summary = {
                "success": True,
                "exercise_id": self.exercise_id,
                "build_id": self.build_id,
                "duration_seconds": time.time() - start_time,
                "devices": list(self.payload["devices"].keys())
            }

            await self.artifacts.write_json("summary.json", summary)
            return summary

        except Exception as e:
            self.logger.error(f"Execution failed: {e}", exc_info=True)
            summary = {
                "success": False,
                "error": str(e),
                "exercise_id": self.exercise_id,
                "build_id": self.build_id
            }
            await self.artifacts.write_json("summary.json", summary)
            return summary

    async def _execute_steps(self, device, steps: list[dict]) -> list[dict]:
        """Execute command/verify steps and capture history."""
        history = []

        for step in steps:
            if step["type"] == "cmd":
                output = await device.execute(step["value"])
                history.append({
                    "type": "command",
                    "command": step["value"],
                    "output": output,
                    "timestamp": time.time()
                })

            elif step["type"] == "verify":
                output = await device.execute(step["value"])
                history.append({
                    "type": "verification",
                    "command": step["value"],
                    "output": output,
                    "timestamp": time.time()
                })

        return history
```

---

## 6. Data Flow & Integration

### 6.1 Happy Path Flow

```
1. Instructor Input → Pedagogy Planner
   - Multi-turn Q&A extracts requirements
   - Output: ExerciseSpec JSON

2. ExerciseSpec → Designer
   - Generate topology YAML
   - Generate initial configs
   - Lint topology: POST /lint/topology
   - Lint configs: POST /lint/cli (stateful, per device)
   - Retry if linting fails (max 2x)
   - Output: DesignOutput JSON

3. DesignOutput → Lab Guide Author
   - Write step-by-step instructions
   - Add inline verification commands
   - Parse into per-device sections
   - Lint each section: POST /lint/cli (stateful)
   - Retry if linting fails (max 2x)
   - Output: DraftLabGuide (Markdown)

4. DraftLabGuide → Validator
   - Parse Markdown to runner payload
   - Submit Cloud Run Job: submit_headless_job(payload)
   - Poll job status (wait for completion)
   - Fetch artifacts from GCS: artifacts.read(...)
   - Parse summary.json
   - Output: ValidationResult (Go/No-Go)

5a. ValidationResult (Success) → Publisher
   - Convert Draft to Final Lab Guide
   - Add metadata header
   - Publish to GCS/catalog
   - Notify instructor
   - Output: PublishedLab URL

5b. ValidationResult (Failure) → RCA
   - Analyze logs and device histories
   - Classify failure type
   - Generate PatchPlan
   - Route to Designer/Author/Planner
   - Retry validation (max 2x per agent)
```

### 6.2 Error Handling Strategy

| Error Type | Detection Point | Recovery Action | Escalation |
|------------|----------------|-----------------|------------|
| Topology syntax error | Designer → lint_topology | Regenerate topology, retry | After 2 retries, escalate to RCA |
| Config syntax error | Designer → lint_cli | Fix commands, retry | After 2 retries, escalate to RCA |
| Instruction error | Author → lint_cli | Rewrite steps, retry | After 2 retries, escalate to RCA |
| Simulation failure | Validator → headless job | Route to RCA for analysis | After RCA patch + 2 retries, escalate to human |
| Design mismatch | RCA → artifact analysis | Route to Designer with PatchPlan | After 2 design iterations, escalate to human |

---

## 7. Deployment Strategy

### 7.1 GCP Resource Configuration

#### Service Accounts

```bash
# Orchestrator SA (runs orchestrator, invokes parser-linter and runner)
gcloud iam service-accounts create netgenius-orchestrator \
  --display-name="NetGenius Orchestrator"

# Parser-Linter SA (runs parser-linter service)
gcloud iam service-accounts create netgenius-parser-linter \
  --display-name="NetGenius Parser-Linter"

# Runner SA (runs headless job, writes to GCS)
gcloud iam service-accounts create netgenius-runner \
  --display-name="NetGenius Headless Runner"
```

#### IAM Bindings

```bash
# Orchestrator can invoke parser-linter
gcloud run services add-iam-policy-binding parser-linter \
  --member="serviceAccount:netgenius-orchestrator@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Orchestrator can execute runner jobs
gcloud run jobs add-iam-policy-binding headless-runner \
  --member="serviceAccount:netgenius-orchestrator@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Runner can write to GCS
gsutil iam ch \
  serviceAccount:netgenius-runner@${PROJECT_ID}.iam.gserviceaccount.com:roles/storage.objectAdmin \
  gs://netgenius-artifacts-dev
```

#### Cloud Run Service (Parser-Linter)

```bash
gcloud run deploy parser-linter \
  --image=docker.pkg.dev/${PROJECT_ID}/netgenius/parser-linter:latest \
  --region=us-central1 \
  --platform=managed \
  --no-allow-unauthenticated \
  --service-account=netgenius-parser-linter@${PROJECT_ID}.iam.gserviceaccount.com \
  --min-instances=0 \
  --max-instances=10 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=30s
```

#### Cloud Run Job (Headless Runner)

```bash
gcloud run jobs create headless-runner \
  --image=docker.pkg.dev/${PROJECT_ID}/netgenius/headless-runner:latest \
  --region=us-central1 \
  --service-account=netgenius-runner@${PROJECT_ID}.iam.gserviceaccount.com \
  --memory=2Gi \
  --cpu=1 \
  --task-timeout=2h \
  --max-retries=0 \
  --parallelism=1
```

### 7.2 CI/CD Pipeline

```yaml
# .github/workflows/deploy-parser-linter.yml
name: Deploy Parser-Linter

on:
  push:
    branches: [main]
    paths:
      - 'parser-linter/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1

      - name: Build and push image
        run: |
          cd parser-linter
          gcloud builds submit --tag docker.pkg.dev/$PROJECT_ID/netgenius/parser-linter:$GITHUB_SHA
          gcloud builds submit --tag docker.pkg.dev/$PROJECT_ID/netgenius/parser-linter:latest

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy parser-linter \
            --image docker.pkg.dev/$PROJECT_ID/netgenius/parser-linter:$GITHUB_SHA \
            --region us-central1 \
            --platform managed
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

| Component | Test Coverage | Key Test Cases |
|-----------|--------------|----------------|
| Parser-Linter | CLI syntax validation | Valid commands pass, invalid commands fail, mode transitions correct |
| Headless Runner | Payload parsing | Device configs extracted correctly, steps parsed properly |
| Designer Agent | Topology generation | Valid YAML produced, linting integrated |
| Author Agent | Markdown generation | Per-device sections formatted correctly, verifies included |

### 8.2 Integration Tests

```python
# tests/integration/test_planner_to_designer.py
def test_planner_to_designer_flow():
    """Test Planner → Designer flow with linting."""
    # Arrange
    exercise_spec = ExerciseSpec(
        title="Static Routing Lab",
        objectives=["Configure static routes", "Verify reachability"],
        constraints={"devices": 2, "time_minutes": 30},
        level="CCNA"
    )

    # Act
    design_output = designer_agent.run(exercise_spec)

    # Assert
    assert design_output.topology_yaml is not None
    assert len(design_output.initial_configs) == 2
    assert design_output.lint_results["topology"]["ok"] == True
    assert all(r["ok"] for r in design_output.lint_results["cli"]["results"])
```

### 8.3 End-to-End Tests

```python
# tests/e2e/test_static_routing_lab.py
def test_static_routing_lab_e2e():
    """Test full flow for static routing lab."""
    # Arrange
    user_prompt = "Create a CCNA-level lab for static routing with 2 routers"

    # Act
    result = orchestrator.run(user_prompt)

    # Assert
    assert result.status == "published"
    assert result.validation_result.success == True
    assert result.published_lab.url is not None

    # Verify artifacts
    artifacts = gcs_client.list_artifacts(result.exercise_id, result.build_id)
    assert "summary.json" in artifacts
    assert "device_histories.json" in artifacts
```

### 8.4 Acceptance Tests (from PRD §15)

1. **Smoke Test:** Minimal 2-router static routing lab passes end-to-end
2. **Negative Test:** Invalid interface name caught by `/lint/cli` (stateful)
3. **Resilience Test:** Simulator crash returns structured failure with actionable artifacts

---

## 9. Risk Mitigation

### 9.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Parser false negatives | High | Medium | Golden test suite with known-good/bad commands; stateful + stateless dual validation |
| Simulator nondeterminism | Medium | Low | Fixed timing seeds; single retry on timeout; structured error reporting |
| GCP quota limits | High | Low | Start in us-central1 with small-scale testing; request quota increases proactively |
| ADK agent loops | Medium | Medium | Hard limit of 2 retries per agent; circuit breaker after 5 total iterations |
| Cloud Run Job cold start | Medium | High | Pre-warm with minimal test job; optimize container image size |
| OIDC auth failures | High | Low | Comprehensive auth testing in CI; fallback to API keys in dev |

### 9.2 Timeline Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| M1 overrun (infra setup) | High | Use Terraform for reproducibility; pre-test GCP setup |
| M2 overrun (linter complexity) | Medium | Start with simplified stateful parser; defer stateless to post-MVP |
| M3 overrun (simulator integration) | High | Have fallback mock simulator for headless runner testing |
| M4 overrun (RCA complexity) | Low | Implement basic rule-based RCA; defer LLM-based analysis to post-MVP |

---

## 10. Success Metrics

### 10.1 Performance KPIs (from PRD §4)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Draft Lab Guide validation pass rate | ≥ 90% on 1st or 2nd iteration | Track validation_result.success across all runs |
| End-to-end lab creation time | ≤ 10 min (CCNA exercises) | Measure time from user prompt to published lab |
| Parser-lint response time | ≤ 3s for ≤ 200 commands | Cloud Run request duration metric |
| Headless job completion time | ≤ 5 min (typical topology) | Job execution duration from GCS summary.json |

### 10.2 Quality Metrics

- **Solvability:** 100% of published labs must be solvable by students (validated via headless run)
- **Linter Accuracy:** <5% false positive rate on valid commands, <1% false negative rate on invalid commands
- **Error Handling:** 100% of failures should produce actionable error messages and artifact URLs

### 10.3 Hackathon Demo Metrics

- Successfully demonstrate 3 example labs (static routing, VLAN, OSPF)
- Zero manual fixes required between Planner and Publisher
- Artifacts (logs, configs, histories) clearly showcase validation process

---

## Appendices

### Appendix A: Key Commands Reference

```bash
# Deploy parser-linter
cd parser-linter
gcloud builds submit --tag docker.pkg.dev/${PROJECT_ID}/netgenius/parser-linter
gcloud run deploy parser-linter --image docker.pkg.dev/${PROJECT_ID}/netgenius/parser-linter

# Create headless runner job
cd headless-runner
gcloud builds submit --tag docker.pkg.dev/${PROJECT_ID}/netgenius/headless-runner
gcloud run jobs create headless-runner --image docker.pkg.dev/${PROJECT_ID}/netgenius/headless-runner

# Execute job manually (testing)
gcloud run jobs execute headless-runner \
  --region=us-central1 \
  --args='--exercise-id=test-001 --build-id=build-123'

# View job logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=headless-runner" \
  --limit=50 --format=json

# List artifacts
gsutil ls -r gs://netgenius-artifacts-dev/artifacts/test-001/build-123/
```

### Appendix B: Data Contract Examples

See PRD §6 for full data contracts:
- ExerciseSpec (Planner → Designer)
- DesignOutput (Designer → Author)
- DraftLabGuide (Author → Validator)
- Headless Job Artifacts (Validator → Publisher)

### Appendix C: Troubleshooting Guide

| Issue | Diagnosis | Solution |
|-------|-----------|----------|
| Parser-linter returns 403 | OIDC token missing/invalid | Verify SA has `roles/run.invoker`, check token expiry |
| Headless job times out | Simulation taking too long | Check topology size; increase job timeout; review device histories |
| Artifacts not in GCS | SA lacks storage permissions | Grant `roles/storage.objectAdmin` to runner SA |
| Designer retries exhausted | Linting keeps failing | Review lint results; check if objectives are too complex |

---

## Next Steps

1. **Review this plan** with the team and stakeholders
2. **Set up GCP project** and configure service accounts (M1 Day 1)
3. **Begin implementation** following milestone breakdown
4. **Daily standups** to track progress against timeline
5. **Demo rehearsal** on Day 6 evening

**Questions or feedback?** Contact: Rafael Campos (Owner)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-04
**Status:** Ready for Implementation ✅
