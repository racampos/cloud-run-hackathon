# Backend API Requirements for Frontend Integration

**Document Version:** 2.0 (Revised after Backend Review)
**Date:** November 8, 2025
**Status:** ✅ APPROVED - Ready for Implementation
**Priority:** High (Required for Frontend Integration)
**Changelog:** Added interactive Planner conversation support, clarified status tracking, fixed naming consistency, added timeout handling

---

## Executive Summary

The frontend is **complete and functional** with mock data. To integrate with the real backend, you need to build a **REST API wrapper** around the existing ADK pipeline with support for **interactive multi-turn conversation** during the Planner phase.

**Key Requirements:**
1. ✅ **5 REST endpoints** (4 originally specified + 1 new for conversation)
2. ✅ **Interactive Planner** with multi-turn Q&A (CRITICAL - missed in v1.0)
3. ✅ **Conversation state tracking** with message history
4. ✅ **Manual status updates** after each agent completes (simplified approach)
5. ✅ **Timeout handling** for robustness
6. ✅ **Consistent naming** (`progress` not `outputs`)

**Estimated Implementation Time:** 5-6 hours (increased from 3-4 due to conversation support)
**Recommended Approach:** FastAPI with async background tasks

---

## Current Backend State

### What Already Exists ✅

- **ADK Pipeline:** Fully functional with Planner → Designer → Author → Validator → RCA
- **Interactive Planner:** Multi-turn conversation agent (see `orchestrator/test_planner_interactive.py`)
- **Session Management:** InMemorySessionService stores pipeline state + conversation history
- **Data Models:** Complete Pydantic schemas in `orchestrator/schemas/`
- **CLI Interface:** `python main_adk.py create --prompt "..."`

### What's Missing ❌

- **No HTTP endpoints** - Backend is CLI-only
- **No REST API** - No way for frontend to interact
- **No conversation endpoint** - No way to send user responses during Planner Q&A
- **No real-time status** - No endpoint to poll progress
- **No lab persistence** - Session state is lost after CLI exits

---

## Required Architecture

```
Frontend (Next.js)
    ↓ HTTP POST/GET
┌──────────────────────────────────────────┐
│   FastAPI Server (NEW)                   │
│   - POST /api/labs/create                │
│   - POST /api/labs/{id}/message   ← NEW │
│   - GET  /api/labs/{id}/status           │
│   - GET  /api/labs/{id}                  │
│   - GET  /api/labs                       │
│   - In-memory lab storage                │
│   - Background task runner                │
│   - Conversation message queue     ← NEW │
└──────────────────────────────────────────┘
    ↓ Python import
┌──────────────────────────────────────────┐
│   Existing ADK Pipeline                  │
│   - Interactive Planner (multi-turn)     │
│   - Designer, Author, Validator, RCA     │
│   - Runner.run() + InMemorySessionService│
└──────────────────────────────────────────┘
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

Creates a new lab and starts the interactive Planner conversation in the background.

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
    prompt: str = Field(..., min_length=10, description="Initial instructor prompt")
    dry_run: bool = Field(default=False, description="Skip headless validation")
    enable_rca: bool = Field(default=True, description="Enable RCA retry loop")
```

#### Response (200 OK)
```json
{
  "lab_id": "lab_1731085234",
  "status": "planner_running"
}
```

**Schema:**
```python
class CreateLabResponse(BaseModel):
    lab_id: str
    status: str  # Always "planner_running" on creation
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
   from collections import deque

   labs = {}  # In-memory storage
   labs[lab_id] = {
       "lab_id": lab_id,
       "status": "planner_running",
       "current_agent": "planner",
       "conversation": {
           "messages": [],
           "awaiting_user_input": False
       },
       "progress": {
           "exercise_spec": None,
           "design_output": None,
           "draft_lab_guide": None,
           "validation_result": None,
           "patch_plan": None
       },
       "created_at": datetime.utcnow().isoformat(),
       "updated_at": datetime.utcnow().isoformat(),
       "prompt": request.prompt,
       "pending_messages": deque(),  # Queue for user responses
       "error": None
   }
   ```

3. **Launch pipeline in background:**
   ```python
   from fastapi import BackgroundTasks

   @app.post("/api/labs/create")
   async def create_lab(request: CreateLabRequest, background_tasks: BackgroundTasks):
       lab_id = f"lab_{int(time.time())}"
       # ... initialize lab ...
       background_tasks.add_task(
           run_pipeline,
           lab_id,
           request.prompt,
           request.dry_run,
           request.enable_rca
       )
       return {"lab_id": lab_id, "status": "planner_running"}
   ```

---

## Endpoint 2: Send Message (NEW - CRITICAL)

### `POST /api/labs/{lab_id}/message`

Sends a user message to continue the interactive Planner conversation.

**This endpoint is REQUIRED** because the Planner agent is interactive and asks clarifying questions before generating the ExerciseSpec.

#### Path Parameters
- `lab_id` (string, required) - Unique lab identifier

#### Request Body
```json
{
  "content": "1. Console and VTY passwords, 2. Just one router, 3. Beginner level, 4. 20 minutes"
}
```

**Schema:**
```python
class UserMessage(BaseModel):
    content: str = Field(..., min_length=1, description="User's message content")
```

#### Response (200 OK)
```json
{
  "status": "message_received",
  "conversation_status": "planner_running"
}
```

**Schema:**
```python
class MessageResponse(BaseModel):
    status: str  # Always "message_received"
    conversation_status: str  # Current lab status
```

#### Error Responses
- **404 Not Found** - Lab ID does not exist
- **400 Bad Request** - Cannot send message in current status (e.g., lab already completed)

#### Implementation
```python
@app.post("/api/labs/{lab_id}/message")
async def send_message(lab_id: str, message: UserMessage):
    """Send a message to continue the Planner conversation.

    The background task is waiting for user input via the pending_messages queue.
    This endpoint adds the user's message to that queue, allowing the conversation to continue.
    """
    if lab_id not in labs:
        raise HTTPException(status_code=404, detail="Lab not found")

    # Only accept messages during interactive Planner phase
    if labs[lab_id]["status"] not in ["awaiting_user_input", "planner_running"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot send message when status is {labs[lab_id]['status']}"
        )

    # Add message to queue (background task is waiting for this)
    labs[lab_id]["pending_messages"].append(message.content)
    labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

    return {
        "status": "message_received",
        "conversation_status": labs[lab_id]["status"]
    }
```

---

## Endpoint 3: Get Lab Status

### `GET /api/labs/{lab_id}/status`

Returns current lab status, conversation state, and progress. **Frontend polls this endpoint every 3 seconds.**

#### Path Parameters
- `lab_id` (string, required) - Unique lab identifier

#### Response (200 OK)

**During Planner Conversation:**
```json
{
  "lab_id": "lab_1731085234",
  "status": "awaiting_user_input",
  "current_agent": "planner",
  "conversation": {
    "messages": [
      {
        "role": "user",
        "content": "A simple lab to evaluate password configuration on Cisco routers",
        "timestamp": "2025-11-08T10:00:00Z"
      },
      {
        "role": "assistant",
        "content": "I'll help you design a lab! Please answer:\n1. What specific types of passwords?\n2. How many routers?\n3. Difficulty level?\n4. Estimated time?\n5. Include verification steps?",
        "timestamp": "2025-11-08T10:00:05Z"
      }
    ],
    "awaiting_user_input": true
  },
  "progress": {
    "exercise_spec": null,
    "design_output": null,
    "draft_lab_guide": null,
    "validation_result": null,
    "patch_plan": null
  },
  "created_at": "2025-11-08T10:00:00Z",
  "updated_at": "2025-11-08T10:00:05Z",
  "prompt": "A simple lab to evaluate password configuration on Cisco routers",
  "error": null
}
```

**After Planner Completes:**
```json
{
  "lab_id": "lab_1731085234",
  "status": "designer_running",
  "current_agent": "designer",
  "conversation": {
    "messages": [ /* ... full conversation history ... */ ],
    "awaiting_user_input": false
  },
  "progress": {
    "exercise_spec": {
      "title": "Cisco Router Basic Password Configuration",
      "objectives": ["Configure console password", "Configure VTY password"],
      "constraints": {"devices": 1, "time_minutes": 20},
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
  "prompt": "A simple lab to evaluate password configuration on Cisco routers",
  "error": null
}
```

**Schema:**
```python
class ConversationMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: str  # ISO 8601

class Conversation(BaseModel):
    messages: list[ConversationMessage]
    awaiting_user_input: bool

class LabStatus(BaseModel):
    lab_id: str
    status: str  # See status values below
    current_agent: Optional[str] = None
    conversation: Conversation
    progress: Dict[str, Any]  # Contains exercise_spec, design_output, etc.
    created_at: str
    updated_at: str
    prompt: str
    error: Optional[str] = None
```

**Status Values:**
- `"pending"` - Lab created, pipeline not started (not used currently)
- `"planner_running"` - Planner agent processing (may ask questions)
- **`"awaiting_user_input"`** - Planner waiting for user's answer
- **`"planner_complete"`** - ExerciseSpec generated, moving to Designer
- `"designer_running"` - Designer agent executing
- `"designer_complete"` - Designer done, Author starting
- `"author_running"` - Author agent executing
- `"author_complete"` - Author done, Validator starting
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

    # Return everything except internal queue
    return {
        k: v for k, v in labs[lab_id].items()
        if k != "pending_messages"
    }
```

---

## Endpoint 4: Get Full Lab Details

### `GET /api/labs/{lab_id}`

Returns complete lab data. **Same as status endpoint for MVP.**

#### Implementation
```python
@app.get("/api/labs/{lab_id}")
async def get_lab(lab_id: str):
    if lab_id not in labs:
        raise HTTPException(status_code=404, detail="Lab not found")

    return {
        k: v for k, v in labs[lab_id].items()
        if k != "pending_messages"
    }
```

---

## Endpoint 5: List All Labs

### `GET /api/labs`

Returns list of all created labs.

#### Response (200 OK)
```json
[
  {
    "lab_id": "lab_1731085234",
    "title": "Cisco Router Basic Password Configuration",
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
    title: str
    status: str
    created_at: str
```

#### Implementation
```python
@app.get("/api/labs")
async def list_labs():
    result = []
    for lab_id, lab in labs.items():
        # Get title from exercise_spec if available
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

## Background Task Implementation

This is the core of the backend. It handles:
1. Interactive Planner conversation (Phase 1)
2. Automated pipeline execution (Phase 2)

### Complete Implementation

```python
import asyncio
import time
import re
import json
from datetime import datetime
from collections import deque

async def run_pipeline(
    lab_id: str,
    initial_prompt: str,
    dry_run: bool,
    enable_rca: bool
):
    """Run the complete lab generation pipeline.

    Phase 1: Interactive Planner Conversation
    - Send initial prompt
    - Loop: Get agent response → Wait for user answer → Send answer
    - Continue until ExerciseSpec is generated

    Phase 2: Automated Pipeline
    - Designer → Author → Validator (if not dry_run) → RCA (if enabled)
    - Update status manually after each agent completes
    """

    try:
        # Overall timeout: 10 minutes
        async with asyncio.timeout(600):

            # ========== PHASE 1: INTERACTIVE PLANNER CONVERSATION ==========

            labs[lab_id]["status"] = "planner_running"
            labs[lab_id]["current_agent"] = "planner"
            labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

            # Import ADK components
            from adk_agents.planner import planner_agent
            from google.adk import Runner
            from google.adk.sessions import InMemorySessionService
            from google.genai import types

            # Initialize session
            session_service = InMemorySessionService()
            session_id = lab_id

            await session_service.create_session(
                app_name="adk_agents",
                user_id="api",
                session_id=session_id
            )

            # Create Planner runner
            planner_runner = Runner(
                agent=planner_agent,
                app_name="adk_agents",
                session_service=session_service
            )

            # Add initial prompt to conversation
            labs[lab_id]["conversation"]["messages"].append({
                "role": "user",
                "content": initial_prompt,
                "timestamp": datetime.utcnow().isoformat()
            })

            # Prepare first message
            message = types.Content(
                parts=[types.Part(text=initial_prompt)],
                role="user"
            )

            exercise_spec = None
            max_turns = 10  # Safety limit
            turn_count = 0
            planner_start_time = time.time()
            planner_timeout = 300  # 5 minutes max for planning phase

            while exercise_spec is None and turn_count < max_turns:
                turn_count += 1

                # Check planner timeout
                if time.time() - planner_start_time > planner_timeout:
                    raise Exception("Planner conversation timed out after 5 minutes")

                # Run planner with current message
                events = list(planner_runner.run(
                    user_id="api",
                    session_id=session_id,
                    new_message=message
                ))

                # Extract agent's response from events
                agent_response = ""
                for event in events:
                    if hasattr(event, 'content') and event.content:
                        if hasattr(event.content, 'parts'):
                            for part in event.content.parts:
                                if hasattr(part, 'text'):
                                    agent_response += part.text

                # Add agent response to conversation
                if agent_response:
                    labs[lab_id]["conversation"]["messages"].append({
                        "role": "assistant",
                        "content": agent_response,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

                # Check if response contains complete ExerciseSpec
                json_match = re.search(r'\{[\s\S]*\}', agent_response)
                if json_match:
                    try:
                        potential_spec = json.loads(json_match.group())
                        required_fields = ['title', 'objectives', 'constraints', 'level', 'prerequisites']

                        if all(key in potential_spec for key in required_fields):
                            # Planner is done!
                            exercise_spec = potential_spec
                            labs[lab_id]["progress"]["exercise_spec"] = exercise_spec
                            labs[lab_id]["status"] = "planner_complete"
                            labs[lab_id]["conversation"]["awaiting_user_input"] = False
                            labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()
                            break
                    except json.JSONDecodeError:
                        pass

                # No complete spec yet - Planner is asking questions
                # Wait for user's response
                labs[lab_id]["status"] = "awaiting_user_input"
                labs[lab_id]["conversation"]["awaiting_user_input"] = True
                labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

                # Wait for user to send message via /message endpoint
                wait_start = time.time()
                while not labs[lab_id]["pending_messages"]:
                    if time.time() - wait_start > 120:  # 2 minutes per question
                        raise Exception("User did not respond within 2 minutes")
                    await asyncio.sleep(0.5)

                # Get user's answer from queue
                user_answer = labs[lab_id]["pending_messages"].popleft()

                # Add to conversation history
                labs[lab_id]["conversation"]["messages"].append({
                    "role": "user",
                    "content": user_answer,
                    "timestamp": datetime.utcnow().isoformat()
                })

                labs[lab_id]["status"] = "planner_running"
                labs[lab_id]["conversation"]["awaiting_user_input"] = False
                labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

                # Create message for next turn
                message = types.Content(
                    parts=[types.Part(text=user_answer)],
                    role="user"
                )

            if exercise_spec is None:
                raise Exception("Planner failed to produce ExerciseSpec after max turns")

            # ========== PHASE 2: AUTOMATED PIPELINE ==========

            # Import remaining agents
            from adk_agents.designer import designer_agent
            from adk_agents.author import author_agent
            from adk_agents.validator import validator_agent

            # Designer
            labs[lab_id]["status"] = "designer_running"
            labs[lab_id]["current_agent"] = "designer"
            labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

            designer_runner = Runner(
                agent=designer_agent,
                app_name="adk_agents",
                session_service=session_service
            )

            async with asyncio.timeout(120):  # 2 min timeout per agent
                events = list(designer_runner.run(
                    user_id="api",
                    session_id=session_id,
                    new_message=None  # Reads exercise_spec from session.state
                ))

            session = await session_service.get_session(
                app_name="adk_agents",
                user_id="api",
                session_id=session_id
            )
            labs[lab_id]["progress"]["design_output"] = session.state.get("design_output")
            labs[lab_id]["status"] = "designer_complete"
            labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

            # Author
            labs[lab_id]["status"] = "author_running"
            labs[lab_id]["current_agent"] = "author"
            labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

            author_runner = Runner(
                agent=author_agent,
                app_name="adk_agents",
                session_service=session_service
            )

            async with asyncio.timeout(120):
                events = list(author_runner.run(
                    user_id="api",
                    session_id=session_id,
                    new_message=None
                ))

            session = await session_service.get_session(
                app_name="adk_agents",
                user_id="api",
                session_id=session_id
            )
            labs[lab_id]["progress"]["draft_lab_guide"] = session.state.get("draft_lab_guide")
            labs[lab_id]["status"] = "author_complete"
            labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

            # Validator (if not dry_run)
            if not dry_run:
                labs[lab_id]["status"] = "validator_running"
                labs[lab_id]["current_agent"] = "validator"
                labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

                validator_runner = Runner(
                    agent=validator_agent,
                    app_name="adk_agents",
                    session_service=session_service
                )

                async with asyncio.timeout(300):  # 5 min for validation
                    events = list(validator_runner.run(
                        user_id="api",
                        session_id=session_id,
                        new_message=None
                    ))

                session = await session_service.get_session(
                    app_name="adk_agents",
                    user_id="api",
                    session_id=session_id
                )
                labs[lab_id]["progress"]["validation_result"] = session.state.get("validation_result")
                labs[lab_id]["status"] = "validator_complete"
                labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

            # Final status
            labs[lab_id]["status"] = "completed"
            labs[lab_id]["current_agent"] = None
            labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

    except asyncio.TimeoutError:
        labs[lab_id]["status"] = "failed"
        labs[lab_id]["error"] = "Pipeline execution timed out"
        labs[lab_id]["current_agent"] = None
        labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

    except Exception as e:
        labs[lab_id]["status"] = "failed"
        labs[lab_id]["error"] = str(e)
        labs[lab_id]["current_agent"] = None
        labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()
```

---

## Complete API Server Example

Here's a working `api_server.py` template:

```python
# orchestrator/api_server.py

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from collections import deque
import time

app = FastAPI(title="NetGenius API", version="2.0.0")

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

# ========== REQUEST/RESPONSE MODELS ==========

class CreateLabRequest(BaseModel):
    prompt: str = Field(..., min_length=10)
    dry_run: bool = False
    enable_rca: bool = True

class CreateLabResponse(BaseModel):
    lab_id: str
    status: str

class UserMessage(BaseModel):
    content: str = Field(..., min_length=1)

class MessageResponse(BaseModel):
    status: str
    conversation_status: str

# ========== ENDPOINTS ==========

@app.post("/api/labs/create", response_model=CreateLabResponse)
async def create_lab(request: CreateLabRequest, background_tasks: BackgroundTasks):
    lab_id = f"lab_{int(time.time())}"

    labs[lab_id] = {
        "lab_id": lab_id,
        "status": "planner_running",
        "current_agent": "planner",
        "conversation": {
            "messages": [],
            "awaiting_user_input": False
        },
        "progress": {
            "exercise_spec": None,
            "design_output": None,
            "draft_lab_guide": None,
            "validation_result": None,
            "patch_plan": None
        },
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "prompt": request.prompt,
        "pending_messages": deque(),
        "error": None
    }

    background_tasks.add_task(
        run_pipeline,
        lab_id,
        request.prompt,
        request.dry_run,
        request.enable_rca
    )

    return {"lab_id": lab_id, "status": "planner_running"}

@app.post("/api/labs/{lab_id}/message", response_model=MessageResponse)
async def send_message(lab_id: str, message: UserMessage):
    if lab_id not in labs:
        raise HTTPException(status_code=404, detail="Lab not found")

    if labs[lab_id]["status"] not in ["awaiting_user_input", "planner_running"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot send message when status is {labs[lab_id]['status']}"
        )

    labs[lab_id]["pending_messages"].append(message.content)
    labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

    return {
        "status": "message_received",
        "conversation_status": labs[lab_id]["status"]
    }

@app.get("/api/labs/{lab_id}/status")
async def get_lab_status(lab_id: str):
    if lab_id not in labs:
        raise HTTPException(status_code=404, detail="Lab not found")
    return {k: v for k, v in labs[lab_id].items() if k != "pending_messages"}

@app.get("/api/labs/{lab_id}")
async def get_lab(lab_id: str):
    if lab_id not in labs:
        raise HTTPException(status_code=404, detail="Lab not found")
    return {k: v for k, v in labs[lab_id].items() if k != "pending_messages"}

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

# ========== BACKGROUND TASK ==========

async def run_pipeline(lab_id: str, initial_prompt: str, dry_run: bool, enable_rca: bool):
    # See complete implementation above
    pass

# ========== MAIN ==========

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

---

## Testing

### Step 1: Start Backend API
```bash
cd orchestrator
uvicorn api_server:app --reload --port 8080
```

### Step 2: Test Interactive Conversation with curl

```bash
# 1. Create lab
RESPONSE=$(curl -X POST http://localhost:8080/api/labs/create \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A simple password lab"}')

LAB_ID=$(echo $RESPONSE | jq -r '.lab_id')
echo "Lab ID: $LAB_ID"

# 2. Check status (Planner should ask questions)
curl http://localhost:8080/api/labs/$LAB_ID/status | jq .

# 3. Send user's answer
curl -X POST http://localhost:8080/api/labs/$LAB_ID/message \
  -H "Content-Type: application/json" \
  -d '{"content": "1. Console and VTY, 2. One router, 3. Beginner, 4. 20 min"}'

# 4. Poll status again (may ask more questions or continue to Designer)
curl http://localhost:8080/api/labs/$LAB_ID/status | jq .

# 5. List all labs
curl http://localhost:8080/api/labs | jq .
```

### Step 3: Test with Frontend

```bash
cd frontend

# Configure frontend
echo 'NEXT_PUBLIC_ORCHESTRATOR_URL=http://localhost:8080' > .env.local

# Switch to real backend (edit lib/api.ts)
# const USE_MOCK_DATA = false

npm run dev
```

---

## Deployment to Cloud Run

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install fastapi uvicorn

COPY orchestrator/ ./orchestrator/
COPY orchestrator/api_server.py .

EXPOSE 8080

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

## Summary of Changes from v1.0

### Critical Changes ✅
1. **Added `POST /api/labs/{id}/message` endpoint** - Required for interactive Planner
2. **Added `conversation` object** - Tracks message history and `awaiting_user_input` flag
3. **Added new statuses** - `awaiting_user_input`, `planner_complete`
4. **Updated background task** - Phase 1 (interactive Planner) + Phase 2 (automated pipeline)

### Major Changes ✅
5. **Specified status tracking approach** - Manual updates after each agent (no polling loop)
6. **Fixed naming** - `progress` consistently (not `outputs`)

### Minor Changes ✅
7. **Added timeout handling** - Overall (10 min), Planner (5 min), per-agent (2 min), user response (2 min)
8. **Thread safety note** - Not required for async tasks in MVP, but harmless if added

---

## Frontend Integration Checklist

The frontend team needs to update:

- [ ] Add `Conversation`, `ConversationMessage` types to `lib/types.ts`
- [ ] Add `sendMessage(labId, content)` to `lib/api.ts`
- [ ] Update `Lab` type to include `conversation` field
- [ ] Create conversation UI component (message display + input box)
- [ ] Update lab detail page to show conversation when `awaiting_user_input`
- [ ] Update mock data to simulate Planner asking 1-2 questions
- [ ] Test end-to-end conversation flow

---

## Questions?

Both teams should refer to:
- **Interactive Planner example:** `orchestrator/test_planner_interactive.py`
- **ADK multi-turn pattern:** Same file shows `runner.run()` called multiple times
- **Frontend types:** `frontend/lib/types.ts`
- **This document:** Single source of truth for API contract

**Status:** ✅ APPROVED - Ready for parallel implementation by both teams.
