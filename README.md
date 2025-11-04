# NetGenius - AI-Powered Networking Lab Generator

**Status:** M1 Development (Foundation)
**Platform:** Google Cloud (Cloud Run + Cloud Run Jobs)
**Architecture:** Multi-agent system using Google ADK
**Repository:** Public (Orchestrator only)

## Overview

NetGenius automates the full lifecycle of networking lab creation for instructors:
- 📋 Planning learning objectives
- 🏗️ Designing network topology and configurations
- ✍️ Authoring student-facing lab guides
- ✅ Validating labs via headless simulation
- 📦 Publishing final, solvable lab materials

## Architecture

```
┌─────────────────────────────────────────────────────┐
│           Orchestrator (This Repo - Public)         │
│                    Google ADK                        │
│  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌────────┐│
│  │ Planner  │→ │ Designer │→ │ Author │→ │Validator││
│  └──────────┘  └──────────┘  └────────┘  └────────┘│
└────────┬────────────────────────────────────┬───────┘
         │                                    │
    ┌────┴────────┐                      ┌────┴──────────┐
    │  Parser-    │                      │   Headless    │
    │  Linter     │                      │   Runner      │
    │  (Private)  │                      │   (Private)   │
    │  Cloud Run  │                      │  Cloud Run Job│
    └─────────────┘                      └────────┬──────┘
                                                  │
                                         ┌────────┴──────┐
                                         │  GCS Artifacts│
                                         └───────────────┘
```

## Repository Structure

This repository contains **only the open-source orchestrator**. The validation and simulation services are maintained in separate private repositories.

### This Repository (Public)
```
cloud-run-hackathon/
├── orchestrator/          # ADK-based multi-agent orchestrator
│   ├── agents/           # Planner, Designer, Author, Validator, RCA, Publisher
│   ├── tools/            # Tool wrappers for private services
│   └── schemas/          # Data models for agent communication
├── docs/                 # API documentation for all services
│   ├── parser-linter-api.md     # Parser-Linter API contract
│   └── headless-runner-api.md   # Headless Runner API contract
├── infra/                # GCP infrastructure and deployment
│   ├── scripts/          # Setup and deployment scripts
│   └── terraform/        # Infrastructure as Code (coming soon)
├── examples/             # Sample labs and payloads
│   └── static-routing/   # Example static routing lab
└── README.md             # This file
```

### Private Repositories (Not Included)

**netgenius-parser-linter** (Private)
- Fast CLI and topology validation service
- Stateful/stateless command parsing
- Cisco IOS syntax validation
- Deployed as Cloud Run Service

**netgenius-headless-runner** (Private)
- Network simulation execution engine
- Proprietary simulator integration
- GCS artifact generation
- Deployed as Cloud Run Job

## Components

| Component | Description | Visibility | Deployment |
|-----------|-------------|------------|------------|
| **Orchestrator** | Multi-agent coordination via Google ADK | Public (this repo) | Local/Container |
| **Parser-Linter** | Fast CLI/topology validation service | Private | Cloud Run Service |
| **Headless Runner** | Simulation execution in Cloud Run Jobs | Private | Cloud Run Job |

## API Documentation

Even though the Parser-Linter and Headless Runner source code is private, their API contracts are fully documented:

- [Parser-Linter API Reference](docs/parser-linter-api.md) - Complete API specification
- [Headless Runner API Reference](docs/headless-runner-api.md) - Job payload and artifact formats

The orchestrator integrates with these services via well-defined REST/RPC interfaces.

## Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud SDK
- Access to deployed Parser-Linter and Headless Runner services

### Local Development

1. **Set up virtual environment:**
```bash
cd orchestrator
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
export GCP_PROJECT_ID="your-project-id"
export PARSER_LINTER_URL="https://parser-linter-xxx-uc.a.run.app"
export REGION="us-central1"
```

3. **Test orchestrator:**
```bash
python main.py test-integration
python main.py create --prompt "Create a CCNA static routing lab"
```

### Deploying Private Services

The Parser-Linter and Headless Runner services must be built and deployed from their private repositories before running the orchestrator.

1. **Deploy Parser-Linter:**
```bash
# In netgenius-parser-linter repository (private)
gcloud builds submit --tag=us-central1-docker.pkg.dev/PROJECT/netgenius/parser-linter

# Then in this repository
./infra/scripts/deploy-parser-linter.sh
```

2. **Deploy Headless Runner:**
```bash
# In netgenius-headless-runner repository (private)
gcloud builds submit --tag=us-central1-docker.pkg.dev/PROJECT/netgenius/headless-runner

# Then in this repository
./infra/scripts/deploy-headless-runner.sh
```

## GCP Infrastructure Setup

```bash
# Set up GCP project, service accounts, GCS, Artifact Registry
./infra/scripts/setup-gcp.sh

# Deploy services (after building private images)
./infra/scripts/deploy-parser-linter.sh
./infra/scripts/deploy-headless-runner.sh
```

## Testing

### Unit Tests (Orchestrator Only)
```bash
cd orchestrator
pytest tests/
```

### Integration Tests
```bash
# Requires deployed Parser-Linter and Headless Runner
cd orchestrator
python main.py test-integration
```

### Example Lab Execution
```bash
# Run a static routing lab example
cd orchestrator
python main.py create \
  --prompt "Create a basic static routing lab with 2 routers" \
  --verbose
```

## Development Milestones

- [x] **M1 (Days 1-2):** Foundation - Infrastructure, orchestrator skeleton ← Current
- [ ] **M2 (Days 3-4):** Core agents + linting integration
- [ ] **M3 (Day 5):** Headless validation end-to-end
- [ ] **M4 (Day 6):** RCA + Publisher + polish
- [ ] **M5 (Day 7):** Demo preparation

## Documentation

- [PRD.md](PRD.md) - Product Requirements Document
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - Detailed implementation guide
- [docs/parser-linter-api.md](docs/parser-linter-api.md) - Parser-Linter API
- [docs/headless-runner-api.md](docs/headless-runner-api.md) - Headless Runner API

## How It Works

### 1. Orchestrator (Public)

The orchestrator coordinates a multi-agent workflow:

1. **Pedagogy Planner** - Extracts learning objectives from instructor prompt
2. **Designer** - Creates network topology and initial/target configurations
3. **Lab Guide Author** - Writes step-by-step student instructions
4. **Validator** - Executes headless simulation to verify lab is solvable
5. **RCA Agent** - Analyzes failures and routes fixes
6. **Publisher** - Generates final lab guide and artifacts

### 2. Parser-Linter (Private Service)

Fast validation service that catches errors before expensive simulation:

- **POST /lint/topology** - Validates YAML topology structure
- **POST /lint/cli** - Validates CLI commands (stateful/stateless)

See [API Documentation](docs/parser-linter-api.md) for details.

### 3. Headless Runner (Private Job)

Executes complete lab simulation in isolated environment:

- Applies initial configurations
- Runs student steps
- Executes verification commands
- Captures device histories and artifacts
- Writes results to GCS

See [API Documentation](docs/headless-runner-api.md) for details.

## Example Workflow

```python
# 1. Instructor provides prompt
"Create a CCNA-level OSPF lab with 2 routers and basic adjacency"

# 2. Planner extracts objectives
ExerciseSpec(
    title="OSPF Basic Adjacency",
    objectives=["Enable OSPF", "Establish adjacency", "Verify routes"],
    level="CCNA"
)

# 3. Designer creates topology + configs
# Calls: POST /lint/topology, POST /lint/cli

# 4. Author writes lab guide
# Calls: POST /lint/cli (per device section)

# 5. Validator runs simulation
# Calls: Cloud Run Job API with payload

# 6. Job writes artifacts to GCS
# Orchestrator reads summary.json

# 7. Publisher generates final lab guide
```

## License

**Orchestrator:** MIT License (open-source)
**Parser-Linter & Headless Runner:** Proprietary (closed-source)

## Hackathon Details

**Event:** Google Cloud Run Hackathon
**Owner:** Rafael Campos
**Category:** AI-Powered Automation

This public repository demonstrates the orchestration layer and architecture while keeping proprietary validation and simulation logic private.

---

**Current Status:** M1 - Foundation phase complete ✅

For questions or issues, please open a GitHub issue in this repository.
