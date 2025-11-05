# Google ADK Integration Plan for NetGenius Multi-Agent Architecture

## Executive Summary

This document outlines the comprehensive plan to refactor NetGenius orchestrator from custom Python agents to **Google Agent Development Kit (ADK)** - a requirement for the Google Cloud hackathon. The refactor will leverage ADK's multi-agent patterns, Gemini models, and workflow orchestration while maintaining our current M1-M3 implementation.

---

## 1. Current Architecture vs ADK Architecture

### Current State (Non-ADK)
```python
# Custom Python functions acting as "agents"
async def extract_exercise_spec(prompt: str) -> ExerciseSpec:
    # Template-based pattern matching
    return _parse_prompt_simple(prompt)

async def create_design(spec: ExerciseSpec) -> DesignOutput:
    # Hardcoded topology templates
    return _generate_topology_template(spec)

# No LLM integration
# No session management
# No state persistence
# Manual orchestration in main.py
```

### Target State (ADK-Based)
```python
from google.adk.agents import LlmAgent, SequentialAgent, AgentTool
from google.adk.runner import Runner

# LLM-powered agents with Gemini
planner_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="PedagogyPlanner",
    instruction="Extract learning objectives from instructor prompts...",
    tools=[...]
)

# Workflow orchestration
pipeline = SequentialAgent(
    name="LabCreationPipeline",
    sub_agents=[planner_agent, designer_agent, author_agent, validator_agent]
)

# ADK Runner with session management
runner = Runner(agent=pipeline, app_name="netgenius")
```

---

## 2. ADK Core Concepts Applied to NetGenius

### 2.1 Agent Types We'll Use

#### **LLM Agents** (Primary)
- **Planner Agent**: Uses Gemini to analyze instructor prompts and generate structured exercise specs
- **Designer Agent**: Uses Gemini to create network topologies and configurations
- **Author Agent**: Uses Gemini to write pedagogically sound lab guides
- **Reviewer Agent** (New): Validates outputs before passing to next stage

#### **Workflow Agents** (Orchestration)
- **SequentialAgent**: Main pipeline orchestrator (Planner → Designer → Author → Validator)
- **ParallelAgent**: For parallel validation tasks (topology lint + CLI lint simultaneously)

#### **Custom Agents** (Integration)
- **Validator Agent**: Wraps Cloud Run Jobs API for headless execution
- **GCS Artifact Agent**: Fetches validation results from Google Cloud Storage

### 2.2 Multi-Agent Communication Patterns

#### Pattern 1: Sequential Pipeline with Shared State
```python
# Planner saves to state
planner_agent = LlmAgent(
    name="Planner",
    output_key="exercise_spec",  # Saves to session.state["exercise_spec"]
    instruction="Extract objectives and topology requirements..."
)

# Designer reads from state
designer_agent = LlmAgent(
    name="Designer",
    instruction="Create topology using requirements: {exercise_spec}",
    output_key="design_output"
)

# Orchestrate with SequentialAgent
pipeline = SequentialAgent(
    name="LabPipeline",
    sub_agents=[planner_agent, designer_agent, author_agent]
)
```

#### Pattern 2: AgentTool for External Service Calls
```python
# Parser-Linter as an agent
linter_agent = LlmAgent(
    name="ParserLinter",
    instruction="Validate Containerlab YAML and Cisco IOS commands",
    tools=[lint_topology_tool, lint_cli_tool]
)

# Designer uses linter as a tool
designer_agent = LlmAgent(
    name="Designer",
    tools=[
        AgentTool(agent=linter_agent),  # Synchronous invocation
        generate_topology_tool
    ],
    instruction="Generate topology, then use linter_agent to validate"
)
```

#### Pattern 3: Parallel Validation
```python
# Run topology and CLI linting concurrently
parallel_linter = ParallelAgent(
    name="ParallelLinter",
    sub_agents=[topology_linter_agent, cli_linter_agent]
)

# Integrate into main pipeline
pipeline = SequentialAgent(
    sub_agents=[
        planner_agent,
        designer_agent,
        parallel_linter,  # Both lints run simultaneously
        author_agent
    ]
)
```

---

## 3. Detailed Refactoring Plan by Milestone

### Phase 1: Foundation Setup (Week 1)

#### Tasks:
1. **Install Google ADK**
   ```bash
   pip install google-adk
   ```

2. **Set up Gemini API Authentication**
   - Obtain API key from Google AI Studio
   - Add to `.env`: `GOOGLE_API_KEY="..."`
   - Alternative: Use Vertex AI with service account

3. **Create ADK Project Structure**
   ```bash
   orchestrator/
   ├── adk_agents/
   │   ├── __init__.py
   │   ├── planner.py       # LlmAgent for pedagogy planning
   │   ├── designer.py      # LlmAgent for topology design
   │   ├── author.py        # LlmAgent for lab guide writing
   │   ├── validator.py     # Custom agent for Cloud Run Jobs
   │   └── tools/
   │       ├── linter_tools.py      # Parser-linter API wrappers
   │       ├── topology_tools.py    # Containerlab generation helpers
   │       └── gcs_tools.py         # GCS artifact fetching
   ├── workflows/
   │   ├── lab_creation_pipeline.py  # SequentialAgent orchestration
   │   └── validation_workflow.py    # Parallel validation logic
   └── main_adk.py          # New ADK-based CLI entry point
   ```

4. **Define Pydantic Schemas for State**
   - Keep existing schemas in `orchestrator/schemas/`
   - Add state management helpers

---

### Phase 2: Convert Planner Agent to ADK (Week 1-2)

#### Current Implementation:
```python
# orchestrator/agents/planner.py (non-ADK)
async def extract_exercise_spec(user_prompt: str) -> ExerciseSpec:
    if "static routing" in user_prompt.lower():
        return _create_static_routing_spec()
    # ...template matching
```

#### ADK Implementation:
```python
# orchestrator/adk_agents/planner.py
from google.adk.agents import LlmAgent
from pydantic import BaseModel

class ExerciseSpec(BaseModel):
    title: str
    objectives: list[str]
    devices: list[dict]
    lab_type: str
    # ...

planner_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="PedagogyPlanner",
    description="Extracts learning objectives and requirements from instructor prompts",
    instruction="""
You are an expert networking instructor analyzing lab exercise requests.

Extract the following from the user's prompt:
1. Learning objectives (what students will learn)
2. Required network topology (routers, switches, links)
3. Lab type (static routing, OSPF, VLAN, EIGRP, ACL, etc.)
4. Difficulty level (beginner, intermediate, advanced)
5. Estimated completion time

Return a structured JSON matching the ExerciseSpec schema.

Example:
User: "Create a basic VLAN lab with 2 switches"
Output: {
  "title": "Basic VLAN Configuration",
  "objectives": [
    "Configure VLANs on Cisco switches",
    "Assign access ports to VLANs",
    "Configure trunk links"
  ],
  "devices": [
    {"hostname": "SW1", "platform": "cisco_3560"},
    {"hostname": "SW2", "platform": "cisco_3560"}
  ],
  "lab_type": "vlan",
  "level": "beginner",
  "estimated_time_minutes": 30
}
""",
    output_key="exercise_spec",  # Saves to session.state["exercise_spec"]
    output_schema=ExerciseSpec,  # Pydantic model for structured output
)
```

#### Testing:
```python
from google.adk.runner import Runner
from google.adk.session import InMemorySessionService

session_service = InMemorySessionService()
runner = Runner(
    agent=planner_agent,
    app_name="netgenius",
    session_service=session_service
)

events = runner.run(
    user_id="test_user",
    session_id="test_session",
    new_message="Create a basic VLAN lab with 2 switches"
)

# Access result from state
exercise_spec = runner.session_service.get_session(
    "test_user", "test_session"
).state["exercise_spec"]
print(exercise_spec)
```

---

### Phase 3: Convert Designer Agent to ADK (Week 2)

#### ADK Implementation:
```python
# orchestrator/adk_agents/designer.py
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import AgentTool

# Define tools for topology generation
def generate_containerlab_yaml(exercise_spec: dict) -> str:
    """Helper function to scaffold basic Containerlab YAML"""
    # Can still use some template logic here
    pass

# Linter integration as tools
async def lint_topology(topology_yaml: str) -> dict:
    """Call parser-linter API for topology validation"""
    # Existing parser_linter.lint_topology() logic
    pass

async def lint_cli(device_type: str, commands: list) -> dict:
    """Call parser-linter API for CLI validation"""
    # Existing parser_linter.lint_cli() logic
    pass

designer_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="Designer",
    description="Creates network topology and device configurations",
    instruction="""
You are a network design expert creating Containerlab topologies and Cisco IOS configs.

Input: exercise_spec from session state with structure: {exercise_spec}

Tasks:
1. Generate Containerlab YAML defining devices and links
2. Create initial device configurations (baseline state)
3. Create target configurations (desired end state demonstrating the concept)
4. Use lint_topology and lint_cli tools to validate your outputs
5. If linting fails, fix issues and re-validate (max 2 retries)

Output a JSON with:
- topology_yaml: Containerlab YAML string
- initial_configs: dict mapping hostname to config
- target_configs: dict mapping hostname to config
- lint_results: validation results

Containerlab YAML format:
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

Cisco IOS config should be realistic and follow best practices.
""",
    tools=[
        generate_containerlab_yaml,
        lint_topology,
        lint_cli
    ],
    output_key="design_output",
    output_schema=DesignOutput,
    planner=BuiltInPlanner()  # Enable multi-step reasoning
)
```

#### Retry Logic with LoopAgent:
```python
from google.adk.agents import LoopAgent

designer_with_retry = LoopAgent(
    name="DesignerWithRetry",
    sub_agents=[designer_agent],
    max_iterations=3,  # Max 2 retries + initial attempt
    description="Designer with automatic retry on linting failures"
)

# Designer checks lint results and sets escalate=True when successful
# If linting fails, loop continues for retry
```

---

### Phase 4: Convert Author Agent to ADK (Week 2-3)

#### ADK Implementation:
```python
# orchestrator/adk_agents/author.py
from google.adk.agents import LlmAgent

author_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="LabGuideAuthor",
    description="Writes student-facing lab guides with clear instructions",
    instruction="""
You are an expert technical writer creating networking lab guides for students.

Input from session state:
- exercise_spec: {exercise_spec}
- design_output: {design_output}

Create a comprehensive lab guide with:

## Structure:
1. Title and learning objectives
2. Lab topology diagram (ASCII art or description)
3. Per-device configuration steps with clear explanations
4. Verification commands to check progress
5. Expected outputs for verification commands
6. Troubleshooting tips for common issues

## Requirements:
- Use imperative mood ("Configure VLAN 10", not "You will configure")
- Provide context for why each step matters pedagogically
- Include verification commands after configuration changes
- Add hints for common mistakes
- Use CLI lint tool to validate command sequences

Output a JSON with:
- title: Lab title
- markdown: Full markdown lab guide
- device_sections: List of per-device instruction sections
- estimated_time_minutes: Estimated completion time
- lint_results: CLI validation results per device

Markdown format example:
```markdown
# Basic VLAN Configuration

## Learning Objectives
- Configure VLANs on Cisco switches
- Assign access ports to VLANs

## Topology
SW1 connected to SW2 via trunk link

## Device: SW1

### Step 1: Create VLAN 10
\`\`\`
SW1(config)# vlan 10
SW1(config-vlan)# name Sales
\`\`\`

**Why?** VLANs segment broadcast domains for security and performance.

### Verification:
\`\`\`
SW1# show vlan brief
\`\`\`

Expected output: VLAN 10 with name "Sales"
```
""",
    tools=[lint_cli],  # Validate command sequences
    output_key="draft_lab_guide",
    output_schema=DraftLabGuide
)
```

---

### Phase 5: Integrate Validator Agent as Custom Agent (Week 3)

#### Custom Agent for Cloud Run Jobs:
```python
# orchestrator/adk_agents/validator.py
from google.adk.agents import BaseAgent
from google.adk.context import InvocationContext
from typing import AsyncIterator
from google.adk.events import Event, EventActions

class ValidatorAgent(BaseAgent):
    """Custom agent for Cloud Run Jobs validation"""

    def __init__(
        self,
        name: str = "Validator",
        project_id: str = "netgenius-hackathon",
        region: str = "us-central1",
        job_name: str = "headless-runner",
        bucket_name: str = "netgenius-artifacts-dev"
    ):
        super().__init__(name=name)
        self.project_id = project_id
        self.region = region
        self.job_name = job_name
        self.bucket_name = bucket_name

    async def run_async(
        self,
        context: InvocationContext
    ) -> AsyncIterator[Event]:
        """Execute Cloud Run Job and fetch artifacts"""

        # Get draft guide from session state
        draft_guide = context.session.state.get("draft_lab_guide")
        design_output = context.session.state.get("design_output")

        # Convert to runner payload (existing logic)
        payload = self._convert_to_runner_payload(draft_guide, design_output)

        # Submit Cloud Run Job (existing logic)
        execution_id = await self._submit_job(payload)

        # Yield progress events
        yield Event(
            type="agent_message",
            content=f"Submitted validation job: {execution_id}"
        )

        # Poll until completion (existing logic)
        success = await self._poll_job_status(execution_id)

        # Fetch artifacts from GCS (existing logic)
        artifacts = await self._fetch_artifacts(execution_id)

        # Save to session state
        context.session.state["validation_result"] = {
            "execution_id": execution_id,
            "success": artifacts.success,
            "summary": artifacts.summary
        }

        # Yield final event
        status = "PASS ✓" if artifacts.success else "FAIL ✗"
        yield Event(
            type="agent_message",
            content=f"Validation {status}\nSteps: {artifacts.passed_steps}/{artifacts.total_steps}"
        )

        # Return control to pipeline
        return EventActions()

    # Existing validator logic methods...
    async def _submit_job(self, payload): ...
    async def _poll_job_status(self, execution_id): ...
    async def _fetch_artifacts(self, execution_id): ...
```

---

### Phase 6: Orchestrate with SequentialAgent (Week 3)

#### Main Pipeline:
```python
# orchestrator/workflows/lab_creation_pipeline.py
from google.adk.agents import SequentialAgent
from adk_agents.planner import planner_agent
from adk_agents.designer import designer_with_retry
from adk_agents.author import author_agent
from adk_agents.validator import ValidatorAgent

# Create sequential pipeline
lab_creation_pipeline = SequentialAgent(
    name="LabCreationPipeline",
    description="End-to-end lab creation: Planner → Designer → Author → Validator",
    sub_agents=[
        planner_agent,
        designer_with_retry,
        author_agent,
        ValidatorAgent()
    ]
)
```

#### New Main Entry Point:
```python
# orchestrator/main_adk.py
import asyncio
import click
from google.adk.runner import Runner
from google.adk.session import InMemorySessionService
from workflows.lab_creation_pipeline import lab_creation_pipeline

@click.command()
@click.option("--prompt", required=True, help="Instructor prompt for lab creation")
@click.option("--dry-run", is_flag=True, help="Skip validation")
def create(prompt: str, dry_run: bool):
    """Create lab using ADK pipeline"""

    session_service = InMemorySessionService()
    runner = Runner(
        agent=lab_creation_pipeline,
        app_name="netgenius",
        session_service=session_service
    )

    # Run pipeline
    events = runner.run(
        user_id="instructor",
        session_id=f"lab_{int(time.time())}",
        new_message=prompt
    )

    # Print events as they stream
    for event in events:
        if event.type == "agent_message":
            print(f"[{event.agent_name}] {event.content}")

    # Save outputs to disk
    session = runner.session_service.get_session("instructor", session_id)
    _save_outputs(session.state)

if __name__ == "__main__":
    create()
```

#### CLI Usage:
```bash
# Run full pipeline with ADK
python main_adk.py create --prompt "Create a basic VLAN lab with 2 switches"

# Use ADK web UI for testing
adk web --port 8000
```

---

## 4. Advanced ADK Features to Leverage

### 4.1 Built-in Tools Integration

```python
from google.adk.tools import google_search, code_execution

# Add web search for latest networking best practices
designer_agent = LlmAgent(
    tools=[
        google_search,  # Search for Containerlab examples
        lint_topology,
        lint_cli
    ],
    instruction="Search for Containerlab topology examples if needed..."
)
```

### 4.2 Planner for Multi-Step Reasoning

```python
from google.adk.agents.planner import BuiltInPlanner

designer_agent = LlmAgent(
    planner=BuiltInPlanner(),  # Enables Chain-of-Thought reasoning
    instruction="Think step-by-step: analyze requirements, design topology, generate configs, validate"
)
```

### 4.3 Generator-Critic Pattern

```python
# Reviewer agent validates outputs
reviewer_agent = LlmAgent(
    name="Reviewer",
    instruction="Review the design_output for correctness, best practices, and pedagogical value",
    output_key="review_feedback"
)

# Pipeline with review step
pipeline_with_review = SequentialAgent(
    sub_agents=[
        planner_agent,
        designer_agent,
        reviewer_agent,  # Reviews designer output
        author_agent     # Incorporates feedback
    ]
)
```

### 4.4 Iterative Refinement with LoopAgent

```python
from google.adk.agents import LoopAgent

# Refine until validation passes
refinement_loop = LoopAgent(
    name="DesignRefinement",
    sub_agents=[designer_agent, reviewer_agent],
    max_iterations=3,
    description="Iteratively refine design until review passes"
)
```

### 4.5 Parallel Linting

```python
# Run topology and CLI linting concurrently
topology_linter = LlmAgent(name="TopologyLinter", tools=[lint_topology], ...)
cli_linter = LlmAgent(name="CLILinter", tools=[lint_cli], ...)

parallel_linter = ParallelAgent(
    name="ParallelLinter",
    sub_agents=[topology_linter, cli_linter]
)

# Merge into main pipeline
pipeline = SequentialAgent(
    sub_agents=[
        planner_agent,
        designer_agent,
        parallel_linter,  # Both run simultaneously
        author_agent
    ]
)
```

---

## 5. State Management & Session Handling

### 5.1 Session State Schema

```python
# Shared state across all agents in pipeline
session.state = {
    "exercise_spec": ExerciseSpec(...),           # From Planner
    "design_output": DesignOutput(...),           # From Designer
    "draft_lab_guide": DraftLabGuide(...),        # From Author
    "validation_result": ValidationResult(...),   # From Validator
    "temp:current_iteration": 1                   # Temporary iteration counter
}
```

### 5.2 Persistent Session Service

```python
# For production: persist sessions to database
from google.adk.session import FirestoreSessionService

session_service = FirestoreSessionService(
    project_id="netgenius-hackathon",
    collection_name="lab_sessions"
)

runner = Runner(
    agent=lab_creation_pipeline,
    session_service=session_service
)
```

---

## 6. Testing Strategy

### 6.1 Unit Tests for Individual Agents

```python
import pytest
from google.adk.testing import MockRunner

@pytest.mark.asyncio
async def test_planner_agent():
    runner = MockRunner(agent=planner_agent)

    events = runner.run(
        user_id="test",
        session_id="test",
        new_message="Create a basic VLAN lab"
    )

    session = runner.get_session("test", "test")
    exercise_spec = session.state["exercise_spec"]

    assert exercise_spec.lab_type == "vlan"
    assert len(exercise_spec.objectives) > 0
```

### 6.2 Integration Tests for Pipeline

```python
@pytest.mark.asyncio
async def test_full_pipeline():
    runner = Runner(
        agent=lab_creation_pipeline,
        session_service=InMemorySessionService()
    )

    events = runner.run(
        user_id="test",
        session_id="test",
        new_message="Create OSPF lab with 2 routers",
        dry_run=True  # Skip validation
    )

    session = runner.get_session("test", "test")

    # Verify all stages completed
    assert "exercise_spec" in session.state
    assert "design_output" in session.state
    assert "draft_lab_guide" in session.state
```

---

## 7. Deployment Considerations

### 7.1 ADK on Cloud Run

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install google-adk google-cloud-run google-cloud-storage

COPY orchestrator/ .

CMD ["python", "main_adk.py", "web", "--port", "8080"]
```

```bash
# Deploy to Cloud Run
gcloud run deploy netgenius-orchestrator \
  --source=. \
  --region=us-central1 \
  --allow-unauthenticated \
  --set-env-vars=GOOGLE_API_KEY=$GEMINI_API_KEY
```

### 7.2 Vertex AI Agent Engine Deployment

```bash
# Deploy to Vertex AI managed platform
adk deploy --platform=vertex-ai \
  --project=netgenius-hackathon \
  --region=us-central1 \
  --agent=lab_creation_pipeline
```

---

## 8. Migration Timeline

### Week 1: Foundation
- [ ] Install ADK and set up Gemini API
- [ ] Create new `adk_agents/` directory structure
- [ ] Convert Planner agent to LlmAgent
- [ ] Test Planner in isolation

### Week 2: Core Agents
- [ ] Convert Designer agent with linting tools
- [ ] Add LoopAgent for retry logic
- [ ] Convert Author agent
- [ ] Test Planner → Designer → Author sequence

### Week 3: Integration & Validation
- [ ] Implement Validator as Custom Agent
- [ ] Create SequentialAgent pipeline
- [ ] Build new `main_adk.py` entry point
- [ ] End-to-end testing with real Gemini calls

### Week 4: Polish & Deployment
- [ ] Add parallel linting with ParallelAgent
- [ ] Implement Generator-Critic pattern with Reviewer
- [ ] Deploy to Cloud Run
- [ ] Submit to hackathon!

---

## 9. Key Benefits of ADK Integration

### For Hackathon Judging:
✅ **Native Google Cloud Integration** - Uses Gemini, Vertex AI, ADK (all Google tech)
✅ **Multi-Agent Architecture** - Demonstrates sophisticated agent coordination
✅ **LLM-Powered Intelligence** - Replaces templates with true AI reasoning
✅ **Production-Ready** - Uses Google's official agent framework
✅ **Scalable** - ADK handles session management, state, callbacks

### Technical Benefits:
- **Structured Output** - Pydantic schemas ensure type safety
- **Automatic State Management** - No manual state passing
- **Built-in Observability** - Cloud Trace, logging, callbacks
- **Model Agnostic** - Can swap Gemini for other models via LiteLLM
- **Testable** - ADK provides testing utilities

---

## 10. Risks & Mitigations

### Risk 1: Gemini API Costs
**Mitigation:**
- Use `gemini-2.0-flash` (cheaper) for most agents
- Reserve `gemini-2.5-pro` only for complex design tasks
- Implement caching for repeated prompts
- Set usage quotas

### Risk 2: Parser-Linter Not Deployed
**Mitigation:**
- Mock linter tools for testing
- Use template fallbacks if API unavailable
- Document in presentation that full integration requires linter deployment

### Risk 3: Learning Curve for ADK
**Mitigation:**
- Start with simple LlmAgent conversion
- Use official ADK examples as reference
- Keep existing logic in tools, just wrap with ADK

### Risk 4: Debugging LLM Agent Behavior
**Mitigation:**
- Use ADK web UI for interactive testing
- Enable verbose logging with callbacks
- Add explicit logging in agent instructions

---

## 11. Success Criteria

### Minimum Viable ADK Integration (Must Have):
- [ ] All 4 agents (Planner, Designer, Author, Validator) use ADK
- [ ] SequentialAgent orchestrates pipeline
- [ ] Gemini models power LLM agents
- [ ] Session state manages data flow
- [ ] CLI works: `python main_adk.py create --prompt "..."`

### Full ADK Showcase (Nice to Have):
- [ ] ParallelAgent for concurrent linting
- [ ] LoopAgent for iterative refinement
- [ ] Generator-Critic pattern with Reviewer
- [ ] ADK web UI deployment
- [ ] Vertex AI Agent Engine deployment

### Demo Requirements:
- [ ] Live demo showing end-to-end lab creation
- [ ] Architecture diagram showing ADK patterns
- [ ] Presentation slides highlighting Google Cloud tech stack
- [ ] GitHub repo with ADK-based implementation

---

## 12. Next Steps

**Immediate Actions:**
1. Get confirmation from you on this plan
2. Install `google-adk` and set up Gemini API key
3. Start with Planner agent conversion
4. Test in isolation before moving to Designer

**Questions for You:**
1. Do you already have a Gemini API key, or should we set one up?
2. Do you want to use **Gemini API** (via API key) or **Vertex AI** (via service account)?
3. Should we keep the old `main.py` for comparison, or replace it entirely?
4. What's the hackathon submission deadline? (helps prioritize features)

---

## Appendix: ADK Resources

- **Official Docs:** https://google.github.io/adk-docs/
- **GitHub:** https://github.com/google/adk-python
- **Codelabs:** https://codelabs.developers.google.com/?text=adk
- **Blog Post:** https://cloud.google.com/blog/products/ai-machine-learning/build-multi-agentic-systems-using-google-adk
- **API Key:** https://aistudio.google.com/app/apikey

---

**Document Version:** 1.0
**Date:** 2025-01-04
**Author:** Claude (via NetGenius Development Team)
