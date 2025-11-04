# NetGenius - AI-Powered Networking Lab Generator

**Status:** M1 Development (Foundation)
**Platform:** Google Cloud (Cloud Run + Cloud Run Jobs)
**Architecture:** Multi-agent system using Google ADK

## Overview

NetGenius automates the full lifecycle of networking lab creation for instructors:
- 📋 Planning learning objectives
- 🏗️ Designing network topology and configurations
- ✍️ Authoring student-facing lab guides
- ✅ Validating labs via headless simulation
- 📦 Publishing final, solvable lab materials

## Architecture

```
┌─────────────────┐
│  Orchestrator   │ (Public/Open-Source)
│    (ADK)        │
└────────┬────────┘
         │
    ┌────┴────┬─────────────┐
    │         │             │
┌───▼────┐ ┌──▼───────┐ ┌──▼────────┐
│Parser- │ │ Headless │ │    GCS    │
│Linter  │ │  Runner  │ │ Artifacts │
│(Private)│ │(Private) │ └───────────┘
└────────┘ └──────────┘
```

## Components

| Component | Description | Visibility |
|-----------|-------------|------------|
| **Orchestrator** | Multi-agent coordination via Google ADK | Public (open-source) |
| **Parser-Linter** | Fast CLI/topology validation service | Private (closed-source) |
| **Headless Runner** | Simulation execution in Cloud Run Jobs | Private (closed-source) |

## Project Structure

```
cloud-run-hackathon/
├── orchestrator/          # ADK-based orchestration (public)
│   ├── agents/           # Planner, Designer, Author, Validator, RCA, Publisher
│   ├── tools/            # Parser-linter, headless-runner tool wrappers
│   └── schemas/          # Data models for agent communication
├── parser-linter/        # Validation service (private)
│   ├── routers/          # FastAPI endpoints
│   └── linter/           # CLI/topology validation logic
├── headless-runner/      # Simulation runner (private)
│   ├── runner/           # Execution engine
│   └── simulator/        # Proprietary simulator integration
├── infra/                # Terraform and deployment scripts
└── examples/             # Sample labs for testing
```

## Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud SDK
- Docker (for local testing)

### Local Development

1. **Set up virtual environment:**
```bash
cd orchestrator
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

2. **Run Parser-Linter service locally:**
```bash
cd parser-linter
pip install -r requirements.txt
python main.py  # Runs on http://localhost:8080
```

3. **Test orchestrator:**
```bash
cd orchestrator
python main.py test-integration
```

### Testing Services

```bash
# Test parser-linter health
curl http://localhost:8080/health

# Test topology linting
curl -X POST http://localhost:8080/lint/topology \
  -H "Content-Type: application/json" \
  -d '{"topology_yaml": "devices:\n  r1:\n    type: router"}'

# Test CLI linting
curl -X POST http://localhost:8080/lint/cli \
  -H "Content-Type: application/json" \
  -d '{
    "device_type": "cisco_2911",
    "sequence_mode": "stateful",
    "commands": [{"command": "configure terminal"}]
  }'
```

## Development Milestones

- [x] **M1 (Days 1-2):** Foundation - Infrastructure, skeleton services ← Current
- [ ] **M2 (Days 3-4):** Core agents + linting integration
- [ ] **M3 (Day 5):** Headless validation end-to-end
- [ ] **M4 (Day 6):** RCA + Publisher + polish
- [ ] **M5 (Day 7):** Demo preparation

## Documentation

- [PRD.md](PRD.md) - Product Requirements Document
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - Detailed implementation guide
- [docs/api-reference.md](docs/api-reference.md) - API documentation (coming in M2)

## License

- **Orchestrator:** Open-source (license TBD)
- **Parser-Linter & Headless Runner:** Proprietary/Closed-source

## Contact

**Owner:** Rafael Campos
**Project:** Google Cloud Run Hackathon

---

**Current Status:** M1 - Foundation phase complete ✅
