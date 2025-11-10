# NetGenius Instructor Copilot (NIC)

**AI-Powered Networking Lab Generator Built with Google's Agent Development Kit (ADK)**

## Overview

NetGenius Instructor Copilot (NIC) leverages **Google's Agent Development Kit (ADK)** to orchestrate multiple specialized AI agents that automate the full lifecycle of networking lab creation:

- **Planning** learning objectives through interactive multi-turn Q&A (ADK LlmAgent)
- **Designing** network topology and configurations with tool integration (ADK LlmAgent with tools)
- **Authoring** student-facing lab guides with markdown formatting (ADK LlmAgent)
- **Validating** labs via headless simulation (ADK Custom Agent)
- **Publishing** final, solvable lab materials

Built using Google ADK's multi-agent orchestration patterns powered by Gemini 2.5 Flash as the underlying LLM.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                      │
│              Interactive Lab Creation Interface              │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────────────┐
│              Orchestrator (FastAPI + Google ADK)             │
│                   Running on Cloud Run                       │
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

This repository contains **only the open-source orchestrator**. The validation and simulation service (referred to as headless runner in this README) is maintained in a separate private repository.

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
- Google Gemini API key ([Get one here](https://aistudio.google.com/app/apikey))
- Google Cloud SDK (optional, only needed for validation features)

### Running Locally

1. **Configure environment variables:**

```bash
cd orchestrator
cp .env.example .env
```

Edit `.env` and add your Google Gemini API key:

```bash
GOOGLE_API_KEY=your_google_api_key_here
```

**Required environment variables:**

- `GOOGLE_API_KEY` - Your Google Gemini API key (required for all AI agents)

**Optional environment variables** (only needed for Cloud Run Job validation):

- `GCP_PROJECT_ID` - Your GCP project ID (default: `netgenius-hackathon`)
- `REGION` - GCP region (default: `us-central1`)
- `GCS_BUCKET` - GCS bucket for artifacts (default: `netgenius-artifacts-dev`)
- `PORT` - Server port (default: `8080`)

2. **Start the orchestrator:**

```bash
cd orchestrator
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
python api_server.py
```

The orchestrator will start on http://localhost:8080

3. **Start the frontend:**

```bash
cd frontend
npm install
npm run dev
```

The frontend will start on http://localhost:3000

4. **Access the application:**

Open http://localhost:3000 in your browser.

**Note:** The validation stage requires access to the private Headless Runner service. For local development and testing, the planner, designer, and author agents will work without it.

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

The application can be tested through the web interface at http://localhost:3000. You'll see ADK's multi-agent orchestration in action:

1. Enter a lab description (e.g., "Create a basic static routing lab")
2. Interact with the Planner agent's multi-turn conversation
3. Watch ADK coordinate the agent pipeline:
   - Planner: Gathers requirements via conversational Q&A
   - Designer: Creates topology and configurations with tool validation
   - Author: Writes the lab guide using structured output
   - Validator: Runs headless simulation through custom integration

## Documentation

- [PRD.md](PRD.md) - Product Requirements Document
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - Detailed implementation guide
- [docs/headless-runner-api.md](docs/headless-runner-api.md) - Headless Runner API

## How It Works

### Google ADK Multi-Agent Workflow

The orchestrator leverages **Google ADK's agent orchestration capabilities** to coordinate specialized AI agents in a sequential pipeline:

1. **Pedagogy Planner** (`LlmAgent`) - Engages in multi-turn Q&A conversations to gather complete lab requirements using ADK's session management
2. **Designer** (`LlmAgent` with tools) - Creates network topology and configurations, utilizing ADK's tool integration patterns to validate outputs
3. **Lab Guide Author** (`LlmAgent`) - Writes step-by-step student instructions with markdown, leveraging ADK's structured output capabilities
4. **Validator** (Custom `BaseAgent`) - Executes headless simulation to verify lab is solvable, demonstrating ADK's extensibility for custom integrations

Each agent communicates through ADK's **session state**, enabling seamless data flow between agents without manual state management. The entire pipeline is orchestrated using ADK's `SequentialAgent` pattern, providing automatic error handling and retry logic.

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

2. Planner (ADK LlmAgent) asks clarifying questions via multi-turn session:
   - Which password types? (enable, console, VTY)
   - How many routers?
   - Target difficulty and time?

3. Designer (ADK LlmAgent with tools) creates validated outputs:
   - Topology YAML with router(s)
   - Initial configs (base setup)
   - Target configs (with passwords configured)

4. Author (ADK LlmAgent) writes structured markdown:
   - Introduction and objectives
   - Step-by-step instructions
   - Verification commands

5. Validator (Custom ADK Agent) runs simulation via external service:
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

NetGenius Instructor Copilot demonstrates how **Google's Agent Development Kit (ADK)** combined with Cloud Run enables scalable, event-driven AI agent orchestration. The application showcases ADK's multi-agent coordination patterns (LlmAgent, custom agents, session management) running seamlessly on Cloud Run Services, with validation workloads executing as Cloud Run Jobs.

---

For questions or issues, please open a GitHub issue in this repository.
