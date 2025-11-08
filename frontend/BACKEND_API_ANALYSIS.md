# Backend API Analysis - Current State

**Date:** 2025-11-08
**Status:** Analysis Complete

---

## Current Backend Architecture

### Entry Points
The orchestrator has **two main entry points**:

1. **`main.py`** (Old, simpler version - M3)
   - CLI-based using Click
   - Command: `python main.py create --prompt "..." [--dry-run] [--output ./output]`
   - Runs agents sequentially: Planner → Designer → Author → Validator
   - Saves outputs to local files (JSON + Markdown)

2. **`main_adk.py`** ⭐ (Current, ADK-based - M5+)
   - CLI-based using Click
   - Command: `python main_adk.py create --prompt "..." [--dry-run] [--no-rca] [--output ./output]`
   - Uses Google ADK SequentialAgent pipeline
   - Includes RCA (Root Cause Analysis) retry loop
   - Saves outputs to local files via session state

### Key Finding: **NO REST API EXISTS**

❌ The backend is currently **CLI-only** - there are **no HTTP endpoints** like:
- `POST /api/labs/create`
- `GET /api/labs/{id}/status`
- `GET /api/labs/{id}`
- etc.

---

## Data Models (Pydantic Schemas)

All schemas are in `orchestrator/schemas/`:

### 1. ExerciseSpec (`exercise_spec.py`)
Output from Pedagogy Planner agent.

```python
{
  "title": str,
  "objectives": list[str],
  "constraints": dict,  # e.g., {"devices": 4, "time_minutes": 45}
  "level": str,         # "CCNA", "CCNP", etc.
  "prerequisites": list[str]
}
```

### 2. DesignOutput (`design_output.py`)
Output from Designer agent.

```python
{
  "topology_yaml": str,                      # Network topology in YAML
  "initial_configs": dict[str, list[str]],   # Per-device initial commands
  "target_configs": dict[str, list[str]],    # Per-device target commands
  "platforms": dict[str, str],               # e.g., {"r1": "cisco_2911"}
  "lint_results": dict                       # Parser-linter results (if enabled)
}
```

### 3. DraftLabGuide (`draft_lab_guide.py`)
Output from Lab Guide Author agent.

```python
{
  "title": str,
  "markdown": str,                           # Full lab guide in Markdown
  "device_sections": list[DeviceSection],
  "estimated_time_minutes": int,
  "lint_results": dict
}

# DeviceSection structure:
{
  "device_name": str,
  "platform": str,
  "steps": list[CommandStep]
}

# CommandStep structure:
{
  "type": "cmd" | "verify" | "note" | "output",
  "value": str,
  "description": str
}
```

### 4. ValidationResult (`validation_result.py`)
Output from Validator agent.

```python
{
  "success": bool,
  "exercise_id": str,
  "build_id": str,
  "artifact_urls": dict[str, str],  # GCS URLs
  "error_summary": str | None,
  "duration_seconds": float | None
}
```

---

## Current Workflow (ADK Pipeline)

From `main_adk.py` + `adk_agents/pipeline.py`:

```
User runs: python main_adk.py create --prompt "..."
    ↓
Pipeline executes sequentially:
    1. Planner Agent → exercise_spec (stored in session.state)
    2. Designer Agent → design_output (stored in session.state)
    3. Design State Writer → flush design_output
    4. Author Agent → draft_lab_guide (stored in session.state)
    5. Draft State Writer → flush draft_lab_guide
    6. [If validation enabled] Validator Agent → validation_result
    7. [If RCA enabled] RCA Loop (retry on failure)
    ↓
Session state saved to memory (InMemorySessionService)
    ↓
Artifacts written to local filesystem:
    - ./output/exercise_spec.json
    - ./output/design_output.json
    - ./output/draft_lab_guide.json
    - ./output/draft_lab_guide.md
    - ./output/validation_result.json (if validation ran)
    - ./output/patch_plan.json (if RCA ran)
```

**Session State Structure:**
```python
session.state = {
  "exercise_spec": ExerciseSpec,
  "design_output": DesignOutput,
  "draft_lab_guide": DraftLabGuide,
  "validation_result": ValidationResult,  # optional
  "patch_plan": PatchPlan                 # optional (if RCA ran)
}
```

---

## What Needs to Be Built for Frontend Integration

### Option 1: REST API Wrapper (Recommended for Hackathon)

Create a **lightweight FastAPI/Flask wrapper** around the existing ADK pipeline:

**New file:** `orchestrator/api_server.py`

```python
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import asyncio
import uuid
from datetime import datetime

app = FastAPI()

# In-memory storage (replace with Redis/DB for production)
labs = {}

class CreateLabRequest(BaseModel):
    prompt: str
    dry_run: bool = False
    enable_rca: bool = True

class LabStatus(BaseModel):
    lab_id: str
    status: str  # "pending", "planner_running", "designer_running", etc.
    current_agent: str | None
    progress: dict
    created_at: str
    updated_at: str

@app.post("/api/labs/create")
async def create_lab(request: CreateLabRequest, background_tasks: BackgroundTasks):
    lab_id = str(uuid.uuid4())

    labs[lab_id] = {
        "lab_id": lab_id,
        "status": "pending",
        "current_agent": None,
        "progress": {},
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "prompt": request.prompt,
        "outputs": {}
    }

    # Run pipeline in background
    background_tasks.add_task(run_pipeline, lab_id, request.prompt, request.dry_run, request.enable_rca)

    return {"lab_id": lab_id, "status": "pending"}

@app.get("/api/labs/{lab_id}/status")
async def get_lab_status(lab_id: str):
    if lab_id not in labs:
        return {"error": "Lab not found"}, 404
    return labs[lab_id]

@app.get("/api/labs/{lab_id}")
async def get_lab(lab_id: str):
    if lab_id not in labs:
        return {"error": "Lab not found"}, 404
    return labs[lab_id]

@app.get("/api/labs")
async def list_labs():
    return list(labs.values())

async def run_pipeline(lab_id: str, prompt: str, dry_run: bool, enable_rca: bool):
    """Run ADK pipeline and update lab status in real-time."""
    from adk_agents.pipeline import create_lab_pipeline
    from google.adk import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    import time

    # Update status
    labs[lab_id]["status"] = "planner_running"
    labs[lab_id]["current_agent"] = "planner"
    labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

    try:
        # Create pipeline
        pipeline = create_lab_pipeline(
            include_validation=not dry_run,
            include_rca=enable_rca
        )

        # Initialize session
        session_service = InMemorySessionService()
        session_id = f"lab_{int(time.time())}"

        await session_service.create_session(
            app_name="adk_agents",
            user_id="api",
            session_id=session_id
        )

        runner = Runner(
            agent=pipeline,
            app_name="adk_agents",
            session_service=session_service
        )

        # Run pipeline
        message = types.Content(parts=[types.Part(text=prompt)], role="user")
        events = list(runner.run(user_id="api", session_id=session_id, new_message=message))

        # Extract outputs from session state
        session = await session_service.get_session(
            app_name="adk_agents",
            user_id="api",
            session_id=session_id
        )

        # Update lab with outputs
        labs[lab_id]["outputs"] = {
            "exercise_spec": session.state.get("exercise_spec"),
            "design_output": session.state.get("design_output"),
            "draft_lab_guide": session.state.get("draft_lab_guide"),
            "validation_result": session.state.get("validation_result"),
            "patch_plan": session.state.get("patch_plan")
        }
        labs[lab_id]["status"] = "completed"
        labs[lab_id]["current_agent"] = None
        labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

    except Exception as e:
        labs[lab_id]["status"] = "failed"
        labs[lab_id]["error"] = str(e)
        labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()
```

**Deployment:**
```bash
# Run locally
cd orchestrator
uvicorn api_server:app --reload --port 8080

# Or deploy to Cloud Run
gcloud run deploy netgenius-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

---

### Option 2: Direct CLI Integration (Simpler, but less real-time)

Frontend calls the CLI directly via subprocess and polls filesystem:

```typescript
// Frontend spawns background process
const { exec } = require('child_process');
const labId = uuidv4();

exec(`python main_adk.py create --prompt "${prompt}" --output ./labs/${labId}`,
  (error, stdout, stderr) => {
    // Poll ./labs/${labId}/ for JSON files
  }
);
```

**Pros:** No backend changes needed
**Cons:** Hard to get real-time status, not scalable

---

## Recommendation for Hackathon

### **Build Option 1: FastAPI Wrapper**

**Estimated Time:** 3-4 hours

**Why:**
1. Reuses 100% of existing ADK pipeline code
2. Provides clean REST API for frontend
3. Enables real-time status updates (poll every 3s)
4. Cloud Run compatible
5. No changes to core orchestrator logic

**Implementation Steps:**
1. Create `orchestrator/api_server.py` with FastAPI
2. Add in-memory storage for lab state
3. Run ADK pipeline in background tasks
4. Update lab status as pipeline progresses (hook into ADK events)
5. Add CORS middleware for frontend
6. Deploy to Cloud Run

**Endpoints to implement:**
- ✅ `POST /api/labs/create` → Returns `{ lab_id }`
- ✅ `GET /api/labs/{id}/status` → Returns current agent + progress
- ✅ `GET /api/labs/{id}` → Returns full lab data
- ✅ `GET /api/labs` → Returns list of all labs
- ⚠️ `POST /api/labs/{id}/feedback` → (Optional, for RCA manual input)
- ⚠️ `GET /api/artifacts/{path}` → (Optional, proxy to GCS)

---

## Frontend Data Flow (Revised)

```
User submits prompt in UI
    ↓
POST /api/labs/create { prompt }
    ← { lab_id: "abc-123" }
    ↓
Poll GET /api/labs/abc-123/status every 3s
    ↓
Receive updates:
  { status: "planner_running", current_agent: "planner" }
  { status: "designer_running", current_agent: "designer",
    outputs: { exercise_spec: {...} } }
  { status: "author_running", current_agent: "author",
    outputs: { exercise_spec: {...}, design_output: {...} } }
  { status: "validator_running", current_agent: "validator",
    outputs: { ..., draft_lab_guide: {...} } }
  { status: "completed",
    outputs: { ..., validation_result: {...} } }
    ↓
Display results in review interface
```

---

## Action Items

### For Backend (You or Backend Team)
- [ ] Create `orchestrator/api_server.py` with FastAPI
- [ ] Implement `/api/labs/create`, `/api/labs/{id}/status`, `/api/labs/{id}`, `/api/labs` endpoints
- [ ] Add background task runner for ADK pipeline
- [ ] Add CORS middleware
- [ ] Test locally with `uvicorn api_server:app --reload`
- [ ] Create Dockerfile for API server
- [ ] Deploy to Cloud Run

### For Frontend (Me)
- [ ] Update implementation plan with correct API structure
- [ ] Build frontend assuming REST API exists
- [ ] Use polling with 3-second interval
- [ ] Display agent progress in real-time
- [ ] Handle all 5 output types: exercise_spec, design_output, draft_lab_guide, validation_result, patch_plan

---

## Summary

✅ **Backend has all the logic** - ADK pipeline works perfectly
❌ **Backend has no REST API** - It's currently CLI-only
🔧 **Solution:** Build lightweight FastAPI wrapper (3-4 hours)
🚀 **Frontend can proceed** - Mock the API endpoints initially, then integrate real backend when ready

**Next Step:** Decide who builds the API wrapper - you, or should I proceed with frontend using mock data first?
