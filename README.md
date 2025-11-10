# NetGenius Instructor Copilot (NIC)

**AI-Powered Networking Lab Generator**

**Status:** M1 Development (Foundation)
**Platform:** Google Cloud (Cloud Run + Cloud Run Jobs)
**Architecture:** Multi-agent system using Google ADK
**Repository:** Public (Orchestrator only)

## Overview

NetGenius Instructor Copilot (NIC) automates the full lifecycle of networking lab creation for instructors:

- Planning learning objectives
- Designing network topology and configurations
- Authoring student-facing lab guides
- Validating labs via headless simulation
- Publishing final, solvable lab materials

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                      │
│              Interactive Lab Creation Interface              │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────────────┐
│              Orchestrator (FastAPI + Google ADK)             │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐     │
│  │ Planner  │→ │ Designer │→ │  Author  │→ │ Validator │     │
│  └──────────┘  └──────────┘  └──────────┘  └─────┬─────┘     │
└──────────────────────────────────────────────────┼───────────┘
                                                   │
                                          ┌────────┴───────────┐
                                          │  Headless Runner   │
                                          │  (Private)         │
                                          │  Cloud Run Job     │
                                          └──────────┬─────────┘
                                                     │
                                          ┌──────────┴─────────┐
                                          │    GCS Artifacts   │
                                          └────────────────────┘
```

## Repository Structure

This repository contains **only the open-source orchestrator**. The validation and simulation services are maintained in separate private repositories.

### This Repository (Public)

```
cloud-run-hackathon/
├── orchestrator/          # ADK-based multi-agent orchestrator
│   ├── adk_agents/       # Planner, Designer, Author, Validator agents
│   ├── tools/            # Tool wrappers for private services
│   └── schemas/          # Data models for agent communication
├── frontend/             # Next.js web interface
│   ├── components/       # React components for lab creation UI
│   └── app/             # Next.js app router pages
├── docs/                 # API documentation
│   └── headless-runner-api.md   # Headless Runner API contract
├── infra/                # GCP infrastructure and deployment
│   └── scripts/          # Setup and deployment scripts
├── examples/             # Sample labs and payloads
│   └── static-routing/   # Example static routing lab
└── README.md             # This file
```

### Private Repositories (Not Included)

**netgenius-headless-runner** (Private)

- Network simulation execution engine
- Proprietary simulator integration
- GCS artifact generation
- Deployed as Cloud Run Job

## Components

| Component           | Description                             | Visibility         | Deployment        |
| ------------------- | --------------------------------------- | ------------------ | ----------------- |
| **Frontend**        | Next.js web interface for lab creation  | Public (this repo) | Vercel            |
| **Orchestrator**    | Multi-agent coordination via Google ADK | Public (this repo) | Cloud Run Service |
| **Headless Runner** | Simulation execution in Cloud Run Jobs  | Private            | Cloud Run Job     |

## API Documentation

The Headless Runner source code is private, but its API contract is fully documented:

- [Headless Runner API Reference](docs/headless-runner-api.md) - Job payload and artifact formats

The orchestrator integrates with the Headless Runner via a well-defined job execution interface.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Google Cloud SDK
- Access to deployed Headless Runner service

### Running Locally

1. **Start the orchestrator:**

```bash
cd orchestrator
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
python api_server.py
```

2. **Start the frontend:**

```bash
cd frontend
npm install
npm run dev
```

3. **Access the application:**

Open http://localhost:3000 in your browser.

### Deploying to Production

The Headless Runner service must be built and deployed from its private repository before running the orchestrator.

1. **Deploy Headless Runner:**

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

# Deploy Headless Runner (after building private image)
./infra/scripts/deploy-headless-runner.sh
```

## Testing

The application can be tested through the web interface at http://localhost:3000. Simply:

1. Enter a lab description (e.g., "Create a basic static routing lab")
2. Answer any clarifying questions from the Planner
3. Watch the agents work through the workflow:
   - Planner: Gathers requirements
   - Designer: Creates topology and configurations
   - Author: Writes the lab guide
   - Validator: Runs headless simulation

## Documentation

- [PRD.md](PRD.md) - Product Requirements Document
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - Detailed implementation guide
- [docs/headless-runner-api.md](docs/headless-runner-api.md) - Headless Runner API

## How It Works

### Multi-Agent Workflow

The orchestrator coordinates a multi-agent workflow using Google ADK:

1. **Pedagogy Planner** - Engages in Q&A to gather complete lab requirements
2. **Designer** - Creates network topology and initial/target configurations
3. **Lab Guide Author** - Writes step-by-step student instructions with markdown
4. **Validator** - Executes headless simulation to verify lab is solvable

### Headless Runner (Private Service)

Executes complete lab simulation in isolated Cloud Run Job:

- Applies initial configurations
- Runs student steps
- Executes verification commands
- Captures device histories and artifacts
- Writes results to GCS

See [API Documentation](docs/headless-runner-api.md) for details.

## Example Workflow

```
1. Instructor enters prompt: "Create a password configuration lab"

2. Planner asks clarifying questions:
   - Which password types? (enable, console, VTY)
   - How many routers?
   - Target difficulty and time?

3. Designer creates:
   - Topology YAML with router(s)
   - Initial configs (base setup)
   - Target configs (with passwords configured)

4. Author writes lab guide:
   - Introduction and objectives
   - Step-by-step instructions
   - Verification commands

5. Validator runs simulation:
   - Triggers Cloud Run Job
   - Applies configs and tests student steps
   - Returns success/failure with detailed logs

```

## License

**Frontend & Orchestrator:** MIT License (open-source)
**Headless Runner:** Proprietary (closed-source)

## Hackathon Details

**Event:** Google Cloud Run Hackathon
**Team:** Rafael Campos
**Category:** AI-Powered Automation
**Stack:** Google ADK (Gemini 2.5 Flash) + FastAPI + Next.js + Cloud Run + Cloud Run Jobs

NetGenius Instructor Copilot demonstrates how Google Cloud Run and Cloud Run Jobs enable scalable, event-driven AI agent orchestration with seamless integration between web frontend, multi-agent backend, and batch simulation workloads.

---

For questions or issues, please open a GitHub issue in this repository.
