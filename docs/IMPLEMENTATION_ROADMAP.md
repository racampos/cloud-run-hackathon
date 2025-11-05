# NetGenius Implementation Roadmap

**Purpose:** Step-by-step execution guide for implementing the ADK-based architecture
**Reference:** See `IMPLEMENTATION_PLAN.md` for milestone definitions and complete code examples
**Timeline:** 7 days (hackathon cadence)

---

## Overview

This roadmap provides a **tactical, day-by-day breakdown** of how to implement the milestones defined in `IMPLEMENTATION_PLAN.md`. Each day maps to one or more milestones with specific tasks and verification steps.

**Key Principle:** Build incrementally, test continuously, commit frequently.

---

## Pre-Work: Environment Setup

**Maps to:** `IMPLEMENTATION_PLAN.md` → **M0: Setup & Environment Configuration**

**Before starting Day 1, complete these setup tasks:**

### 1. Install Google ADK
```bash
cd orchestrator
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install google-adk google-cloud-run google-cloud-storage
```

### 2. Configure Gemini API Key
```bash
# Create .env file
cat > orchestrator/.env << EOF
GOOGLE_API_KEY="your-gemini-api-key-here"
GCP_PROJECT_ID="netgenius-hackathon"
REGION="us-central1"
GCS_BUCKET="netgenius-artifacts-dev"
EOF
```

Get your API key from: https://aistudio.google.com/app/apikey

### 3. Verify ADK Installation
```bash
adk --version
# Should output: adk version 0.2.x

# Test ADK web UI
adk web --port 8000
# Navigate to http://localhost:8000 - should see ADK interface
```

### 4. Set Up GCP Project
```bash
# Run infrastructure setup
cd infra/scripts
chmod +x setup-gcp.sh
./setup-gcp.sh

# Verify GCS bucket created
gsutil ls gs://netgenius-artifacts-dev
```

**Checkpoint:** ✅ ADK installed, API key configured, GCP project ready

---

## Day 1: Interactive Planner Agent

**Maps to:** `IMPLEMENTATION_PLAN.md` → **M1: Interactive Planner Agent**

**Goal:** Implement multi-turn Q&A planner that refines vague prompts into complete ExerciseSpec

### Morning: Schema & Agent Setup

**Tasks:**
1. Create directory structure
```bash
cd orchestrator
mkdir -p adk_agents adk_agents/tools workflows schemas tests
```

2. Implement ExerciseSpec schema
```bash
# Edit schemas/exercise_spec.py
# See IMPLEMENTATION_PLAN.md M1 for complete Pydantic model
```

3. Implement Planner agent
```bash
# Edit adk_agents/planner.py
# See IMPLEMENTATION_PLAN.md M1 for complete LlmAgent definition
```

**Key Focus:**
- `LlmAgent` with `model="gemini-2.5-flash"`
- `instruction` with question templates for each lab type
- `output_key="exercise_spec"`
- `output_schema=ExerciseSpec`

### Afternoon: Testing & Validation

**Tasks:**
1. Test with ADK web UI
```bash
cd orchestrator
adk web --port 8000
```

**Test Cases:**
- Input: "teach static routing" → Should ask 3-5 clarifying questions
- Input: "3 router OSPF lab, intermediate level, 45 minutes" → Should skip questions, output ExerciseSpec

2. Write unit tests
```bash
# Edit tests/test_planner.py
# See IMPLEMENTATION_PLAN.md Section 7.1 for test examples
```

3. Run tests
```bash
pytest tests/test_planner.py -v
```

**Checkpoint:** ✅ Planner asks questions for vague prompts, skips for detailed prompts

**Commit:** `git commit -m "M1: Implement interactive planner with ADK LlmAgent"`

---

## Day 2: Designer Agent with Linting Tools

**Maps to:** `IMPLEMENTATION_PLAN.md` → **M2: Designer Agent with Linting Integration**

**Goal:** Generate topology + configs, validate with linter tools

### Morning: Linter Tools (Mocked)

**Tasks:**
1. Implement linter tool wrappers
```bash
# Edit adk_agents/tools/linter_tools.py
# See IMPLEMENTATION_PLAN.md M2 for complete implementation
```

**Key Points:**
- Return mock responses if `PARSER_LINTER_URL` not set
- Implement both `lint_topology()` and `lint_cli()`
- Functions automatically become ADK tools

2. Implement DesignOutput schema
```bash
# Edit schemas/design_output.py
```

### Afternoon: Designer Agent Implementation

**Tasks:**
1. Implement Designer agent
```bash
# Edit adk_agents/designer.py
# See IMPLEMENTATION_PLAN.md M2 for complete LlmAgent with tools
```

**Key Features:**
- Reads `{exercise_spec}` from session state
- Uses `lint_topology` and `lint_cli` tools
- `planner=BuiltInPlanner()` for multi-step reasoning
- Retry logic built into LLM instruction

2. Test Designer in isolation
```bash
# Create test script that injects exercise_spec into session
python -c "
from google.adk.runner import Runner
from adk_agents.designer import designer_agent

runner = Runner(agent=designer_agent)
session = runner.session_service.get_session('test', 'test')

# Inject exercise_spec
session.state['exercise_spec'] = {
    'lab_type': 'static_routing',
    'devices': [{'hostname': 'R1'}, {'hostname': 'R2'}],
    'level': 'beginner'
}

# Run designer
events = runner.run(user_id='test', session_id='test', new_message='Create design')

# Check output
print(session.state['design_output'])
"
```

**Checkpoint:** ✅ Designer generates topology YAML and configs with linting

**Commit:** `git commit -m "M2: Implement Designer agent with linting tools"`

---

## Day 3: Author Agent & Pipeline Connection

**Maps to:**
- `IMPLEMENTATION_PLAN.md` → **M3: Author Agent**
- `IMPLEMENTATION_PLAN.md` → **M5: Pipeline Orchestration** (partial)

**Goal:** Generate lab guides and connect Planner → Designer → Author

### Morning: Author Agent

**Tasks:**
1. Implement DraftLabGuide schema
```bash
# Edit schemas/draft_lab_guide.py
```

2. Implement Author agent
```bash
# Edit adk_agents/author.py
# See IMPLEMENTATION_PLAN.md M3 for complete implementation
```

**Key Features:**
- Reads `{exercise_spec}` and `{design_output}` from session
- Generates markdown lab guide
- Uses `lint_cli` to validate command sequences

### Afternoon: Connect Pipeline (Planner → Designer → Author)

**Tasks:**
1. Create pipeline orchestration
```bash
# Edit workflows/pipeline.py
from google.adk.agents import SequentialAgent
from adk_agents.planner import planner_agent
from adk_agents.designer import designer_agent
from adk_agents.author import author_agent

lab_creation_pipeline = SequentialAgent(
    name="LabCreationPipeline",
    description="Planning → Design → Authoring",
    sub_agents=[
        planner_agent,
        designer_agent,
        author_agent
    ]
)
```

2. Test partial pipeline
```bash
# Create test with injected exercise_spec
# Verify Designer → Author flow works
```

**Checkpoint:** ✅ Pipeline runs Planner → Designer → Author successfully

**Commit:** `git commit -m "M3: Implement Author agent and connect partial pipeline"`

---

## Day 4: Validator Agent (Cloud Run Jobs)

**Maps to:** `IMPLEMENTATION_PLAN.md` → **M4: Validator as Custom Agent**

**Goal:** Execute headless validation and fetch GCS artifacts

### Morning: Validator Custom Agent

**Tasks:**
1. Implement ValidatorAgent extending BaseAgent
```bash
# Edit adk_agents/validator.py
# See IMPLEMENTATION_PLAN.md M4 for complete Custom Agent implementation
```

**Key Methods:**
- `run_async(context: InvocationContext)` - Main entry point
- `_convert_payload()` - DraftLabGuide → runner JSON
- `_submit_job()` - Cloud Run Jobs API call
- `_poll_job()` - Status polling loop
- `_fetch_artifacts()` - GCS download

2. Test Validator in isolation
```bash
# Mock Cloud Run Job response for testing
# Or deploy headless-runner if ready
```

### Afternoon: Full Pipeline Integration

**Tasks:**
1. Add Validator to pipeline
```bash
# Edit workflows/pipeline.py
from adk_agents.validator import ValidatorAgent

lab_creation_pipeline = SequentialAgent(
    sub_agents=[
        planner_agent,
        designer_agent,
        author_agent,
        ValidatorAgent()  # Add validator
    ]
)
```

2. Test with mock/real Cloud Run Job
```bash
# If headless-runner deployed:
gcloud run jobs execute headless-runner \
  --region=us-central1 \
  --wait
```

**Checkpoint:** ✅ Full pipeline runs Planner → Designer → Author → Validator

**Commit:** `git commit -m "M4: Implement Validator custom agent with Cloud Run Jobs"`

---

## Day 5: Interactive CLI & Multi-Turn Conversations

**Maps to:** `IMPLEMENTATION_PLAN.md` → **M5: Pipeline Orchestration** (complete)

**Goal:** Build CLI that handles interactive Q&A and displays results

### Morning: CLI Implementation

**Tasks:**
1. Implement main CLI entry point
```bash
# Edit main_adk.py
# See IMPLEMENTATION_PLAN.md M5 for complete implementation
```

**Key Features:**
- Multi-turn conversation loop for planner
- Pretty-printed progress updates
- Artifact saving to disk

2. Test interactive flow
```bash
cd orchestrator
python main_adk.py create

# Test conversation:
# > "teach static routing"
# [Answer questions]
# [Watch pipeline execute]
# [See final results]
```

### Afternoon: Artifact Saving & Output Formatting

**Tasks:**
1. Implement artifact saving function
```python
def _save_artifacts(state):
    """Save all outputs to disk"""
    # exercise_spec.json
    # design_output.json
    # topology.yaml
    # lab_guide.md
    # validation/summary.json
```

2. Add pretty printing with Rich
```python
from rich.console import Console
from rich.progress import Progress

console = Console()
# Use console.print() for colored output
# Use Progress() for status indicators
```

3. Test end-to-end with artifact verification
```bash
python main_adk.py create --prompt "VLAN lab with 2 switches"

# Verify outputs:
ls -la ./output/
# Should contain: exercise_spec.json, design_output.json, lab_guide.md
```

**Checkpoint:** ✅ CLI handles full conversation and saves all artifacts

**Commit:** `git commit -m "M5: Complete pipeline orchestration with interactive CLI"`

---

## Day 6: Testing, Polish & Documentation

**Maps to:** `IMPLEMENTATION_PLAN.md` → **M6: Testing & Polish**

**Goal:** Comprehensive testing, error handling, documentation

### Morning: Unit & Integration Tests

**Tasks:**
1. Write unit tests for each agent
```bash
# tests/test_planner.py
# tests/test_designer.py
# tests/test_author.py
# tests/test_validator.py
```

2. Write integration tests
```bash
# tests/test_pipeline.py
# See IMPLEMENTATION_PLAN.md Section 7.2 for examples
```

3. Run full test suite
```bash
pytest tests/ -v --cov=adk_agents --cov=workflows
```

### Afternoon: Error Handling & Documentation

**Tasks:**
1. Add error handling
- Missing API key → Clear error message
- Linting failures → Retry logic in instructions
- Cloud Run Job failures → Graceful degradation
- GCS fetch failures → Retry with backoff

2. Update documentation
```bash
# Edit README.md with quickstart
# Edit docs/SETUP_INSTRUCTIONS.md with troubleshooting
# Create docs/CLI_USAGE.md with examples
```

3. Create example labs
```bash
# examples/static-routing/payload.json
# examples/vlan-basic/payload.json
# examples/ospf-two-router/payload.json
```

**Checkpoint:** ✅ All tests pass, examples work, docs complete

**Commit:** `git commit -m "M6: Add comprehensive testing and documentation"`

---

## Day 7: Deployment & Demo Preparation

**Maps to:** `IMPLEMENTATION_PLAN.md` → **M7: Deployment & Demo Preparation**

**Goal:** Deploy to Cloud Run, prepare demo materials

### Morning: Cloud Run Deployment

**Tasks:**
1. Build and deploy
```bash
cd orchestrator

# Build container
gcloud builds submit --tag us-central1-docker.pkg.dev/netgenius-hackathon/netgenius/orchestrator

# Deploy to Cloud Run
gcloud run deploy netgenius-orchestrator \
  --image us-central1-docker.pkg.dev/netgenius-hackathon/netgenius/orchestrator \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=$GEMINI_API_KEY,GCP_PROJECT_ID=netgenius-hackathon
```

2. Test deployed service
```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe netgenius-orchestrator \
  --region us-central1 \
  --format 'value(status.url)')

# Test web UI
open $SERVICE_URL
```

### Afternoon: Demo Preparation

**Tasks:**
1. **Create demo script** (docs/DEMO_SCRIPT.md)
   - Introduction (2 min)
   - Interactive planning demo (3 min)
   - Pipeline execution walkthrough (5 min)
   - Artifacts showcase (3 min)
   - Architecture explanation (5 min)
   - Q&A (2 min)

2. **Prepare presentation slides**
   - Problem statement
   - ADK architecture diagram
   - Agent interaction flow
   - Live demo
   - Results & artifacts
   - Tech stack (Google Cloud + ADK)

3. **Record backup demo video**
   - In case live demo fails
   - Shows complete flow
   - 5-10 minutes max

4. **Polish GitHub repo**
   - Clean README
   - Clear examples
   - Complete documentation
   - Architecture diagrams

**Checkpoint:** ✅ Service deployed, demo ready, backup prepared

**Commit:** `git commit -m "M7: Deploy to Cloud Run and prepare demo materials"`

---

## Daily Checklist Template

Use this for each day:

**Morning:**
- [ ] Review milestone goals (IMPLEMENTATION_PLAN.md)
- [ ] Pull latest code
- [ ] Activate virtual environment
- [ ] Run existing tests to ensure nothing broke

**During Implementation:**
- [ ] Follow code examples from IMPLEMENTATION_PLAN.md
- [ ] Test incrementally (don't wait until end of day)
- [ ] Commit frequently with clear messages
- [ ] Document any deviations or issues

**End of Day:**
- [ ] Run full test suite
- [ ] Verify checkpoint criteria met
- [ ] Commit final changes
- [ ] Update progress in this document
- [ ] Preview next day's tasks

---

## Troubleshooting Guide

### Issue: "ModuleNotFoundError: No module named 'google.adk'"
**Solution:**
```bash
pip install google-adk
# or
pip install -r requirements.txt
```

### Issue: "API key not found"
**Solution:**
```bash
# Verify .env file exists and contains GOOGLE_API_KEY
cat orchestrator/.env

# Ensure ADK loads .env (ADK does this automatically)
```

### Issue: "Planner doesn't ask questions"
**Solution:**
- Check `instruction` includes question templates
- Test with vague prompt: "teach static routing" (no details)
- Verify `output_schema=ExerciseSpec` is set
- Check ADK web UI for conversation history

### Issue: "Designer/Author linting fails"
**Solution:**
- Verify mock linter tools return `{"ok": True, ...}`
- Check `PARSER_LINTER_URL` is NOT set (for testing with mocks)
- Review LLM instruction - should include retry logic

### Issue: "Validator Cloud Run Job fails"
**Solution:**
```bash
# Check if job exists
gcloud run jobs describe headless-runner --region us-central1

# Check job logs
gcloud run jobs executions list --job headless-runner --region us-central1

# Verify GCS bucket permissions
gsutil iam get gs://netgenius-artifacts-dev
```

### Issue: "Pipeline doesn't connect agents"
**Solution:**
- Verify `SequentialAgent` has all sub_agents
- Check `output_key` matches what next agent expects
- Inspect `session.state` to see what's actually stored
- Review agent `instruction` for placeholder syntax: `{exercise_spec}`

---

## Progress Tracking

**Completed Milestones:**

- [ ] M0: Setup & Environment Configuration
- [ ] M1: Interactive Planner Agent
- [ ] M2: Designer Agent with Linting
- [ ] M3: Author Agent
- [ ] M4: Validator Agent
- [ ] M5: Pipeline Orchestration
- [ ] M6: Testing & Polish
- [ ] M7: Deployment & Demo

**Current Status:** [Update daily]

**Blockers:** [List any blockers and resolution plans]

**Next Steps:** [What to tackle next]

---

## Key Success Indicators

By end of Day 7, you should have:

✅ All 4 agents implemented with ADK patterns
✅ Full pipeline running (Planner → Designer → Author → Validator)
✅ Interactive Q&A working in web UI
✅ Tests passing (unit + integration)
✅ Service deployed to Cloud Run
✅ 3 example labs working (static routing, VLAN, OSPF)
✅ Demo script prepared with backup materials
✅ GitHub repo polished and public

---

**Document Purpose:** Tactical execution guide - use alongside `IMPLEMENTATION_PLAN.md` (strategic) and `docs/SETUP_INSTRUCTIONS.md` (environment setup)

**Last Updated:** 2025-01-05
