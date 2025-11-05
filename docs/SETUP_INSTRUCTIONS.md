# NetGenius ADK Setup Instructions

## Quick Start (7-Day Hackathon Timeline)

### Day 1: Environment Setup

#### 1. Install Google ADK

```bash
cd orchestrator
pip install google-adk google-cloud-run google-cloud-storage
```

#### 2. Set Up Gemini API Key

Create `.env` file in the `orchestrator/` directory:

```bash
# orchestrator/.env
GOOGLE_API_KEY="your-gemini-api-key-here"
```

**Where to get API key:**
- Visit https://aistudio.google.com/app/apikey
- Create new API key or use existing one
- Copy and paste into `.env`

#### 3. Verify Installation

```bash
# Test ADK installation
python -c "import google.adk; print('ADK installed successfully!')"

# Initialize ADK project
adk create netgenius_orchestrator
```

---

### Day 2-3: Implement Interactive Planner (Deep Research Style)

See `docs/ADK_INTERACTIVE_PLANNER.md` for full details.

**Quick implementation:**

```python
# orchestrator/adk_agents/planner.py
from google.adk.agents import LlmAgent
from schemas.exercise_spec import ExerciseSpec

planner_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="PedagogyPlanner",
    description="Interactive planner with multi-turn Q&A",
    instruction="""
You are an expert networking instructor.

When user provides initial prompt (e.g., "teach static routing"):
1. Ask 3-5 clarifying questions:
   - Number of devices
   - Specific topics (floating routes, default routes, etc.)
   - Difficulty level
   - Time estimate

2. Wait for answers
3. Ask follow-ups if needed
4. Once complete, output ExerciseSpec JSON

IMPORTANT: If user provides detailed info upfront, skip questions.
""",
    output_key="exercise_spec",
    output_schema=ExerciseSpec
)
```

**Test with ADK Web UI:**

```bash
cd orchestrator
adk web --port 8000
```

Navigate to http://localhost:8000 and test conversation:
- "I want to teach static routing"
- Answer the questions
- Verify it produces complete ExerciseSpec

---

### Day 3-4: Implement Designer & Author Agents

```python
# orchestrator/adk_agents/designer.py
from google.adk.agents import LlmAgent
from adk_agents.tools.linter_tools import lint_topology, lint_cli

designer_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="Designer",
    instruction="""
Create Containerlab topology and Cisco IOS configs from: {exercise_spec}

1. Generate topology YAML
2. Create initial configs
3. Create target configs
4. Validate with lint_topology and lint_cli
5. Fix issues if linting fails
""",
    tools=[lint_topology, lint_cli],
    output_key="design_output",
    planner=BuiltInPlanner()  # Multi-step reasoning
)
```

```python
# orchestrator/adk_agents/author.py
author_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="LabGuideAuthor",
    instruction="""
Write student-facing lab guide from:
- {exercise_spec}
- {design_output}

Include:
- Clear objectives
- Step-by-step instructions
- Verification commands
- Troubleshooting tips

Validate commands with lint_cli tool.
""",
    tools=[lint_cli],
    output_key="draft_lab_guide"
)
```

---

### Day 5: Implement Validator & Orchestration

```python
# orchestrator/adk_agents/validator.py
from google.adk.agents import BaseAgent

class ValidatorAgent(BaseAgent):
    """Custom agent for Cloud Run Jobs validation"""

    async def run_async(self, context: InvocationContext):
        # Get artifacts from session
        draft_guide = context.session.state["draft_lab_guide"]
        design = context.session.state["design_output"]

        # Submit Cloud Run Job
        execution_id = await self._submit_job(draft_guide, design)

        # Poll and fetch results
        artifacts = await self._fetch_artifacts(execution_id)

        # Save to state
        context.session.state["validation_result"] = {
            "success": artifacts.success,
            "execution_id": execution_id
        }

        yield Event(content=f"Validation: {'PASS' if artifacts.success else 'FAIL'}")
```

```python
# orchestrator/workflows/pipeline.py
from google.adk.agents import SequentialAgent

lab_pipeline = SequentialAgent(
    name="LabCreationPipeline",
    sub_agents=[
        planner_agent,
        designer_agent,
        author_agent,
        ValidatorAgent()
    ]
)
```

---

### Day 6: CLI & Testing

```python
# orchestrator/main_adk.py
import click
from google.adk.runner import Runner
from workflows.pipeline import lab_pipeline

@click.command()
@click.option("--prompt", help="Initial instructor prompt")
def create(prompt):
    """Create lab with interactive Q&A"""

    runner = Runner(agent=lab_pipeline, app_name="netgenius")

    # Interactive mode if no prompt
    if not prompt:
        prompt = input("What lab would you like to create? ")

    # Start conversation
    session_id = f"lab_{int(time.time())}"

    events = runner.run(
        user_id="instructor",
        session_id=session_id,
        new_message=prompt
    )

    # Handle multi-turn conversation
    session = runner.session_service.get_session("instructor", session_id)

    while "exercise_spec" not in session.state:
        # Agent asking questions
        for event in events:
            print(event.content)

        # Get user answers
        answers = input("\nYour answers: ")

        # Continue conversation
        events = runner.run(
            user_id="instructor",
            session_id=session_id,
            new_message=answers
        )

        session = runner.session_service.get_session("instructor", session_id)

    # ExerciseSpec complete, pipeline continues automatically
    print("\n✓ Planning complete! Running Designer → Author → Validator...")

    # Wait for final results
    for event in events:
        print(event.content)

if __name__ == "__main__":
    create()
```

**Test:**

```bash
python main_adk.py create
# Follow interactive prompts

# Or direct:
python main_adk.py create --prompt "Create intermediate OSPF lab with 3 routers"
```

---

### Day 7: Polish & Demo Prep

#### Deploy to Cloud Run

```dockerfile
# orchestrator/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["adk", "web", "--port", "8080", "--host", "0.0.0.0"]
```

```bash
# Deploy
gcloud run deploy netgenius-orchestrator \
  --source=. \
  --region=us-central1 \
  --allow-unauthenticated \
  --set-env-vars=GOOGLE_API_KEY=$GEMINI_API_KEY
```

#### Demo Script

1. **Show Web UI**: Open ADK web interface
2. **Interactive Planning**: Type "teach static routing", answer questions
3. **Pipeline Execution**: Show Planner → Designer → Author → Validator
4. **Artifacts**: Display generated topology, configs, lab guide
5. **Validation**: Show GCS artifacts with PASS/FAIL

---

## Project Structure (ADK-Based)

```
orchestrator/
├── .env                          # Gemini API key
├── main_adk.py                   # ADK-based CLI entry point
├── requirements.txt              # google-adk, google-cloud-*
│
├── adk_agents/                   # All ADK agents
│   ├── __init__.py
│   ├── planner.py               # Interactive Q&A agent
│   ├── designer.py              # Topology & config generation
│   ├── author.py                # Lab guide writing
│   ├── validator.py             # Cloud Run Jobs integration
│   └── tools/                   # Custom tools
│       ├── linter_tools.py      # Parser-linter API wrappers
│       ├── topology_tools.py    # Containerlab helpers
│       └── gcs_tools.py         # Artifact fetching
│
├── workflows/                    # Orchestration
│   └── pipeline.py              # SequentialAgent definition
│
└── schemas/                      # Pydantic models (unchanged)
    ├── exercise_spec.py
    ├── design_output.py
    └── draft_lab_guide.py
```

**Note:** Remove old `agents/` directory and `main.py` after ADK migration is complete.

---

## Environment Variables

```bash
# orchestrator/.env

# Required
GOOGLE_API_KEY="your-gemini-api-key"

# Optional (for Cloud Run Jobs)
GCP_PROJECT_ID="netgenius-hackathon"
REGION="us-central1"
GCS_BUCKET="netgenius-artifacts-dev"
```

---

## Testing Checklist

### Planner Agent:
- [ ] Minimal prompt: "teach VLANs" → asks 5 questions
- [ ] Detailed prompt: "3 router OSPF, multi-area, 60 min" → skips questions
- [ ] Edge case: conflicting requirements → asks clarifying question
- [ ] Web UI: conversation flows naturally

### Designer Agent:
- [ ] Reads `{exercise_spec}` from session state
- [ ] Generates valid Containerlab YAML
- [ ] Creates realistic Cisco IOS configs
- [ ] Calls linter tools for validation
- [ ] Saves to `design_output` in session state

### Author Agent:
- [ ] Reads `{exercise_spec}` and `{design_output}` from state
- [ ] Generates markdown lab guide
- [ ] Includes verification commands
- [ ] Lints command sequences
- [ ] Saves to `draft_lab_guide` in state

### Validator Agent:
- [ ] Converts draft guide to runner payload
- [ ] Submits Cloud Run Job
- [ ] Polls until completion
- [ ] Fetches GCS artifacts
- [ ] Determines PASS/FAIL

### Full Pipeline:
- [ ] Runs Planner → Designer → Author → Validator sequentially
- [ ] Each agent reads from previous agent's output in state
- [ ] Final state contains all artifacts
- [ ] CLI saves outputs to disk

---

## Common Issues & Solutions

### Issue: "ModuleNotFoundError: No module named 'google.adk'"
**Solution:**
```bash
pip install google-adk
```

### Issue: "API key not found"
**Solution:** Check `.env` file exists and contains `GOOGLE_API_KEY="..."`

### Issue: "Agent not responding"
**Solution:** Check Gemini API quota/billing at https://console.cloud.google.com/

### Issue: "Linter tools failing"
**Solution:** Parser-linter not deployed yet. Use mock responses for testing:
```python
async def lint_topology(yaml_str: str) -> dict:
    return {"ok": True, "errors": []}  # Mock for now
```

---

## Next Steps

1. **Set up `.env` with your Gemini API key**
2. **Install ADK: `pip install google-adk`**
3. **Start with Planner agent** - test with `adk web`
4. **Add Designer & Author agents**
5. **Integrate Validator as Custom Agent**
6. **Test full pipeline end-to-end**
7. **Deploy to Cloud Run for demo**

Ready to start implementing! 🚀
