# NetGenius Implementation Plan

**Version:** 2.0 (ADK-First)
**Date:** 2025-01-05
**Status:** Ready for Implementation
**Target:** Google Cloud Hackathon (7-day timeline)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Milestone Breakdown](#4-milestone-breakdown)
5. [Component Implementation Details](#5-component-implementation-details)
6. [Data Flow & Integration](#6-data-flow--integration)
7. [Testing Strategy](#7-testing-strategy)
8. [Success Metrics](#8-success-metrics)
9. [Supplementary Documentation](#9-supplementary-documentation)

---

## 1. Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Orchestrator (Google ADK)                      │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           Multi-Agent Pipeline (ADK)                     │  │
│  │                                                          │  │
│  │  ┌────────────┐   ┌────────────┐   ┌────────────┐      │  │
│  │  │  Planner   │ → │  Designer  │ → │   Author   │ →    │  │
│  │  │ (LlmAgent) │   │ (LlmAgent) │   │ (LlmAgent) │      │  │
│  │  │            │   │            │   │            │      │  │
│  │  │ Multi-turn │   │  Topology  │   │ Lab Guide  │      │  │
│  │  │    Q&A     │   │  + Configs │   │  Writing   │      │  │
│  │  └────────────┘   └────────────┘   └────────────┘      │  │
│  │                                                          │  │
│  │  ┌─────────────────┐                                    │  │
│  │  │   Validator     │ (Custom Agent)                     │  │
│  │  │ Cloud Run Jobs  │                                    │  │
│  │  └─────────────────┘                                    │  │
│  │                                                          │  │
│  │  Orchestrated by: SequentialAgent                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    ADK Tools                             │  │
│  │  - lint_topology (Parser-Linter API)                    │  │
│  │  - lint_cli (Parser-Linter API)                         │  │
│  │  - submit_validation_job (Cloud Run Jobs API)           │  │
│  │  - fetch_artifacts (GCS)                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────┬───────────────────┬───────────────────┘
                          │                   │
              ┌───────────┘                   └──────────────┐
              ↓                                              ↓
    ┌─────────────────────┐                    ┌──────────────────┐
    │ Parser-Linter Svc   │                    │ Headless Runner  │
    │  (Cloud Run)        │                    │ (Cloud Run Job)  │
    │  - /lint/topology   │                    │ - Containerlab   │
    │  - /lint/cli        │                    │ - GCS Artifacts  │
    │  PRIVATE            │                    │ PRIVATE          │
    └─────────────────────┘                    └──────────────────┘
              ↑                                         ↓
              │                            ┌──────────────────┐
              │                            │   GCS Bucket     │
              │                            │   Artifacts      │
              │                            └──────────────────┘
         OIDC Auth
```

### 1.2 Component Responsibilities

| Component | Purpose | ADK Role | Visibility |
|-----------|---------|----------|------------|
| Planner | Interactive Q&A to extract exercise requirements | LlmAgent with Gemini | Public |
| Designer | Generate topology + configs with linting | LlmAgent with tools | Public |
| Author | Write student-facing lab guides | LlmAgent with tools | Public |
| Validator | Execute headless validation | Custom Agent (BaseAgent) | Public |
| Parser-Linter | Fast CLI/topology validation | External service (ADK tool) | Private |
| Headless Runner | Execute lab simulation | Cloud Run Job (ADK tool) | Private |

---

## 2. Technology Stack

### 2.1 Core Technologies

| Layer | Technology | Justification |
|-------|------------|---------------|
| **Agent Framework** | **Google ADK (Agent Development Kit)** | Multi-agent orchestration, required for hackathon |
| **LLM** | **Gemini 2.5 Flash/Pro** | Google's latest model, optimized for ADK |
| Runtime | Python 3.11 | ADK compatibility, rich ecosystem |
| Cloud Platform | Google Cloud Platform | Cloud Run, Cloud Run Jobs, GCS |
| Container Registry | Artifact Registry | Native GCP integration |
| Storage | Google Cloud Storage | Artifact persistence |
| Authentication | OIDC + API Key | Service-to-service (OIDC), Gemini (API key) |

### 2.2 Key Dependencies

```python
# orchestrator/requirements.txt

# Google ADK (Core)
google-adk>=0.2.0

# Google Cloud Services
google-cloud-run>=0.10.0
google-cloud-storage>=2.10.0
google-auth>=2.23.0

# Utilities
pydantic>=2.5.0
pyyaml>=6.0.1
httpx>=0.25.0
structlog>=23.2.0
click>=8.1.0
rich>=13.0.0
```

---

## 3. Project Structure

### 3.1 Repository Structure (ADK-Based)

```
cloud-run-hackathon/
├── PRD.md                          # Product Requirements Document
├── IMPLEMENTATION_PLAN.md          # This document (ADK-first)
├── README.md                       # Project overview
│
├── orchestrator/                   # ADK-based orchestration (PUBLIC)
│   ├── .env                        # Gemini API key
│   ├── main_adk.py                 # ADK CLI entry point
│   ├── requirements.txt
│   ├── Dockerfile
│   │
│   ├── adk_agents/                 # All ADK agents
│   │   ├── __init__.py
│   │   ├── planner.py              # LlmAgent: Interactive Q&A
│   │   ├── designer.py             # LlmAgent: Topology + configs
│   │   ├── author.py               # LlmAgent: Lab guide writing
│   │   ├── validator.py            # Custom Agent: Cloud Run Jobs
│   │   └── tools/                  # ADK tools
│   │       ├── linter_tools.py     # Parser-Linter API wrappers
│   │       ├── gcs_tools.py        # GCS artifact fetching
│   │       └── runner_tools.py     # Cloud Run Jobs integration
│   │
│   ├── workflows/                  # ADK orchestration
│   │   └── pipeline.py             # SequentialAgent definition
│   │
│   ├── schemas/                    # Pydantic models
│   │   ├── __init__.py
│   │   ├── exercise_spec.py        # ExerciseSpec (Planner output)
│   │   ├── design_output.py        # DesignOutput (Designer output)
│   │   ├── draft_lab_guide.py      # DraftLabGuide (Author output)
│   │   └── validation_result.py    # ValidationResult (Validator output)
│   │
│   └── tests/
│       ├── test_planner.py
│       ├── test_designer.py
│       ├── test_author.py
│       ├── test_validator.py
│       └── test_pipeline.py
│
├── docs/                           # Documentation
│   ├── parser-linter-api.md        # API contract for linter service
│   ├── headless-runner-api.md      # API contract for runner job
│   ├── ADK_INTEGRATION_PLAN.md     # Detailed ADK technical guide
│   ├── ADK_INTERACTIVE_PLANNER.md  # Deep Research-style Q&A implementation
│   ├── IMPLEMENTATION_ROADMAP.md   # Day-by-day implementation guide
│   └── SETUP_INSTRUCTIONS.md       # Environment setup guide
│
├── infra/                          # Infrastructure automation
│   └── scripts/
│       ├── setup-gcp.sh            # GCP project setup
│       ├── deploy-parser-linter.sh # Deploy private service
│       └── deploy-headless-runner.sh # Deploy private job
│
├── examples/                       # Sample labs
│   ├── static-routing/
│   ├── vlan-basic/
│   └── ospf-two-router/
│
└── .github/
    └── workflows/
        └── ci.yml                  # Lint and test orchestrator
```

### 3.2 Private Repositories

**netgenius-parser-linter** (Separate private repository)
- FastAPI service with `/lint/topology` and `/lint/cli` endpoints
- Stateful CLI parser tracking mode transitions
- Deployed as Cloud Run Service

**netgenius-headless-runner** (Separate private repository)
- Containerlab-based simulation executor
- Reads lab guide payloads, executes steps, writes GCS artifacts
- Deployed as Cloud Run Job

---

## 4. Milestone Breakdown

### M0: Setup & Environment Configuration

**Goal:** Install ADK, configure Gemini API, verify environment

**Tasks:**
- [ ] Create `orchestrator/.env` with Gemini API key
- [ ] Install ADK: `pip install google-adk`
- [ ] Verify installation: `adk --version`
- [ ] Test ADK web UI: `adk web --port 8000`
- [ ] Set up GCP project (run `infra/scripts/setup-gcp.sh`)
- [ ] Create service accounts and IAM bindings
- [ ] Create GCS bucket for artifacts

**Deliverables:**
- Working ADK installation
- Gemini API key configured
- GCP project ready
- Service accounts created

**Reference:** `docs/SETUP_INSTRUCTIONS.md`

---

### M1: Interactive Planner Agent (ADK Multi-Turn Q&A)

**Goal:** Implement ChatGPT Deep Research-style interactive planner using ADK

**Background:**
Per PRD Section 7.1: *"Pedagogy Planner — multi-turn Q&A with instructor → ExerciseSpec"*

The instructor provides a vague prompt like "teach static routing", and the agent asks clarifying questions:
- How many routers?
- Include floating static routes?
- Difficulty level?
- Time estimate?

**Implementation:**

```python
# orchestrator/adk_agents/planner.py
from google.adk.agents import LlmAgent
from schemas.exercise_spec import ExerciseSpec

planner_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="PedagogyPlanner",
    description="Interactive planner with multi-turn Q&A for lab requirements",
    instruction="""
You are an expert networking instructor helping design lab exercises.

INTERACTION FLOW:
1. User provides initial prompt (e.g., "teach static routing")
2. Analyze what's missing (device count, topics, difficulty, time)
3. Ask 3-5 targeted clarifying questions
4. Wait for user's answers
5. If incomplete, ask follow-up questions
6. Once you have complete information, output ExerciseSpec JSON

QUESTION TEMPLATES BY LAB TYPE:

Static Routing:
- How many routers? (2-4 recommended)
- Include floating static routes for redundancy?
- Include default routes (0.0.0.0/0)?
- Difficulty level? (Beginner/Intermediate/Advanced)
- Estimated time? (30/45/60 minutes)

OSPF:
- How many routers? How many areas?
- Single-area or multi-area OSPF?
- Include route summarization?
- Teach DR/BDR election?

VLANs:
- How many switches? How many VLANs?
- Include inter-VLAN routing?
- Include trunk configuration?

IMPORTANT:
- If user provides detailed info upfront, skip questions
- Keep questions concise (5 max per turn)
- Use friendly, professional tone

OUTPUT: When ready, return JSON matching ExerciseSpec schema (no markdown).
""",
    output_key="exercise_spec",
    output_schema=ExerciseSpec
)
```

**ADK Features Used:**
- `LlmAgent` with Gemini for intelligent conversation
- `output_schema` for structured Pydantic output
- Session management (automatic via ADK Runner)
- Multi-turn conversation history (automatic)

**Testing:**
```bash
# Start ADK web UI
cd orchestrator
adk web --port 8000

# Test conversations:
# 1. "teach static routing" → should ask questions
# 2. "3 router OSPF, intermediate, 45 min" → should skip to output
```

**Deliverables:**
- [ ] `adk_agents/planner.py` with LlmAgent
- [ ] `schemas/exercise_spec.py` with Pydantic model
- [ ] Interactive Q&A working in ADK web UI
- [ ] Unit tests for planner agent

**Reference:** `docs/ADK_INTERACTIVE_PLANNER.md`

---

### M2: Designer Agent with Linting Integration

**Goal:** Implement topology and config generation with Parser-Linter validation

**Implementation:**

```python
# orchestrator/adk_agents/designer.py
from google.adk.agents import LlmAgent
from google.adk.agents.planner import BuiltInPlanner
from adk_agents.tools.linter_tools import lint_topology, lint_cli
from schemas.design_output import DesignOutput

designer_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="Designer",
    description="Creates network topology and device configurations with validation",
    instruction="""
You are a network design expert creating Containerlab topologies and Cisco IOS configs.

INPUT: {exercise_spec} from session state

TASKS:
1. Generate Containerlab YAML defining devices and links
2. Create initial device configs (baseline state)
3. Create target configs (desired end state after lab completion)
4. Use lint_topology() tool to validate YAML structure
5. Use lint_cli() tool with sequence_mode="stateful" to validate configs
6. If linting fails, analyze errors and fix (max 2 retries)

CONTAINERLAB FORMAT:
```yaml
topology:
  nodes:
    R1:
      kind: cisco_iosv
      image: cisco-iosv:15.6
    R2:
      kind: cisco_iosv
      image: cisco-iosv:15.6
  links:
    - endpoints: ["R1:GigabitEthernet0/0", "R2:GigabitEthernet0/0"]
```

CISCO IOS CONFIG REQUIREMENTS:
- Start with: hostname, no ip domain-lookup, line con 0
- Configure interfaces with IP addresses
- Add routing protocol config per exercise_spec
- Make configs realistic and follow best practices

OUTPUT: JSON with topology_yaml, initial_configs, target_configs, lint_results
""",
    tools=[lint_topology, lint_cli],
    output_key="design_output",
    output_schema=DesignOutput,
    planner=BuiltInPlanner()  # Enable multi-step reasoning
)
```

**ADK Tools:**

```python
# orchestrator/adk_agents/tools/linter_tools.py
import httpx
import os

async def lint_topology(topology_yaml: str) -> dict:
    """
    Validate Containerlab topology YAML.

    Calls Parser-Linter service: POST /lint/topology
    """
    # For testing: return mock if service not deployed
    if not os.getenv("PARSER_LINTER_URL"):
        return {"ok": True, "errors": [], "warnings": [], "message": "Mock response"}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{os.getenv('PARSER_LINTER_URL')}/lint/topology",
            json={"topology_yaml": topology_yaml},
            headers={"Authorization": f"Bearer {get_oidc_token()}"}
        )
        return response.json()

async def lint_cli(
    device_type: str,
    commands: list[dict],
    sequence_mode: str = "stateful"
) -> dict:
    """
    Validate Cisco IOS command sequences.

    Calls Parser-Linter service: POST /lint/cli
    """
    # Mock for testing
    if not os.getenv("PARSER_LINTER_URL"):
        return {
            "ok": True,
            "results": [{"command": c["command"], "valid": True} for c in commands]
        }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{os.getenv('PARSER_LINTER_URL')}/lint/cli",
            json={
                "device_type": device_type,
                "sequence_mode": sequence_mode,
                "commands": commands
            },
            headers={"Authorization": f"Bearer {get_oidc_token()}"}
        )
        return response.json()
```

**Deliverables:**
- [ ] `adk_agents/designer.py` with LlmAgent
- [ ] `adk_agents/tools/linter_tools.py` with API wrappers
- [ ] `schemas/design_output.py` with Pydantic model
- [ ] Designer agent reading `{exercise_spec}` from session state
- [ ] Linting integration with retry logic
- [ ] Mock linter responses for testing (before service deployment)
- [ ] Unit tests for designer agent

**Reference:** `docs/ADK_INTEGRATION_PLAN.md` (Section 3: Phase 2)

---

### M3: Author Agent with Lab Guide Generation

**Goal:** Generate student-facing lab guides with verification steps

**Implementation:**

```python
# orchestrator/adk_agents/author.py
from google.adk.agents import LlmAgent
from adk_agents.tools.linter_tools import lint_cli
from schemas.draft_lab_guide import DraftLabGuide

author_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="LabGuideAuthor",
    description="Writes pedagogically sound lab guides with clear instructions",
    instruction="""
You are an expert technical writer creating networking lab guides.

INPUT:
- {exercise_spec}: Learning objectives, devices, level
- {design_output}: Topology, configs, platforms

CREATE LAB GUIDE WITH:
1. Title and learning objectives
2. Topology description
3. Per-device configuration steps:
   - Clear imperative instructions ("Configure VLAN 10")
   - Explanations of WHY each step matters
   - Verification commands after changes (show ip int brief, ping)
   - Expected outputs
   - Troubleshooting hints

4. Summary and learning reinforcement

VALIDATION:
- Use lint_cli() to validate all command sequences
- Ensure verification commands are syntactically correct

MARKDOWN FORMAT:
# Lab Title

## Learning Objectives
- Objective 1
- Objective 2

## Device: R1

### Step 1: Configure Hostname
```
Router> enable
Router# configure terminal
Router(config)# hostname R1
```

**Why?** Unique hostnames help identify devices.

### Verification:
```
R1# show running-config | include hostname
```
Expected: `hostname R1`

OUTPUT: JSON with title, markdown, device_sections, estimated_time, lint_results
""",
    tools=[lint_cli],
    output_key="draft_lab_guide",
    output_schema=DraftLabGuide
)
```

**Deliverables:**
- [ ] `adk_agents/author.py` with LlmAgent
- [ ] `schemas/draft_lab_guide.py` with Pydantic model
- [ ] Author reads `{exercise_spec}` and `{design_output}` from state
- [ ] Markdown generation with verification steps
- [ ] CLI linting for command validation
- [ ] Unit tests for author agent

**Reference:** `docs/ADK_INTEGRATION_PLAN.md` (Section 3: Phase 3)

---

### M4: Validator as Custom Agent (Cloud Run Jobs)

**Goal:** Execute headless validation and fetch GCS artifacts

**Implementation:**

```python
# orchestrator/adk_agents/validator.py
from google.adk.agents import BaseAgent
from google.adk.context import InvocationContext
from google.adk.events import Event, EventActions
from google.cloud import run_v2, storage
import json
import asyncio
import time

class ValidatorAgent(BaseAgent):
    """Custom agent for headless validation via Cloud Run Jobs"""

    def __init__(
        self,
        project_id: str = "netgenius-hackathon",
        region: str = "us-central1",
        job_name: str = "headless-runner",
        bucket_name: str = "netgenius-artifacts-dev"
    ):
        super().__init__(name="Validator")
        self.project_id = project_id
        self.region = region
        self.job_name = job_name
        self.bucket_name = bucket_name

    async def run_async(self, context: InvocationContext):
        """Execute validation workflow"""

        # Get artifacts from session state
        draft_guide = context.session.state.get("draft_lab_guide")
        design = context.session.state.get("design_output")

        if not draft_guide or not design:
            yield Event(
                type="agent_message",
                content="ERROR: Missing draft_lab_guide or design_output in state"
            )
            return EventActions()

        # Step 1: Convert to runner payload
        payload = self._convert_payload(draft_guide, design)

        yield Event(
            type="agent_message",
            content="Converting lab guide to validation payload..."
        )

        # Step 2: Submit Cloud Run Job
        execution_id = await self._submit_job(payload)

        yield Event(
            type="agent_message",
            content=f"Submitted validation job: {execution_id}"
        )

        # Step 3: Poll until completion
        success = await self._poll_job(execution_id)

        # Step 4: Fetch artifacts from GCS
        artifacts = await self._fetch_artifacts(execution_id)

        # Step 5: Save to state
        context.session.state["validation_result"] = {
            "execution_id": execution_id,
            "success": artifacts["success"],
            "summary": artifacts["summary"],
            "passed_steps": artifacts["passed_steps"],
            "total_steps": artifacts["total_steps"]
        }

        status = "PASS ✓" if artifacts["success"] else "FAIL ✗"
        yield Event(
            type="agent_message",
            content=f"""
Validation Complete: {status}
Execution ID: {execution_id}
Steps: {artifacts['passed_steps']}/{artifacts['total_steps']} passed
"""
        )

        return EventActions()

    def _convert_payload(self, draft_guide, design):
        """Convert DraftLabGuide to runner payload"""
        devices_payload = []
        for section in draft_guide["device_sections"]:
            device_dict = {
                "hostname": section["hostname"],
                "steps": [
                    {
                        "type": step["type"],
                        "value": step["value"],
                        "description": step["description"]
                    }
                    for step in section["steps"]
                ]
            }
            devices_payload.append(device_dict)

        return {
            "topology": design["topology_yaml"],
            "initial_configs": design["initial_configs"],
            "devices": devices_payload
        }

    async def _submit_job(self, payload):
        """Submit Cloud Run Job"""
        execution_id = time.strftime("%Y%m%d-%H%M%S")
        client = run_v2.JobsClient()

        request = run_v2.RunJobRequest(
            name=f"projects/{self.project_id}/locations/{self.region}/jobs/{self.job_name}",
            overrides={
                "container_overrides": [{
                    "env": [
                        {"name": "EXECUTION_ID", "value": execution_id},
                        {"name": "GCS_BUCKET", "value": self.bucket_name},
                        {"name": "VALIDATION_PAYLOAD", "value": json.dumps(payload)}
                    ]
                }]
            }
        )

        operation = client.run_job(request=request)
        return execution_id

    async def _poll_job(self, execution_id):
        """Poll job status until completion"""
        client = run_v2.ExecutionsClient()
        job_path = f"projects/{self.project_id}/locations/{self.region}/jobs/{self.job_name}"

        while True:
            request = run_v2.ListExecutionsRequest(parent=job_path)
            executions = client.list_executions(request=request)

            latest = None
            for execution in executions:
                if latest is None or execution.create_time > latest.create_time:
                    latest = execution

            if latest:
                succeeded = latest.succeeded_count
                failed = latest.failed_count
                total = latest.task_count

                if succeeded + failed == total:
                    return failed == 0

            await asyncio.sleep(10)

    async def _fetch_artifacts(self, execution_id):
        """Fetch artifacts from GCS"""
        storage_client = storage.Client(project=self.project_id)
        bucket = storage_client.bucket(self.bucket_name)

        # Fetch summary.json
        summary_blob = bucket.blob(f"{execution_id}/summary.json")
        summary = json.loads(summary_blob.download_as_text())

        return {
            "success": summary.get("status") == "PASS",
            "summary": summary,
            "passed_steps": summary.get("stats", {}).get("passed", 0),
            "total_steps": summary.get("stats", {}).get("total_steps", 0)
        }
```

**Deliverables:**
- [ ] `adk_agents/validator.py` as Custom Agent extending `BaseAgent`
- [ ] Cloud Run Jobs API integration
- [ ] GCS artifact fetching
- [ ] Payload conversion from DraftLabGuide
- [ ] Job polling with status updates
- [ ] Unit tests for validator

**Reference:** `docs/ADK_INTEGRATION_PLAN.md` (Section 3: Phase 5)

---

### M5: Pipeline Orchestration with SequentialAgent

**Goal:** Connect all agents in ADK pipeline

**Implementation:**

```python
# orchestrator/workflows/pipeline.py
from google.adk.agents import SequentialAgent
from adk_agents.planner import planner_agent
from adk_agents.designer import designer_agent
from adk_agents.author import author_agent
from adk_agents.validator import ValidatorAgent

lab_creation_pipeline = SequentialAgent(
    name="LabCreationPipeline",
    description="End-to-end lab creation: Planning → Design → Authoring → Validation",
    sub_agents=[
        planner_agent,      # Multi-turn Q&A → exercise_spec
        designer_agent,     # Reads exercise_spec → design_output
        author_agent,       # Reads exercise_spec + design_output → draft_lab_guide
        ValidatorAgent()    # Reads draft_lab_guide + design_output → validation_result
    ]
)
```

**Interactive CLI:**

```python
# orchestrator/main_adk.py
import click
from google.adk.runner import Runner
from google.adk.session import InMemorySessionService
from workflows.pipeline import lab_creation_pipeline
import time

@click.command()
@click.option("--prompt", help="Initial instructor prompt (optional)")
@click.option("--dry-run", is_flag=True, help="Skip validation step")
def create(prompt, dry_run):
    """Create lab with interactive Q&A"""

    session_service = InMemorySessionService()
    runner = Runner(
        agent=lab_creation_pipeline,
        app_name="netgenius",
        session_service=session_service
    )

    user_id = "instructor"
    session_id = f"lab_{int(time.time())}"

    print("=" * 60)
    print("NetGenius Lab Creator (Powered by Google ADK)")
    print("=" * 60)

    # Get initial prompt
    if not prompt:
        prompt = input("\nWhat lab would you like to create? ")

    # Start conversation
    events = runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=prompt
    )

    # Print initial response
    for event in events:
        if event.type == "agent_message":
            print(f"\n{event.content}\n")

    # Multi-turn loop for planner Q&A
    session = session_service.get_session(user_id, session_id)

    while "exercise_spec" not in session.state:
        # Planner is asking questions
        user_response = input("Your answers: ")

        events = runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=user_response
        )

        for event in events:
            if event.type == "agent_message":
                print(f"\n{event.content}\n")

        session = session_service.get_session(user_id, session_id)

        if "exercise_spec" in session.state:
            print("\n✓ Planning complete! Proceeding to design...\n")
            break

    # Pipeline continues automatically (Designer → Author → Validator)
    # Display final results
    print("\n" + "=" * 60)
    print("Lab Creation Complete!")
    print("=" * 60)

    validation = session.state.get("validation_result", {})
    if validation:
        status = "PASSED" if validation["success"] else "FAILED"
        print(f"\nValidation: {status}")
        print(f"Steps: {validation['passed_steps']}/{validation['total_steps']}")

    # Save artifacts
    _save_artifacts(session.state)

if __name__ == "__main__":
    create()
```

**Deliverables:**
- [ ] `workflows/pipeline.py` with SequentialAgent
- [ ] `main_adk.py` with interactive CLI
- [ ] Multi-turn conversation handling
- [ ] Artifact saving to disk
- [ ] End-to-end pipeline testing

**Reference:** `docs/IMPLEMENTATION_ROADMAP.md` (Milestone 5)

---

### M6: Testing & Polish

**Goal:** Comprehensive testing, error handling, documentation

**Tasks:**

1. **Unit Tests**
   - [ ] Test each agent in isolation
   - [ ] Test planner with various prompts
   - [ ] Test designer with different lab types
   - [ ] Test author with mock design outputs
   - [ ] Test validator with mock Cloud Run Jobs

2. **Integration Tests**
   - [ ] Test Planner → Designer flow
   - [ ] Test Designer → Author flow
   - [ ] Test Author → Validator flow
   - [ ] Test full pipeline end-to-end

3. **Example Labs**
   - [ ] Static routing (2 routers)
   - [ ] VLAN basic (2 switches)
   - [ ] OSPF (3 routers)
   - [ ] All examples pass validation

4. **Error Handling**
   - [ ] Handle missing API keys gracefully
   - [ ] Handle linting failures with retries
   - [ ] Handle Cloud Run Job failures
   - [ ] Handle GCS artifact fetch failures

5. **Documentation**
   - [ ] Update README with quickstart
   - [ ] Document CLI usage
   - [ ] Document environment variables
   - [ ] Create troubleshooting guide

**Deliverables:**
- [ ] Complete test suite (unit + integration)
- [ ] All example labs working
- [ ] Error handling comprehensive
- [ ] Documentation complete

---

### M7: Deployment & Demo Preparation

**Goal:** Deploy to Cloud Run, prepare demo materials

**Tasks:**

1. **Cloud Run Deployment**
   ```dockerfile
   # orchestrator/Dockerfile
   FROM python:3.11-slim

   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY . .
   EXPOSE 8080

   CMD ["adk", "web", "--port", "8080", "--host", "0.0.0.0"]
   ```

   ```bash
   gcloud run deploy netgenius-orchestrator \
     --source=. \
     --region=us-central1 \
     --allow-unauthenticated \
     --set-env-vars=GOOGLE_API_KEY=$GEMINI_API_KEY
   ```

2. **Demo Script**
   - [ ] Introduction (2 min): Problem + solution
   - [ ] Interactive Planning (3 min): "teach static routing" → Q&A
   - [ ] Pipeline Execution (5 min): Show all agents running
   - [ ] Artifacts Review (3 min): Show generated files
   - [ ] Architecture Explanation (5 min): ADK diagram
   - [ ] Q&A (2 min)

3. **Presentation Materials**
   - [ ] Slides with architecture diagrams
   - [ ] Live demo script with fallback
   - [ ] Pre-recorded video (backup)
   - [ ] GitHub repo polished

**Deliverables:**
- [ ] Cloud Run service deployed
- [ ] Demo script prepared
- [ ] Presentation slides complete
- [ ] Backup materials ready

---

## 5. Component Implementation Details

### 5.1 ADK Session State Management

All agents share session state through `InvocationContext`. Data flows via `output_key`:

```python
session.state = {
    "exercise_spec": {          # From Planner (output_key="exercise_spec")
        "title": "Static Routing Lab",
        "objectives": [...],
        "devices": [...],
        "lab_type": "static_routing"
    },
    "design_output": {          # From Designer (output_key="design_output")
        "topology_yaml": "...",
        "initial_configs": {...},
        "target_configs": {...}
    },
    "draft_lab_guide": {        # From Author (output_key="draft_lab_guide")
        "title": "...",
        "markdown": "...",
        "device_sections": [...]
    },
    "validation_result": {      # From Validator (custom agent writes directly)
        "execution_id": "20250105-143022",
        "success": True,
        "passed_steps": 12,
        "total_steps": 12
    }
}
```

### 5.2 ADK Agent Communication

**Sequential Pipeline:**
- SequentialAgent passes same `InvocationContext` to each sub-agent
- Each agent reads from `session.state` using placeholders: `{exercise_spec}`
- Each agent writes to `session.state` using `output_key`
- No manual state passing required

**Custom Agent Integration:**
- Validator extends `BaseAgent`
- Implements `run_async(context: InvocationContext)`
- Reads from `context.session.state`
- Writes to `context.session.state`
- Yields `Event` objects for progress updates

### 5.3 Tool Definitions

ADK automatically wraps Python functions as tools:

```python
# orchestrator/adk_agents/tools/linter_tools.py

async def lint_topology(topology_yaml: str) -> dict:
    """
    Validates network topology YAML structure.

    This function is automatically available as a tool to LlmAgent.
    """
    # Implementation
    pass

# Usage in agent:
designer_agent = LlmAgent(
    tools=[lint_topology, lint_cli],  # Functions become tools
    instruction="Use lint_topology() to validate..."
)
```

---

## 6. Data Flow & Integration

### 6.1 Happy Path Flow

```
1. User: "teach static routing"
   ↓
2. Planner (LlmAgent): Asks questions via multi-turn conversation
   - "How many routers?"
   - "Include floating routes?"
   - "Difficulty level?"
   ↓
3. User: "3 routers, yes, intermediate"
   ↓
4. Planner: Outputs ExerciseSpec to session.state["exercise_spec"]
   ↓
5. Designer (LlmAgent): Reads {exercise_spec}
   - Generates topology YAML
   - Generates initial/target configs
   - Calls lint_topology() tool
   - Calls lint_cli() tool
   - Retries if linting fails
   ↓ Outputs to session.state["design_output"]

6. Author (LlmAgent): Reads {exercise_spec} + {design_output}
   - Writes markdown lab guide
   - Adds verification steps
   - Calls lint_cli() to validate commands
   ↓ Outputs to session.state["draft_lab_guide"]

7. Validator (Custom Agent): Reads draft_lab_guide + design_output
   - Converts to runner payload
   - Submits Cloud Run Job
   - Polls until completion
   - Fetches GCS artifacts
   - Parses summary.json
   ↓ Outputs to session.state["validation_result"]

8. Success: Display results to user
```

### 6.2 Error Handling

| Error Type | Detection | Recovery | ADK Pattern |
|------------|-----------|----------|-------------|
| Invalid prompt | Planner | Ask clarifying questions | Multi-turn conversation |
| Topology lint fail | Designer | LLM self-corrects, retry | Tool feedback loop |
| CLI lint fail | Designer/Author | LLM self-corrects, retry | Tool feedback loop |
| Job submission fail | Validator | Log error, escalate | Exception in run_async |
| GCS fetch fail | Validator | Retry with backoff | asyncio retry logic |

---

## 7. Testing Strategy

### 7.1 Unit Tests

```python
# tests/test_planner.py
import pytest
from google.adk.runner import Runner
from adk_agents.planner import planner_agent

def test_planner_with_minimal_prompt():
    """Test planner with vague prompt - should ask questions"""
    runner = Runner(agent=planner_agent)

    events = runner.run(
        user_id="test",
        session_id="test",
        new_message="teach static routing"
    )

    # Should ask questions (not immediately output ExerciseSpec)
    session = runner.session_service.get_session("test", "test")
    assert "exercise_spec" not in session.state

def test_planner_with_detailed_prompt():
    """Test planner with detailed prompt - should skip questions"""
    runner = Runner(agent=planner_agent)

    events = runner.run(
        user_id="test",
        session_id="test",
        new_message="3 router OSPF lab, intermediate level, 45 minutes"
    )

    # Should output ExerciseSpec immediately
    session = runner.session_service.get_session("test", "test")
    assert "exercise_spec" in session.state
    assert session.state["exercise_spec"]["lab_type"] == "ospf"
```

### 7.2 Integration Tests

```python
# tests/test_pipeline.py
def test_full_pipeline():
    """Test Planner → Designer → Author → Validator"""
    from workflows.pipeline import lab_creation_pipeline

    runner = Runner(agent=lab_creation_pipeline)
    session = runner.session_service.get_session("test", "test")

    # Inject exercise_spec to skip interactive Q&A
    session.state["exercise_spec"] = {
        "title": "Static Routing Lab",
        "lab_type": "static_routing",
        "devices": [{"hostname": "R1"}, {"hostname": "R2"}],
        "level": "beginner"
    }

    # Run pipeline (Designer → Author → Validator)
    events = runner.run(user_id="test", session_id="test", new_message="Create lab")

    # Assert all stages completed
    assert "design_output" in session.state
    assert "draft_lab_guide" in session.state
    assert "validation_result" in session.state
```

---

## 8. Success Metrics

### 8.1 Performance KPIs (from PRD)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Lab creation time | ≤ 10 min | End-to-end (Planner → Validator) |
| Validation pass rate | ≥ 90% first/second iteration | Track validation_result.success |
| Parser-lint response | ≤ 3s for ≤ 200 commands | Tool call latency |
| Headless job completion | ≤ 5 min typical topology | Job duration from summary.json |

### 8.2 Hackathon Demo Metrics

- [ ] Successfully demonstrate 3 lab types (static routing, VLAN, OSPF)
- [ ] Interactive Q&A works smoothly in web UI
- [ ] All agents run without errors
- [ ] Artifacts clearly show validation results
- [ ] Zero manual intervention required

### 8.3 Code Quality

- [ ] All agents use ADK patterns correctly
- [ ] No hardcoded secrets (use env vars)
- [ ] Comprehensive error handling
- [ ] Test coverage ≥ 80%
- [ ] Documentation complete

---

## 9. Supplementary Documentation

For detailed implementation guidance, refer to:

- **`docs/ADK_INTEGRATION_PLAN.md`** - Complete technical guide to ADK patterns, agent types, and code examples
- **`docs/ADK_INTERACTIVE_PLANNER.md`** - Deep dive on multi-turn Q&A implementation (Deep Research style)
- **`docs/IMPLEMENTATION_ROADMAP.md`** - Day-by-day breakdown with concrete tasks
- **`docs/SETUP_INSTRUCTIONS.md`** - Environment setup, API key configuration, testing procedures
- **`docs/parser-linter-api.md`** - API contract for Parser-Linter service
- **`docs/headless-runner-api.md`** - API contract for Headless Runner job

---

## Next Steps

1. **Review this plan** and confirm alignment with hackathon goals
2. **Set up environment** following `docs/SETUP_INSTRUCTIONS.md`
3. **Start with M0-M1** (Setup + Interactive Planner)
4. **Iterate through milestones** M2-M7
5. **Test continuously** as each milestone completes
6. **Prepare demo** in parallel with M6-M7

**Key Success Factor:** ADK from day 1 - all agents use Google's official framework, showcasing best practices for the hackathon.

---

**Document Version:** 2.0 (ADK-First)
**Last Updated:** 2025-01-05
**Status:** Ready for Implementation ✅
