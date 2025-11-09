# NetGenius API - New Architecture Documentation

## Overview

The NetGenius API has been refactored to separate the Planner agent from the generation pipeline. This enables:
1. **Interactive Planner conversation** - Planner runs independently for requirements gathering
2. **Automated generation pipeline** - Designer → Author → Validator runs as a single SequentialAgent
3. **Progress updates via conversation** - Canned messages injected into Planner's chat showing generation progress

## Architecture Changes

### Previous Architecture (Old)
```
POST /api/labs/create
  ↓
Background Task: run_pipeline()
  ↓
Planner (manual loop) → Designer → Author → Validator
  ↓
Poll GET /api/labs/{lab_id}/status for progress
```

### New Architecture
```
POST /api/labs/create
  ↓ (Creates lab, initializes session)
POST /api/labs/{lab_id}/chat (repeat until done=true)
  ↓ (Planner Q&A, generates exercise_spec)
  ↓ (When done=true: auto-triggers generation)
Background Task: run_generation_pipeline()
  ↓
ADK SequentialAgent: Designer → Author → Validator
  ↓
Canned progress messages injected into Planner conversation
  ↓
Poll GET /api/labs/{lab_id}/status for latest_planner_update
```

## API Endpoints

### 1. Create Lab (Modified)
**Endpoint:** `POST /api/labs/create`

**Request Body:**
```json
{
  "prompt": "Initial user prompt",
  "dry_run": false,
  "enable_rca": true
}
```

**Response:**
```json
{
  "lab_id": "lab_1762718464",
  "message": "Lab created successfully"
}
```

**Status After Creation:** `planner_running`

**Changes:**
- Still creates the lab and initializes ADK session
- NO longer triggers the full pipeline in background
- Planner interaction now happens via separate endpoint

---

### 2. Chat with Planner (NEW)
**Endpoint:** `POST /api/labs/{lab_id}/chat`

**Request Body:**
```json
{
  "message": "User's message to Planner"
}
```

**Response (When Planner needs more info):**
```json
{
  "done": false,
  "response": "What skill level should this lab target? (beginner/intermediate/advanced)"
}
```

**Response (When Planner is done):**
```json
{
  "done": true,
  "response": "Perfect! I have everything I need...",
  "exercise_spec": {
    "title": "Cisco Router Basic Password Configuration",
    "objectives": ["Configure enable secret", "..."],
    "constraints": {...}
  },
  "generation_started": true
}
```

**Behavior:**
- Planner agent runs independently with its own Runner
- Conversation history managed by ADK (`session.events`)
- When `done=true`, the `exercise_spec` is ready in session state
- Lab status changes to `planner_complete`
- **Generation pipeline automatically starts in background** (no need to call /generate)

**Frontend Flow:**
```javascript
// Loop until Planner is done
while (true) {
  const userMessage = await getUserInput();

  const response = await fetch(`/api/labs/${labId}/chat`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: userMessage})
  });

  const data = await response.json();

  displayMessage(data.response);

  if (data.done) {
    // Planner complete! Generation started automatically
    console.log('Generation pipeline started:', data.generation_started);
    // Start polling for progress messages
    startProgressPolling();
    break;
  }
}
```

---

### 3. Start Generation Pipeline (OPTIONAL - Auto-triggered)
**Endpoint:** `POST /api/labs/{lab_id}/generate`

**Note:** This endpoint is **optional** and primarily for manual/testing purposes. Generation automatically starts when the Planner completes (done=true in /chat response).

**Request Body:** (Empty)

**Response:**
```json
{
  "message": "Generation started",
  "lab_id": "lab_1762718464"
}
```

**Prerequisites:**
- Planner must have completed (exercise_spec exists in session)
- Lab status must be `planner_complete`, `completed`, or `failed`

**Errors:**
- `400` - exercise_spec missing (Planner hasn't completed)
- `404` - Lab not found
- `409` - Generation already in progress

**Use Cases:**
- Manual testing/debugging
- Re-running generation after failure
- Advanced workflows where you want to delay generation

**Normal Flow:** Frontend does NOT need to call this - generation auto-starts from /chat endpoint.

---

### 4. Get Lab Status (Modified)
**Endpoint:** `GET /api/labs/{lab_id}/status`

**Response:**
```json
{
  "lab_id": "lab_1762718464",
  "status": "designer_running",
  "current_agent": "designer",
  "created_at": "2025-11-09T10:00:00",
  "updated_at": "2025-11-09T10:05:30",
  "prompt": "Create a lab about...",
  "dry_run": false,
  "latest_planner_update": {
    "timestamp": "2025-11-09T10:05:30",
    "message": "I'm now designing your network topology..."
  },
  "progress": {
    "exercise_spec": {...},
    "design_output": {...},
    "draft_lab_guide": {...},
    "validation_result": {...}
  },
  "conversation": {
    "messages": [...]
  }
}
```

**New Field: `latest_planner_update`**
- Contains the most recent progress message
- Injected by `run_generation_pipeline()` as canned messages
- Messages appear as if Planner said them
- Frontend should poll this field and display new messages in chat

**Usage:**
```javascript
let lastSeenTimestamp = null;

const pollInterval = setInterval(async () => {
  const response = await fetch(`/api/labs/${labId}/status`);
  const data = await response.json();

  if (data.latest_planner_update &&
      data.latest_planner_update.timestamp > lastSeenTimestamp) {
    // New progress message!
    displayMessage({
      role: 'assistant',
      content: data.latest_planner_update.message,
      timestamp: data.latest_planner_update.timestamp
    });
    lastSeenTimestamp = data.latest_planner_update.timestamp;
  }

  if (data.status === 'completed' || data.status === 'failed') {
    clearInterval(pollInterval);
  }
}, 2000);
```

---

## Status Values

### Lab Status Progression

**Phase 1: Planner Interaction**
- `planner_running` - Lab created, waiting for Planner chat
- `planner_complete` - Planner finished, exercise_spec ready

**Phase 2: Generation Pipeline**
- `generation_starting` - /generate endpoint called
- `designer_running` - NetworkDesigner agent executing
- `author_running` - LabGuideAuthor agent executing
- `author_complete` - Author finished
- `validator_running` - Validator agent executing (if not dry_run)
- `validator_complete` - Validator finished

**Phase 3: Final**
- `completed` - Pipeline complete, lab ready
- `failed` - Error occurred during generation

### Current Agent Values

- `null` - No agent running
- `"planner"` - Planner agent (during chat)
- `"designer"` - NetworkDesigner agent
- `"author"` - LabGuideAuthor agent
- `"validator"` - Validator agent

---

## Progress Messages

Progress messages are **canned strings** injected into the Planner conversation using ADK's `append_event()` API.

### Message Timeline

1. **After /generate called:**
   ```
   "Perfect! I have everything I need. Let me start creating your lab..."
   ```

2. **Designer starts:**
   ```
   "I'm now designing your network topology and initial configurations..."
   ```

3. **Designer completes:**
   ```
   "Network design complete! Now writing your lab guide..."
   ```

4. **Author completes:**
   ```
   "Lab guide ready! Running automated validation to verify everything works..."
   ```

5. **Validation passes:**
   ```
   "Excellent! Your lab passed validation and is ready to use 🎉"
   ```

6. **Validation fails:**
   ```
   "Validation found some issues. Your lab is complete but may need manual review."
   ```

7. **Dry-run mode:**
   ```
   "Your lab is ready! (Validation skipped in dry-run mode)"
   ```

8. **Error occurred:**
   ```
   "I encountered an error while generating your lab: {error_message}"
   ```

### Technical Implementation

**Backend (api_server.py):**
```python
async def send_progress_update(message: str):
    """Inject canned message into Planner conversation."""
    session = await _session_service.get_session(
        app_name="adk_agents",
        user_id="api",
        session_id=lab_id
    )

    # Create assistant message from Planner
    canned_content = Content(
        parts=[Part(text=message)],
        role="model"  # "model" = assistant
    )

    canned_event = Event(
        content=canned_content,
        author="PedagogyPlanner"  # Planner's agent name
    )

    # Inject into ADK conversation history
    await _session_service.append_event(session, canned_event)

    # Also store for frontend polling
    labs[lab_id]["latest_planner_update"] = {
        "timestamp": datetime.utcnow().isoformat(),
        "message": message
    }
```

**Key Points:**
- Messages injected into ADK's `session.events` (conversation history)
- When Planner LLM is invoked later, it sees these messages as context
- Messages also stored in `latest_planner_update` for immediate frontend access
- No LLM calls made for progress updates (instant & free)

---

## Session State Management

### ADK Session Structure

**session.events** (Conversation history):
```python
[
  Event(content=Content(parts=[Part(text="Create a lab about...")], role="user"), author="user"),
  Event(content=Content(parts=[Part(text="What skill level?")], role="model"), author="PedagogyPlanner"),
  Event(content=Content(parts=[Part(text="Beginner")], role="user"), author="user"),
  # Canned progress messages injected here:
  Event(content=Content(parts=[Part(text="I'm now designing...")], role="model"), author="PedagogyPlanner"),
  Event(content=Content(parts=[Part(text="Network design complete...")], role="model"), author="PedagogyPlanner"),
]
```

**session.state** (Agent outputs):
```python
{
  "exercise_spec": {...},       # Written by Planner
  "design_output": {...},        # Written by Designer
  "draft_lab_guide": {...},      # Written by Author
  "validation_result_json": "..." # Written by Validator (as JSON string)
}
```

### Shared Session
- Both Planner chat and generation pipeline use **same session** (session_id = lab_id)
- Planner writes `exercise_spec` to `session.state`
- Pipeline reads `exercise_spec` and writes other outputs
- Progress messages injected into `session.events`

---

## Frontend Implementation Guide

### Complete Flow

```javascript
// 1. Create lab
const createResponse = await fetch('/api/labs/create', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    prompt: initialPrompt,
    dry_run: false,
    enable_rca: true
  })
});
const {lab_id} = await createResponse.json();

// 2. Interactive Planner conversation
let plannerDone = false;
while (!plannerDone) {
  const userMessage = await getUserInput();

  const chatResponse = await fetch(`/api/labs/${lab_id}/chat`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: userMessage})
  });

  const chatData = await chatResponse.json();
  displayMessage(chatData.response);

  if (chatData.done) {
    plannerDone = true;
    console.log('Exercise spec ready:', chatData.exercise_spec);
    console.log('Generation started automatically:', chatData.generation_started);
    // Generation pipeline already started in background!
  }
}

// 3. Poll for progress updates (generation already started)
let lastTimestamp = null;
const pollInterval = setInterval(async () => {
  const statusResponse = await fetch(`/api/labs/${lab_id}/status`);
  const status = await statusResponse.json();

  // Check for new progress message
  if (status.latest_planner_update &&
      status.latest_planner_update.timestamp > lastTimestamp) {
    displayMessage({
      role: 'assistant',
      content: status.latest_planner_update.message
    });
    lastTimestamp = status.latest_planner_update.timestamp;
  }

  // Check completion
  if (status.status === 'completed') {
    clearInterval(pollInterval);
    console.log('Lab complete!', status.progress);
  } else if (status.status === 'failed') {
    clearInterval(pollInterval);
    console.error('Lab generation failed:', status.error);
  }
}, 2000);
```

### Error Handling

**Planner Chat Errors:**
```javascript
try {
  const response = await fetch(`/api/labs/${lab_id}/chat`, {...});
  if (!response.ok) {
    if (response.status === 404) {
      // Lab not found
    } else if (response.status === 400) {
      // Message empty
    }
  }
} catch (error) {
  // Network error
}
```

**Generation Trigger Errors:**
```javascript
const response = await fetch(`/api/labs/${lab_id}/generate`, {method: 'POST'});
if (!response.ok) {
  if (response.status === 400) {
    // exercise_spec missing (Planner not done)
  } else if (response.status === 409) {
    // Already generating
  }
}
```

---

## Backward Compatibility

**Old /api/labs/create endpoint still exists** but is now deprecated for the new flow.

If you want to use the old single-endpoint approach (for testing/migration):
- The old `run_pipeline()` function still exists
- It manually runs Planner → Designer → Author → Validator
- But it does NOT support the new progress message system

**Recommendation:** Migrate to new architecture for better UX.

---

## Testing the New Architecture

### Manual Test (cURL)

```bash
# 1. Create lab
curl -X POST http://localhost:8081/api/labs/create \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a beginner lab about Cisco router passwords, 20 minutes", "dry_run": false}'

# Response: {"lab_id": "lab_123", "message": "Lab created successfully"}

# 2. Chat with Planner
curl -X POST http://localhost:8081/api/labs/lab_123/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a beginner lab about Cisco router passwords, 20 minutes"}'

# Response: {"done": false, "response": "What specific password features..."}

# Continue chatting until done=true
# When done=true, generation starts automatically (no need to call /generate)

# 3. Poll for progress (generation already started)
curl http://localhost:8081/api/labs/lab_123/status

# Response includes latest_planner_update field
```

---

## Key Differences from Old Architecture

| Aspect | Old Architecture | New Architecture |
|--------|------------------|------------------|
| **Planner interaction** | Background loop in run_pipeline | Dedicated /chat endpoint |
| **Pipeline trigger** | Automatic after create | Automatic when Planner completes |
| **Progress updates** | Status polling only | Canned messages in Planner chat |
| **Agent execution** | Manual Runner for each agent | Single SequentialAgent pipeline |
| **Conversation history** | Stored in labs[lab_id]["conversation"] | ADK session.events |
| **RCA support** | Not implemented | Ready for Stage 2 |

---

## Future: Stage 2 (RCA Support)

Once Stage 1 is tested, we'll add:
- `create_generation_pipeline(include_rca=True)`
- New status values: `rca_analyzing`, `designer_retrying`, `author_retrying`, `validator_retrying`
- New field: `retry_count`, `max_retries`
- Additional progress messages for RCA analysis and retries

This will enable automatic retry on validation failures with targeted fixes.
