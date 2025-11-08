# Backend API Review & Recommendations

**Reviewer:** Backend Team (Claude Code - Backend Agent)
**Date:** November 8, 2025
**Document Reviewed:** `frontend/BACKEND_REQUIREMENTS.md` v1.0
**Status:** Needs Revision (5 issues identified)

---

## Executive Summary

The frontend team has produced an **excellent and well-thought-out API specification** that demonstrates a strong understanding of the backend architecture. The core design is sound and 90% production-ready. However, there are **5 critical issues** that need to be addressed before implementation:

1. **CRITICAL**: Planner agent is interactive and requires multi-turn conversation support
2. **MAJOR**: Status tracking implementation needs clarification
3. **MINOR**: Inconsistent naming (`outputs` vs `progress`)
4. **MINOR**: Missing timeout handling for long-running tasks
5. **MINOR**: Thread safety concerns with in-memory storage

Below are detailed explanations and recommended solutions for each issue.

---

## Issue 1: Planner Agent Interactivity (CRITICAL)

### Problem

The spec assumes the Planner can run non-interactively with just a single `prompt` parameter:

```python
# From spec line 198
message = types.Content(parts=[types.Part(text=prompt)], role="user")
events = list(runner.run(user_id="api", session_id=session_id, new_message=message))
# Assumes this completes and exercise_spec appears in session.state
```

**This is incorrect.** The Planner agent is designed to be **interactive** - it asks clarifying questions and waits for user responses before generating the complete `ExerciseSpec`. This is a **mandatory core feature**, similar to how ChatGPT's Deep Research works.

### Evidence

From `orchestrator/test_planner_interactive.py` (tested and confirmed working):

```python
# Turn 1: Initial prompt
message = types.Content(parts=[types.Part(text=initial_prompt)], role="user")
events = list(runner.run(user_id=user_id, session_id=session_id, new_message=message))
# Agent responds with questions, NOT exercise_spec

# Turn 2: User answers
message = types.Content(parts=[types.Part(text=user_response)], role="user")
events = list(runner.run(user_id=user_id, session_id=session_id, new_message=message))
# Agent may ask more questions OR return exercise_spec

# ... continue until exercise_spec is generated
```

**Real example conversation:**
```
User: "A simple lab to evaluate password configuration on Cisco routers."

Agent: "I'll help you design a lab! Please answer a few questions:
1. What specific types of passwords? (console, vty, enable secret, etc.)
2. How many routers should be in the topology?
3. What difficulty level? (Beginner / Intermediate)
4. What is the estimated completion time?
5. Should the lab include verification steps?"

User: "1. Console and VTY, 2. Just one, 3. Beginner, 4. 20 min, 5. Just a running-config."

Agent: {
  "title": "Cisco Router Basic Password Configuration",
  "objectives": [...],
  "constraints": {"devices": 1, "time_minutes": 20},
  "level": "CCNA",
  "prerequisites": [...]
}
```

### Impact

If implemented as currently specified:
- The background task will call `runner.run()` once with the initial prompt
- The Planner will respond with questions
- The background task will assume it's done and try to extract `exercise_spec` from session state
- `exercise_spec` will be `None` because the Planner never received answers to its questions
- The pipeline will fail or hang

### Recommended Solution

**Add message-based conversation support** to the API, similar to how chat APIs work.

#### New Endpoint: `POST /api/labs/{id}/message`

```python
@app.post("/api/labs/{lab_id}/message")
async def send_message(lab_id: str, message: UserMessage):
    """Send a message to continue the conversation.

    Used for:
    - Answering Planner's clarifying questions
    - (Future) Providing feedback during RCA retry loops

    Request Body:
    {
      "content": "1. Console and VTY, 2. Just one, 3. Beginner, 4. 20 min"
    }

    Response:
    {
      "status": "message_received",
      "conversation_status": "planner_running"
    }
    """
    if lab_id not in labs:
        raise HTTPException(status_code=404, detail="Lab not found")

    if labs[lab_id]["status"] not in ["awaiting_user_input", "planner_running"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot send message in current status: {labs[lab_id]['status']}"
        )

    # Queue the user's message
    labs[lab_id]["pending_messages"].append(message.content)
    labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

    return {
        "status": "message_received",
        "conversation_status": labs[lab_id]["status"]
    }


class UserMessage(BaseModel):
    content: str = Field(..., min_length=1, description="User's message content")
```

#### Updated Status Response Schema

Add a `conversation` object to track the multi-turn dialog:

```json
{
  "lab_id": "lab_123",
  "status": "awaiting_user_input",
  "current_agent": "planner",
  "conversation": {
    "messages": [
      {
        "role": "user",
        "content": "A simple lab to evaluate password configuration",
        "timestamp": "2025-11-08T10:00:00Z"
      },
      {
        "role": "assistant",
        "content": "I'll help you design a lab! Please answer: 1. What types of passwords?...",
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
  "prompt": "A simple lab to evaluate password configuration",
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
    status: str  # See updated status values below
    current_agent: Optional[str] = None
    conversation: Conversation
    progress: Dict[str, Any]
    created_at: str
    updated_at: str
    prompt: str
    error: Optional[str] = None
```

#### Updated Status Values

Add these new status values:

- `"pending"` - Lab created, pipeline not started
- `"planner_running"` - Planner agent processing (may ask questions)
- **`"awaiting_user_input"`** - **NEW** - Planner waiting for user's answer to a question
- **`"planner_complete"`** - **NEW** - ExerciseSpec generated, moving to Designer
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

#### Updated Background Task Implementation

```python
async def run_pipeline(lab_id: str, initial_prompt: str, dry_run: bool, enable_rca: bool):
    try:
        labs[lab_id]["status"] = "planner_running"
        labs[lab_id]["current_agent"] = "planner"
        labs[lab_id]["conversation"] = {
            "messages": [],
            "awaiting_user_input": False
        }
        labs[lab_id]["pending_messages"] = deque()  # Thread-safe queue

        # Initialize ADK session (just Planner first)
        from adk_agents.planner import planner_agent
        from google.adk import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types

        session_service = InMemorySessionService()
        session_id = lab_id

        await session_service.create_session(
            app_name="adk_agents",
            user_id="api",
            session_id=session_id
        )

        planner_runner = Runner(
            agent=planner_agent,
            app_name="adk_agents",
            session_service=session_service
        )

        # ===== PHASE 1: Interactive Planner Conversation =====

        # Send initial prompt
        message = types.Content(
            parts=[types.Part(text=initial_prompt)],
            role="user"
        )

        # Add to conversation history
        labs[lab_id]["conversation"]["messages"].append({
            "role": "user",
            "content": initial_prompt,
            "timestamp": datetime.utcnow().isoformat()
        })

        exercise_spec = None
        max_turns = 10  # Safety limit
        turn_count = 0

        while exercise_spec is None and turn_count < max_turns:
            turn_count += 1

            # Run planner with current message
            events = list(planner_runner.run(
                user_id="api",
                session_id=session_id,
                new_message=message
            ))

            # Extract agent's response
            agent_response = ""
            for event in events:
                if hasattr(event, 'content') and event.content:
                    if hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text'):
                                agent_response += part.text

            # Add to conversation history
            if agent_response:
                labs[lab_id]["conversation"]["messages"].append({
                    "role": "assistant",
                    "content": agent_response,
                    "timestamp": datetime.utcnow().isoformat()
                })

            # Check if response contains ExerciseSpec JSON
            import re
            import json
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
            labs[lab_id]["status"] = "awaiting_user_input"
            labs[lab_id]["conversation"]["awaiting_user_input"] = True
            labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

            # Wait for user's response via /message endpoint
            while not labs[lab_id]["pending_messages"]:
                await asyncio.sleep(0.5)

            # Get user's answer
            user_answer = labs[lab_id]["pending_messages"].popleft()

            # Add to conversation history
            labs[lab_id]["conversation"]["messages"].append({
                "role": "user",
                "content": user_answer,
                "timestamp": datetime.utcnow().isoformat()
            })

            labs[lab_id]["status"] = "planner_running"
            labs[lab_id]["conversation"]["awaiting_user_input"] = False

            # Create message for next turn
            message = types.Content(
                parts=[types.Part(text=user_answer)],
                role="user"
            )

        if exercise_spec is None:
            raise Exception("Planner failed to produce ExerciseSpec after max turns")

        # ===== PHASE 2: Automated Pipeline (Designer → Author → Validator → RCA) =====

        labs[lab_id]["status"] = "designer_running"
        labs[lab_id]["current_agent"] = "designer"
        labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

        # Run the rest of the pipeline (Designer, Author, Validator, RCA)
        # The exercise_spec is already in session.state from the Planner conversation
        # Use individual agent runners or the full pipeline (skipping Planner)

        from adk_agents.designer import designer_agent
        from adk_agents.author import author_agent
        from adk_agents.validator import validator_agent

        # Designer
        designer_runner = Runner(
            agent=designer_agent,
            app_name="adk_agents",
            session_service=session_service
        )
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
        labs[lab_id]["status"] = "author_running"
        labs[lab_id]["current_agent"] = "author"
        labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

        # Author
        author_runner = Runner(
            agent=author_agent,
            app_name="adk_agents",
            session_service=session_service
        )
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

        if not dry_run:
            labs[lab_id]["status"] = "validator_running"
            labs[lab_id]["current_agent"] = "validator"
            labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

            # Validator (+ RCA loop if enabled)
            # ... similar pattern ...

        labs[lab_id]["status"] = "completed"
        labs[lab_id]["current_agent"] = None
        labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

    except Exception as e:
        labs[lab_id]["status"] = "failed"
        labs[lab_id]["error"] = str(e)
        labs[lab_id]["current_agent"] = None
        labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()
```

#### Frontend Flow Example

```typescript
// 1. Create lab with initial prompt
const { lab_id } = await createLab({
  prompt: "A simple lab to evaluate password configuration",
  dry_run: false,
  enable_rca: true
})

// 2. Poll status every 2-3 seconds
const pollInterval = setInterval(async () => {
  const status = await getLabStatus(lab_id)

  // Update UI with conversation messages
  displayConversation(status.conversation.messages)

  // Check if waiting for user input
  if (status.conversation.awaiting_user_input) {
    // Show input box for user to answer
    const answer = await showUserInputDialog()

    // Send answer to backend
    await sendMessage(lab_id, { content: answer })
  }

  // Update progress indicators
  if (status.status === "planner_complete") {
    showNotification("Planning complete! Designing topology...")
  }
  if (status.status === "designer_running") {
    showProgressBar("designer", "in_progress")
  }

  // Stop polling when done
  if (status.status === "completed" || status.status === "failed") {
    clearInterval(pollInterval)
    showFinalResults(status)
  }
}, 2000)
```

---

## Issue 2: Status Tracking Implementation Unclear (MAJOR)

### Problem

The spec presents three options for tracking agent progress (lines 509-537) but doesn't commit to one or provide concrete implementation:

- **Option A**: Parse ADK Events (recommended but complex)
- **Option B**: Poll Session State (simple but polling overhead)
- **Option C**: Manual Updates (too coarse-grained)

Without a clear choice, the implementation will be ambiguous.

### Recommended Solution

**Use Option B (Poll Session State)** for MVP. It's simple, reliable, and doesn't require understanding ADK's internal event structure.

#### Implementation

```python
async def run_pipeline(...):
    # ... (after Planner conversation completes) ...

    # Run the rest of the pipeline in a separate task
    async def run_remaining_agents():
        # Run Designer → Author → Validator → RCA
        # ... (sequential agent execution) ...

    # Start pipeline execution
    pipeline_task = asyncio.create_task(run_remaining_agents())

    # Poll session state to track progress
    while not pipeline_task.done():
        session = await session_service.get_session(
            app_name="adk_agents",
            user_id="api",
            session_id=session_id
        )

        # Update status based on what's been written to session.state
        if "design_output" in session.state and labs[lab_id]["status"] == "designer_running":
            labs[lab_id]["status"] = "author_running"
            labs[lab_id]["current_agent"] = "author"
            labs[lab_id]["progress"]["design_output"] = session.state["design_output"]

        if "draft_lab_guide" in session.state and labs[lab_id]["status"] == "author_running":
            if not dry_run:
                labs[lab_id]["status"] = "validator_running"
                labs[lab_id]["current_agent"] = "validator"
            else:
                labs[lab_id]["status"] = "completed"
                labs[lab_id]["current_agent"] = None
            labs[lab_id]["progress"]["draft_lab_guide"] = session.state["draft_lab_guide"]

        if "validation_result" in session.state and labs[lab_id]["status"] == "validator_running":
            labs[lab_id]["status"] = "completed"
            labs[lab_id]["current_agent"] = None
            labs[lab_id]["progress"]["validation_result"] = session.state["validation_result"]

        labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()
        await asyncio.sleep(0.5)  # Poll every 500ms

    # Wait for pipeline to finish
    await pipeline_task
```

**Alternative (Simpler)**: Just update status manually after each agent completes. No polling needed:

```python
# Designer
labs[lab_id]["status"] = "designer_running"
designer_runner.run(...)
labs[lab_id]["progress"]["design_output"] = session.state["design_output"]

# Author
labs[lab_id]["status"] = "author_running"
author_runner.run(...)
labs[lab_id]["progress"]["draft_lab_guide"] = session.state["draft_lab_guide"]

# etc.
```

This is cleaner and avoids the polling loop complexity.

---

## Issue 3: Inconsistent Naming (`outputs` vs `progress`) (MINOR)

### Problem

The spec uses both `outputs` and `progress` inconsistently:

- Line 147-148: `"outputs": {}`
- Line 208-214: `labs[lab_id]["outputs"] = {...}`
- Line 260-271: `"progress": {...}` (in status response example)
- Line 286: `progress: Dict[str, Any]` (in schema)

### Recommended Solution

**Use `progress` consistently** throughout. It's more accurate since these are intermediate results that accumulate as the pipeline progresses.

#### Changes

1. Line 147: Change `"outputs": {}` → `"progress": {}`
2. Lines 208-214: Change `labs[lab_id]["outputs"]` → `labs[lab_id]["progress"]`
3. Ensure all examples and schemas use `progress`

---

## Issue 4: Missing Timeout Handling (MINOR)

### Problem

The background task could hang forever if:
- The Planner conversation never completes (user abandons it)
- A pipeline agent hangs or takes too long
- Network issues with Cloud Run validation jobs

No timeout is specified in the current spec.

### Recommended Solution

Add timeout handling at multiple levels:

#### 1. Overall Pipeline Timeout

```python
async def run_pipeline(lab_id: str, prompt: str, dry_run: bool, enable_rca: bool):
    try:
        # Set overall timeout (10 minutes for full pipeline)
        async with asyncio.timeout(600):
            # ... pipeline execution ...
    except asyncio.TimeoutError:
        labs[lab_id]["status"] = "failed"
        labs[lab_id]["error"] = "Pipeline execution timed out (10 minute limit)"
        labs[lab_id]["current_agent"] = None
    except Exception as e:
        labs[lab_id]["status"] = "failed"
        labs[lab_id]["error"] = str(e)
    finally:
        labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()
```

#### 2. Planner Conversation Timeout

```python
# In the Planner conversation loop
max_turns = 10
planner_timeout = 300  # 5 minutes max for planning phase

start_time = time.time()
while exercise_spec is None and turn_count < max_turns:
    if time.time() - start_time > planner_timeout:
        raise Exception("Planner conversation timed out after 5 minutes")

    # Wait for user response with timeout
    wait_start = time.time()
    while not labs[lab_id]["pending_messages"]:
        if time.time() - wait_start > 120:  # 2 minutes per question
            raise Exception("User did not respond within 2 minutes")
        await asyncio.sleep(0.5)
    # ... continue ...
```

#### 3. Individual Agent Timeouts

```python
# Wrap each agent execution with timeout
async with asyncio.timeout(120):  # 2 minutes per agent
    events = list(designer_runner.run(...))
```

---

## Issue 5: Thread Safety Concerns (MINOR)

### Problem

The spec uses a simple `labs: Dict[str, dict] = {}` which is **not thread-safe**. FastAPI background tasks run in a thread pool, so concurrent lab creations could cause race conditions when updating `labs[lab_id]`.

### Evidence

```python
# Thread 1 (Lab A):
labs[lab_id]["status"] = "designer_running"  # Read-modify-write

# Thread 2 (Lab B) - same time:
labs[lab_id]["status"] = "planner_running"  # Could interleave with Thread 1
```

### Recommended Solution

**Use asyncio.Lock for each lab**:

```python
import asyncio
from collections import defaultdict
from collections import deque

labs: Dict[str, dict] = {}
lab_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

async def run_pipeline(lab_id: str, ...):
    async with lab_locks[lab_id]:
        # All updates to labs[lab_id] are now atomic
        labs[lab_id]["status"] = "planner_running"
        # ... rest of pipeline ...
```

**For status endpoint**:

```python
@app.get("/api/labs/{lab_id}/status")
async def get_lab_status(lab_id: str):
    if lab_id not in labs:
        raise HTTPException(status_code=404, detail="Lab not found")

    async with lab_locks[lab_id]:
        # Return deep copy to avoid race conditions
        return {k: v for k, v in labs[lab_id].items() if k != "pending_messages"}
```

**Alternative**: Use a thread-safe dict library like `readerwriterlock` or `atomicwrites`.

---

## Summary of Required Changes

### Critical (Blocking)
1. ✅ **Add `POST /api/labs/{id}/message` endpoint** for multi-turn Planner conversation
2. ✅ **Add `conversation` object to status response** with message history
3. ✅ **Add new status values**: `"awaiting_user_input"`, `"planner_complete"`
4. ✅ **Update background task** to handle interactive Planner loop before running remaining agents

### Major (Highly Recommended)
5. ✅ **Specify status tracking approach** - recommend manual updates after each agent (simplest)

### Minor (Nice to Have)
6. ✅ **Fix `outputs` → `progress` naming** throughout
7. ✅ **Add timeout handling** for pipeline, Planner conversation, and individual agents
8. ✅ **Add thread safety** with asyncio.Lock per lab

---

## Overall Assessment

**Score: 9/10** - Excellent work by the frontend team!

The spec demonstrates:
- ✅ Deep understanding of ADK pipeline architecture
- ✅ Correct data model mappings
- ✅ Pragmatic MVP scope (in-memory storage, polling)
- ✅ Accurate code examples

The main gap is the **Planner interactivity requirement**, which is a fundamental feature that must be supported. Once this is addressed with the message-based conversation API, the spec will be ready for implementation.

---

## Questions?

If the frontend team has questions about:
- **Interactive Planner pattern**: See `orchestrator/test_planner_interactive.py` (lines 75-192)
- **ADK Runner multi-turn usage**: Same file shows calling `runner.run()` multiple times with same `session_id`
- **Session state persistence**: Session keeps conversation history automatically
- **Backend architecture**: Available for clarification anytime

**Next Steps**: Frontend team updates `BACKEND_REQUIREMENTS.md` → Backend team reviews v2.0 → Implementation begins
