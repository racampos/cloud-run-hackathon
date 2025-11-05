# NetGenius ADK Implementation

This directory contains the Google ADK-powered multi-agent orchestrator for NetGenius lab creation.

## Architecture

The system uses **Google ADK (Agent Development Kit)** to orchestrate four specialized agents in a sequential pipeline:

```
User Prompt → Planner → Designer → Author → Validator → Output
```

### Agents

1. **Planner Agent** (`adk_agents/planner.py`)
   - Type: `LlmAgent` with Gemini 2.5 Flash
   - Purpose: Interactive Q&A to gather complete lab requirements
   - Input: User's initial prompt (e.g., "teach static routing")
   - Output: `ExerciseSpec` (objectives, device count, level, time estimate)
   - Features: Multi-turn conversation, Deep Research-style interaction

2. **Designer Agent** (`adk_agents/designer.py`)
   - Type: `LlmAgent` with Gemini 2.5 Flash + BuiltInPlanner
   - Purpose: Create network topology and configurations
   - Input: `ExerciseSpec` from Planner
   - Output: `DesignOutput` (topology YAML, configs, platforms)
   - Tools: `lint_topology`, `lint_cli` (parser-linter integration)
   - Features: Automatic validation and retry on linting errors

3. **Author Agent** (`adk_agents/author.py`)
   - Type: `LlmAgent` with Gemini 2.5 Flash
   - Purpose: Write student-facing lab guide
   - Input: `ExerciseSpec` + `DesignOutput`
   - Output: `DraftLabGuide` (markdown + structured JSON)
   - Tools: `lint_cli` (validate commands in instructions)
   - Features: Step-by-step instructions with verification

4. **Validator Agent** (`adk_agents/validator.py`)
   - Type: Custom `BaseAgent` (extends ADK's BaseAgent)
   - Purpose: Headless validation via Cloud Run Jobs
   - Input: `DraftLabGuide` + `DesignOutput`
   - Output: `validation_result` (success/failure + artifacts)
   - Features: Submits job, polls for completion, fetches GCS artifacts

### Pipeline

**Sequential Pipeline** (`adk_agents/pipeline.py`):
- Orchestrates all four agents in order
- Each agent reads from and writes to session state
- Automatic data flow: Planner → Designer → Author → Validator
- Available variants:
  - `lab_creation_pipeline`: Full pipeline with validation
  - `lab_creation_pipeline_no_validation`: Skip validator (for testing)

## Setup

### 1. Install Dependencies

```bash
cd orchestrator
pip install -r requirements.txt
```

This installs:
- `google-adk>=1.17.0`
- Google Cloud libraries
- Pydantic, Rich, Click, etc.

### 2. Configure API Key

Create `.env` file:

```bash
# orchestrator/.env
GOOGLE_API_KEY="your-gemini-api-key-here"
GCP_PROJECT_ID="netgenius-hackathon"
REGION="us-central1"
GCS_BUCKET="netgenius-artifacts-dev"
```

Get API key from: https://aistudio.google.com/app/apikey

### 3. Verify Setup

```bash
python test_adk_setup.py
```

Expected output:
```
✓ GOOGLE_API_KEY found
✓ google.adk imported successfully
✓ ADK components imported
✓ ExerciseSpec schema imported
✓ Planner agent loaded: PedagogyPlanner
✓ All setup tests passed!
```

## Usage

### Full Pipeline (with validation)

```bash
python main_adk.py create
```

Interactive mode:
```
What lab would you like to create? teach static routing

Agent: I'll help you design a static routing lab! Let me ask a few questions:

1. How many routers would you like in the topology? (2-4 recommended)
2. Would you like to teach floating static routes for redundancy?
3. Should we include default static routes (0.0.0.0/0)?
4. What difficulty level? (Beginner / Intermediate / Advanced)
5. Estimated completion time? (30 min / 45 min / 60 min)

Your answer: 3 routers, yes include floating routes, intermediate, 45 minutes

Agent: Perfect! Creating lab specification...
[Pipeline runs: Planner → Designer → Author → Validator]

✓ Lab creation pipeline completed!
✓ Exercise spec saved: output/exercise_spec.json
✓ Design output saved: output/design_output.json
✓ Draft lab guide saved: output/draft_lab_guide.md
✓ Validation result saved: output/validation_result.json
✓ Headless validation PASSED
```

### Dry Run (skip validation)

```bash
python main_adk.py create --dry-run
```

Runs Planner → Designer → Author only (no Cloud Run Jobs validation).

### With Initial Prompt

```bash
python main_adk.py create --prompt "Create an intermediate OSPF lab with 3 routers"
```

If prompt is complete, Planner skips Q&A and proceeds directly to design.

### Custom Output Directory

```bash
python main_adk.py create --output /path/to/output
```

## Testing Individual Agents

### Test Planner (Interactive Q&A)

```bash
python test_planner_interactive.py
```

Tests the multi-turn conversation flow.

### Test Designer

```python
from google.adk.runner import Runner
from google.adk.session import InMemorySessionService
from adk_agents.designer import designer_agent

session_service = InMemorySessionService()
runner = Runner(agent=designer_agent, app_name="test", session_service=session_service)

# Manually add exercise_spec to session state
session = session_service.create_session("user1", "session1")
session.state["exercise_spec"] = {...}  # ExerciseSpec dict

# Run designer
events = runner.run(user_id="user1", session_id="session1", new_message="Create design")

# Check output
design_output = session.state.get("design_output")
```

## Session State Flow

ADK automatically manages state across agents via `session.state`:

1. **After Planner**:
   - `session.state["exercise_spec"]` = ExerciseSpec JSON

2. **After Designer**:
   - `session.state["design_output"]` = DesignOutput JSON

3. **After Author**:
   - `session.state["draft_lab_guide"]` = DraftLabGuide JSON

4. **After Validator**:
   - `session.state["validation_result"]` = Validation result JSON

Each agent reads from state (inputs) and writes to state (outputs).

## Files

```
orchestrator/
├── adk_agents/
│   ├── __init__.py           # Agent exports
│   ├── planner.py            # Interactive Planner (LlmAgent)
│   ├── designer.py           # Designer (LlmAgent + tools)
│   ├── author.py             # Author (LlmAgent + tools)
│   ├── validator.py          # Validator (Custom BaseAgent)
│   └── pipeline.py           # SequentialAgent pipeline
├── main_adk.py               # CLI entry point
├── test_adk_setup.py         # Setup verification
├── test_planner_interactive.py  # Planner Q&A test
├── .env                      # API keys (gitignored)
├── requirements.txt          # Dependencies
└── README_ADK.md             # This file
```

## Differences from Legacy Implementation

| Aspect | Legacy (`agents/`) | ADK (`adk_agents/`) |
|--------|-------------------|---------------------|
| LLM Integration | None (templates only) | Gemini 2.5 Flash via ADK |
| Planner UX | Template-based extraction | Multi-turn Q&A (Deep Research style) |
| Designer | Template generation | LLM-generated with validation retry |
| Author | Template generation | LLM-generated instructions |
| Validator | Direct Cloud Run API | ADK BaseAgent wrapper |
| Orchestration | Custom async workflow | ADK SequentialAgent |
| State Management | Manual dict passing | ADK session.state (automatic) |
| Tool Integration | Direct function calls | ADK tool wrapping |

## ADK Features Used

- **LlmAgent**: Gemini-powered agents with instructions and tools
- **BuiltInPlanner**: Multi-step reasoning for complex tasks (Designer)
- **BaseAgent**: Custom agent class for non-LLM workflows (Validator)
- **SequentialAgent**: Orchestration of sub-agents in order
- **Runner**: Execution engine with session management
- **InMemorySessionService**: Session state persistence
- **InvocationContext**: Access to session state within agents
- **Tool Integration**: Automatic Python function → ADK tool conversion

## Next Steps

1. **Add your Gemini API key** to `.env`
2. **Test the Planner**: `python test_planner_interactive.py`
3. **Run the full pipeline**: `python main_adk.py create --dry-run`
4. **Deploy parser-linter** and remove mock responses
5. **Deploy headless-runner** and test full validation

## Troubleshooting

**"GOOGLE_API_KEY not found"**
- Add API key to `orchestrator/.env`
- Get key from https://aistudio.google.com/app/apikey

**"Failed to import google.adk"**
- Run `pip install google-adk`
- Ensure using Python 3.10+

**Linter returns errors**
- Parser-linter service must be deployed
- Update `PARSER_LINTER_URL` in `.env`
- For testing, use `--dry-run` mode

**Validation fails**
- Headless-runner service must be deployed
- Check GCP credentials and permissions
- Verify GCS bucket exists
- Use `--dry-run` to skip validation

## Documentation

- ADK Integration Plan: `docs/ADK_INTEGRATION_PLAN.md`
- Interactive Planner Guide: `docs/ADK_INTERACTIVE_PLANNER.md`
- Implementation Plan: `IMPLEMENTATION_PLAN.md`
- Setup Instructions: `docs/SETUP_INSTRUCTIONS.md`
