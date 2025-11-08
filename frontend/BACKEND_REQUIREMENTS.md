# Backend API Requirements for Frontend Integration

**Document Version:** 1.0
**Date:** November 8, 2025
**Status:** Ready for Implementation
**Priority:** High (Required for Frontend Integration)

---

## Executive Summary

The frontend is **complete and functional** with mock data. To integrate with the real backend, you need to build a **REST API wrapper** around the existing ADK pipeline. This document provides complete specifications for the 4 required endpoints.

**Estimated Implementation Time:** 3-4 hours
**Recommended Approach:** FastAPI wrapper with background tasks

---

## Current Backend State

### What Already Exists ✅

- **ADK Pipeline:** Fully functional with Planner → Designer → Author → Validator → RCA
- **Session Management:** InMemorySessionService stores pipeline state
- **Data Models:** Complete Pydantic schemas in `orchestrator/schemas/`
- **CLI Interface:** `python main_adk.py create --prompt "..."`

### What's Missing ❌

- **No HTTP endpoints** - Backend is CLI-only
- **No REST API** - No way for frontend to interact
- **No real-time status** - No endpoint to poll progress
- **No lab persistence** - Session state is lost after CLI exits

---

## Required Architecture

```
Frontend (Next.js)
    ↓ HTTP POST
┌─────────────────────────────────────┐
│   FastAPI Server (NEW)              │
│   - POST /api/labs/create           │
│   - GET  /api/labs/{id}/status      │
│   - GET  /api/labs/{id}             │
│   - GET  /api/labs                  │
│   - In-memory lab storage           │
│   - Background task runner          │
└─────────────────────────────────────┘
    ↓ Python import
┌─────────────────────────────────────┐
│   Existing ADK Pipeline             │
│   - create_lab_pipeline()           │
│   - Runner.run()                    │
│   - InMemorySessionService          │
└─────────────────────────────────────┘
```

---

## API Endpoint Specifications

### Base URL
- **Development:** `http://localhost:8080`
- **Production:** `https://netgenius-api-{project}.run.app`

### CORS Configuration
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local dev
        "https://netgenius-frontend-*.run.app"  # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Endpoint 1: Create Lab

### `POST /api/labs/create`

Creates a new lab and starts the ADK pipeline in the background.

#### Request Body
```json
{
  "prompt": "Create a CCNA-level static routing lab with 2 routers",
  "dry_run": false,
  "enable_rca": true
}
```

**Schema:**
```python
class CreateLabRequest(BaseModel):
    prompt: str = Field(..., min_length=10, description="Instructor lab prompt")
    dry_run: bool = Field(default=False, description="Skip headless validation")
    enable_rca: bool = Field(default=True, description="Enable RCA retry loop")
```

#### Response (200 OK)
```json
{
  "lab_id": "lab_1731085234",
  "status": "pending"
}
```

**Schema:**
```python
class CreateLabResponse(BaseModel):
    lab_id: str
    status: str  # Always "pending" on creation
```

#### Error Responses
- **400 Bad Request** - Invalid prompt (too short, empty)
- **500 Internal Server Error** - Pipeline initialization failed

#### Implementation Notes

1. **Generate unique lab_id:**
   ```python
   import time
   lab_id = f"lab_{int(time.time())}"
   ```

2. **Store lab in memory:**
   ```python
   labs = {}  # In-memory storage
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
   ```

3. **Launch pipeline in background:**
   ```python
   from fastapi import BackgroundTasks

   @app.post("/api/labs/create")
   async def create_lab(request: CreateLabRequest, background_tasks: BackgroundTasks):
       lab_id = f"lab_{int(time.time())}"
       # ... initialize lab ...
       background_tasks.add_task(run_pipeline, lab_id, request.prompt, request.dry_run, request.enable_rca)
       return {"lab_id": lab_id, "status": "pending"}
   ```

4. **Background task structure:**
   ```python
   async def run_pipeline(lab_id: str, prompt: str, dry_run: bool, enable_rca: bool):
       try:
           # Update status
           labs[lab_id]["status"] = "planner_running"
           labs[lab_id]["current_agent"] = "planner"

           # Import and run ADK pipeline
           from adk_agents.pipeline import create_lab_pipeline
           from google.adk import Runner
           from google.adk.sessions import InMemorySessionService
           from google.genai import types

           pipeline = create_lab_pipeline(
               include_validation=not dry_run,
               include_rca=enable_rca
           )

           session_service = InMemorySessionService()
           session_id = lab_id

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

           message = types.Content(parts=[types.Part(text=prompt)], role="user")
           events = list(runner.run(user_id="api", session_id=session_id, new_message=message))

           # Extract outputs from session state
           session = await session_service.get_session(
               app_name="adk_agents",
               user_id="api",
               session_id=session_id
           )

           # Update lab with final outputs
           labs[lab_id]["outputs"] = {
               "exercise_spec": session.state.get("exercise_spec"),
               "design_output": session.state.get("design_output"),
               "draft_lab_guide": session.state.get("draft_lab_guide"),
               "validation_result": session.state.get("validation_result"),
               "patch_plan": session.state.get("patch_plan")
           }
           labs[lab_id]["status"] = "completed"
           labs[lab_id]["current_agent"] = None

       except Exception as e:
           labs[lab_id]["status"] = "failed"
           labs[lab_id]["error"] = str(e)
       finally:
           labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()
   ```

5. **CRITICAL: Update status during pipeline execution**

   The background task must update `labs[lab_id]["status"]` and `labs[lab_id]["current_agent"]` as the pipeline progresses:

   - After Planner completes: `status = "planner_complete"`, add `exercise_spec` to `progress`
   - When Designer starts: `status = "designer_running"`, `current_agent = "designer"`
   - After Designer completes: `status = "designer_complete"`, add `design_output` to `progress`
   - When Author starts: `status = "author_running"`, `current_agent = "author"`
   - After Author completes: `status = "author_complete"`, add `draft_lab_guide` to `progress`
   - When Validator starts: `status = "validator_running"`, `current_agent = "validator"`
   - After Validator completes: `status = "validator_complete"`, add `validation_result` to `progress`
   - When complete: `status = "completed"`, `current_agent = None`

   **How to track agent transitions:**
   - Option A: Hook into ADK event stream (parse `events` from `runner.run()`)
   - Option B: Manually update after each agent (check `session.state` keys)
   - Option C: Use ADK callbacks if available

---

## Endpoint 2: Get Lab Status

### `GET /api/labs/{lab_id}/status`

Returns current lab status and progress. **Frontend polls this endpoint every 3 seconds.**

#### Path Parameters
- `lab_id` (string, required) - Unique lab identifier

#### Response (200 OK)
```json
{
  "lab_id": "lab_1731085234",
  "status": "designer_running",
  "current_agent": "designer",
  "progress": {
    "exercise_spec": {
      "title": "Static Routing Lab",
      "objectives": ["Configure IP addressing", "Implement static routes"],
      "constraints": {"devices": 2, "time_minutes": 30},
      "level": "CCNA",
      "prerequisites": ["Basic CLI navigation"]
    },
    "design_output": null,
    "draft_lab_guide": null,
    "validation_result": null,
    "patch_plan": null
  },
  "created_at": "2025-11-08T10:00:00Z",
  "updated_at": "2025-11-08T10:02:15Z",
  "prompt": "Create a CCNA-level static routing lab with 2 routers",
  "error": null
}
```

**Schema:**
```python
class LabStatus(BaseModel):
    lab_id: str
    status: str  # Status enum (see below)
    current_agent: Optional[str] = None
    progress: Dict[str, Any]  # Contains exercise_spec, design_output, etc.
    created_at: str  # ISO 8601 timestamp
    updated_at: str  # ISO 8601 timestamp
    prompt: str
    error: Optional[str] = None
```

**Status Values:**
- `"pending"` - Lab created, pipeline not started
- `"planner_running"` - Planner agent executing
- `"planner_complete"` - Planner done, Designer starting
- `"designer_running"` - Designer agent executing
- `"designer_complete"` - Designer done, Author starting
- `"author_running"` - Author agent executing
- `"author_complete"` - Author done, Validator starting (if not dry_run)
- `"validator_running"` - Validator agent executing
- `"validator_complete"` - Validator done
- `"rca_running"` - RCA agent analyzing failure
- `"rca_complete"` - RCA done, retrying
- `"completed"` - All agents finished successfully
- `"failed"` - Pipeline failed with error

**Current Agent Values:**
- `"planner"`, `"designer"`, `"author"`, `"validator"`, `"rca"`, or `null`

#### Error Responses
- **404 Not Found** - Lab ID does not exist

#### Implementation
```python
@app.get("/api/labs/{lab_id}/status")
async def get_lab_status(lab_id: str):
    if lab_id not in labs:
        raise HTTPException(status_code=404, detail="Lab not found")
    return labs[lab_id]
```

---

## Endpoint 3: Get Full Lab Details

### `GET /api/labs/{lab_id}`

Returns complete lab data including all outputs. **Same as status endpoint for MVP.**

#### Path Parameters
- `lab_id` (string, required) - Unique lab identifier

#### Response (200 OK)
Same schema as `/api/labs/{lab_id}/status`

#### Implementation
```python
@app.get("/api/labs/{lab_id}")
async def get_lab(lab_id: str):
    if lab_id not in labs:
        raise HTTPException(status_code=404, detail="Lab not found")
    return labs[lab_id]
```

**Note:** For MVP, this is identical to the status endpoint. In the future, you could make this return more detailed information.

---

## Endpoint 4: List All Labs

### `GET /api/labs`

Returns list of all created labs with summary information.

#### Query Parameters (Optional, Future)
- `status` (string) - Filter by status
- `limit` (integer) - Max results to return
- `offset` (integer) - Pagination offset

#### Response (200 OK)
```json
[
  {
    "lab_id": "lab_1731085234",
    "title": "Static Routing Lab",
    "status": "completed",
    "created_at": "2025-11-08T10:00:00Z"
  },
  {
    "lab_id": "lab_1731085100",
    "title": "OSPF Basics",
    "status": "failed",
    "created_at": "2025-11-08T09:45:00Z"
  }
]
```

**Schema:**
```python
class LabListItem(BaseModel):
    lab_id: str
    title: str  # From exercise_spec.title or truncated prompt
    status: str
    created_at: str
```

#### Implementation
```python
@app.get("/api/labs")
async def list_labs():
    result = []
    for lab_id, lab in labs.items():
        # Get title from exercise_spec if available, otherwise use prompt
        title = "Untitled Lab"
        if lab.get("progress", {}).get("exercise_spec"):
            title = lab["progress"]["exercise_spec"].get("title", title)
        else:
            # Fallback: truncate prompt
            title = lab["prompt"][:50] + ("..." if len(lab["prompt"]) > 50 else "")

        result.append({
            "lab_id": lab["lab_id"],
            "title": title,
            "status": lab["status"],
            "created_at": lab["created_at"]
        })

    # Sort by creation date, newest first
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return result
```

---

## Data Models Reference

### Frontend TypeScript Types → Backend Pydantic Models

The frontend expects these exact data structures. Your Pydantic models already match in `orchestrator/schemas/`.

#### ExerciseSpec (from Planner)
```python
# orchestrator/schemas/exercise_spec.py
class ExerciseSpec(BaseModel):
    title: str
    objectives: list[str]
    constraints: dict  # {"devices": 2, "time_minutes": 30}
    level: str  # "CCNA", "CCNP", etc.
    prerequisites: list[str] = []
```

#### DesignOutput (from Designer)
```python
# orchestrator/schemas/design_output.py
class DesignOutput(BaseModel):
    topology_yaml: str
    initial_configs: dict[str, list[str]]  # device_name -> commands
    target_configs: dict[str, list[str]]
    platforms: dict[str, str]  # device_name -> platform type
    lint_results: dict = {}
```

#### DraftLabGuide (from Author)
```python
# orchestrator/schemas/draft_lab_guide.py
class CommandStep(BaseModel):
    type: str  # "cmd", "verify", "note", "output"
    value: str
    description: str = ""

class DeviceSection(BaseModel):
    device_name: str
    platform: str
    role: Optional[str] = None
    ip_table: Optional[dict[str, str]] = None
    steps: list[CommandStep]

class DraftLabGuide(BaseModel):
    title: str
    objectives: Optional[list[str]] = None
    prerequisites: Optional[list[str]] = None
    topology_description: Optional[str] = None
    device_sections: list[DeviceSection]
    estimated_time_minutes: int
    lint_results: dict = {}
```

#### ValidationResult (from Validator)
```python
# orchestrator/schemas/validation_result.py
class ValidationResult(BaseModel):
    success: bool
    exercise_id: str
    build_id: str
    artifact_urls: dict[str, str] = {}
    error_summary: Optional[str] = None
    duration_seconds: Optional[float] = None
    summary: Optional[dict] = None  # {"passed_steps": 10, "total_steps": 10}
```

---

## Implementation Checklist

### Step 1: Create FastAPI Server
- [ ] Create `orchestrator/api_server.py`
- [ ] Import FastAPI, BackgroundTasks, HTTPException
- [ ] Add CORS middleware
- [ ] Create in-memory labs storage: `labs: Dict[str, dict] = {}`

### Step 2: Implement Endpoints
- [ ] `POST /api/labs/create` - Create lab + start background task
- [ ] `GET /api/labs/{id}/status` - Return lab from storage
- [ ] `GET /api/labs/{id}` - Return lab from storage (same as status)
- [ ] `GET /api/labs` - Return list of all labs

### Step 3: Implement Background Pipeline Runner
- [ ] Create `run_pipeline()` async function
- [ ] Import ADK pipeline: `from adk_agents.pipeline import create_lab_pipeline`
- [ ] Initialize session and runner
- [ ] Run pipeline: `runner.run()`
- [ ] **Critical:** Update `labs[lab_id]["status"]` as agents progress
- [ ] Extract outputs from `session.state`
- [ ] Handle errors and set `status = "failed"`

### Step 4: Status Update Strategy

**Option A: Parse ADK Events (Recommended)**
```python
events = list(runner.run(...))
for event in events:
    # Parse event to determine which agent is running
    # Update labs[lab_id]["status"] accordingly
    # This requires understanding ADK event structure
```

**Option B: Poll Session State**
```python
while True:
    session = await session_service.get_session(...)
    if "exercise_spec" in session.state and labs[lab_id]["status"] == "planner_running":
        labs[lab_id]["status"] = "planner_complete"
        labs[lab_id]["progress"]["exercise_spec"] = session.state["exercise_spec"]
    # ... check for other outputs ...
    await asyncio.sleep(0.5)
```

**Option C: Manual Updates Between Agents**
```python
# Simplified: Just update at major milestones
labs[lab_id]["status"] = "planner_running"
# ... wait for pipeline to complete ...
labs[lab_id]["status"] = "completed"
labs[lab_id]["progress"] = extract_all_outputs(session.state)
```

Choose based on complexity vs. granularity trade-off.

### Step 5: Testing
- [ ] Start server: `uvicorn api_server:app --reload --port 8080`
- [ ] Test with curl:
  ```bash
  # Create lab
  curl -X POST http://localhost:8080/api/labs/create \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Create a CCNA static routing lab", "dry_run": false}'

  # Get status (repeat to watch progress)
  curl http://localhost:8080/api/labs/lab_1731085234/status

  # List all labs
  curl http://localhost:8080/api/labs
  ```
- [ ] Verify frontend connection:
  1. Update `frontend/lib/api.ts`: `USE_MOCK_DATA = false`
  2. Create `frontend/.env.local`: `NEXT_PUBLIC_ORCHESTRATOR_URL=http://localhost:8080`
  3. Run frontend: `npm run dev`
  4. Create a lab and watch real-time progress

### Step 6: Deployment
- [ ] Create Dockerfile for API server
- [ ] Deploy to Cloud Run
- [ ] Update frontend env var with production URL

---

## Example Implementation Structure

```python
# orchestrator/api_server.py

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import time
import asyncio

app = FastAPI(title="NetGenius API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.run.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
labs: Dict[str, dict] = {}

# Request/Response Models
class CreateLabRequest(BaseModel):
    prompt: str = Field(..., min_length=10)
    dry_run: bool = False
    enable_rca: bool = True

class CreateLabResponse(BaseModel):
    lab_id: str
    status: str

# Endpoints
@app.post("/api/labs/create", response_model=CreateLabResponse)
async def create_lab(request: CreateLabRequest, background_tasks: BackgroundTasks):
    lab_id = f"lab_{int(time.time())}"

    labs[lab_id] = {
        "lab_id": lab_id,
        "status": "pending",
        "current_agent": None,
        "progress": {},
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "prompt": request.prompt,
        "error": None
    }

    background_tasks.add_task(
        run_pipeline,
        lab_id,
        request.prompt,
        request.dry_run,
        request.enable_rca
    )

    return {"lab_id": lab_id, "status": "pending"}

@app.get("/api/labs/{lab_id}/status")
async def get_lab_status(lab_id: str):
    if lab_id not in labs:
        raise HTTPException(status_code=404, detail="Lab not found")
    return labs[lab_id]

@app.get("/api/labs/{lab_id}")
async def get_lab(lab_id: str):
    if lab_id not in labs:
        raise HTTPException(status_code=404, detail="Lab not found")
    return labs[lab_id]

@app.get("/api/labs")
async def list_labs():
    result = []
    for lab_id, lab in labs.items():
        title = "Untitled Lab"
        if lab.get("progress", {}).get("exercise_spec"):
            title = lab["progress"]["exercise_spec"].get("title", title)
        else:
            title = lab["prompt"][:50] + ("..." if len(lab["prompt"]) > 50 else "")

        result.append({
            "lab_id": lab["lab_id"],
            "title": title,
            "status": lab["status"],
            "created_at": lab["created_at"]
        })

    result.sort(key=lambda x: x["created_at"], reverse=True)
    return result

# Background Task
async def run_pipeline(lab_id: str, prompt: str, dry_run: bool, enable_rca: bool):
    try:
        labs[lab_id]["status"] = "planner_running"
        labs[lab_id]["current_agent"] = "planner"
        labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

        # Import ADK pipeline
        from adk_agents.pipeline import create_lab_pipeline
        from google.adk import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types

        # Create pipeline
        pipeline = create_lab_pipeline(
            include_validation=not dry_run,
            include_rca=enable_rca
        )

        # Initialize session
        session_service = InMemorySessionService()
        session_id = lab_id

        await session_service.create_session(
            app_name="adk_agents",
            user_id="api",
            session_id=session_id
        )

        # Create runner
        runner = Runner(
            agent=pipeline,
            app_name="adk_agents",
            session_service=session_service
        )

        # Run pipeline
        message = types.Content(parts=[types.Part(text=prompt)], role="user")
        events = list(runner.run(user_id="api", session_id=session_id, new_message=message))

        # TODO: Parse events to update status in real-time
        # For now, just update at the end

        # Extract final outputs
        session = await session_service.get_session(
            app_name="adk_agents",
            user_id="api",
            session_id=session_id
        )

        labs[lab_id]["progress"] = {
            "exercise_spec": session.state.get("exercise_spec"),
            "design_output": session.state.get("design_output"),
            "draft_lab_guide": session.state.get("draft_lab_guide"),
            "validation_result": session.state.get("validation_result"),
            "patch_plan": session.state.get("patch_plan")
        }
        labs[lab_id]["status"] = "completed"
        labs[lab_id]["current_agent"] = None

    except Exception as e:
        labs[lab_id]["status"] = "failed"
        labs[lab_id]["error"] = str(e)
        labs[lab_id]["current_agent"] = None
    finally:
        labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

---

## Testing with Frontend

### Step 1: Start Backend API
```bash
cd orchestrator
uvicorn api_server:app --reload --port 8080
```

### Step 2: Configure Frontend
```bash
cd frontend
echo 'NEXT_PUBLIC_ORCHESTRATOR_URL=http://localhost:8080' > .env.local
```

Edit `lib/api.ts`:
```typescript
const USE_MOCK_DATA = false; // Switch to real backend
```

### Step 3: Start Frontend
```bash
npm run dev
```

### Step 4: Test End-to-End
1. Open http://localhost:3000
2. Click "Create New Lab"
3. Enter prompt: "Create a CCNA static routing lab with 2 routers"
4. Watch progress tracker update in real-time
5. Verify all panels populate with data

---

## Performance Considerations

### In-Memory Storage
- **For MVP:** In-memory `dict` is acceptable
- **For Production:** Consider Redis or database
  ```python
  # Future: Replace with Redis
  import redis
  r = redis.Redis(host='localhost', port=6379, db=0)
  labs = {}  # Replace with r.hgetall(), r.hset(), etc.
  ```

### Concurrent Labs
- Multiple labs can run simultaneously (FastAPI background tasks)
- ADK Runner uses InMemorySessionService - confirm thread safety
- Consider adding `max_concurrent_labs` limit if needed

### Long Polling vs SSE
- MVP uses 3-second polling (simple, works everywhere)
- Future: Consider Server-Sent Events (SSE) for true real-time
  ```python
  from sse_starlette.sse import EventSourceResponse

  @app.get("/api/labs/{lab_id}/stream")
  async def stream_lab_status(lab_id: str):
      async def event_generator():
          while labs[lab_id]["status"] not in ["completed", "failed"]:
              yield {"data": labs[lab_id]}
              await asyncio.sleep(1)
      return EventSourceResponse(event_generator())
  ```

---

## Error Handling

### Common Errors

1. **Pipeline Timeout**
   ```python
   import asyncio
   try:
       await asyncio.wait_for(run_pipeline(...), timeout=600)  # 10 min max
   except asyncio.TimeoutError:
       labs[lab_id]["status"] = "failed"
       labs[lab_id]["error"] = "Pipeline execution timed out"
   ```

2. **ADK Errors**
   - Catch `Exception` in `run_pipeline()`
   - Log full traceback
   - Set `labs[lab_id]["error"]` with user-friendly message

3. **Missing Environment Variables**
   ```python
   import os
   if not os.getenv("GOOGLE_API_KEY"):
       raise RuntimeError("GOOGLE_API_KEY not set")
   ```

---

## Security Considerations

### For MVP (Hackathon)
- ✅ CORS configured for localhost + Cloud Run
- ✅ No authentication (allowed for demo)
- ✅ In-memory storage (no data persistence)

### For Production (Future)
- [ ] Add API key authentication
- [ ] Rate limiting (per user/IP)
- [ ] Input validation (prompt length, sanitization)
- [ ] Persistent storage with access controls
- [ ] Audit logging

---

## Deployment to Cloud Run

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY orchestrator/ ./orchestrator/
COPY orchestrator/api_server.py .

# Expose port
EXPOSE 8080

# Run server
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Deploy
```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/PROJECT/netgenius/netgenius-api

gcloud run deploy netgenius-api \
  --image us-central1-docker.pkg.dev/PROJECT/netgenius/netgenius-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_API_KEY=${GOOGLE_API_KEY}" \
  --memory 2Gi \
  --cpu 2 \
  --timeout 600 \
  --min-instances 0 \
  --max-instances 10
```

---

## Summary

### What to Build
1. FastAPI server with 4 endpoints
2. In-memory lab storage
3. Background task runner for ADK pipeline
4. Status tracking as agents progress

### Estimated Time
- Basic endpoints: **1 hour**
- Pipeline integration: **1-2 hours**
- Status tracking: **1 hour**
- Testing + debugging: **1 hour**
- **Total: 3-4 hours**

### Success Criteria
- ✅ Frontend can create labs via `POST /api/labs/create`
- ✅ Frontend polls `GET /api/labs/{id}/status` and sees progress
- ✅ Status updates from `pending` → `planner_running` → ... → `completed`
- ✅ All outputs populate in frontend UI (topology, configs, guide, validation)
- ✅ Lab library shows all created labs

---

## Questions?

If you have questions about:
- **ADK Pipeline Integration:** Check `orchestrator/main_adk.py` for working example
- **Data Models:** See `orchestrator/schemas/*.py`
- **Frontend Expectations:** See `frontend/lib/types.ts` and `frontend/lib/api.ts`

**The frontend is ready and waiting!** Build the API and you'll have a fully functional system. 🚀
