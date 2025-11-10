"""NetGenius REST API Server

FastAPI wrapper around the ADK lab creation pipeline.
Provides HTTP endpoints for the Next.js frontend.

Based on BACKEND_REQUIREMENTS_V2.md (APPROVED)
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from collections import deque
import time
import asyncio
import re
import json
import os
import sys
from dotenv import load_dotenv


# ========== UTILITY FUNCTIONS ==========

def utc_now() -> str:
    """Get current UTC timestamp in ISO format with explicit 'Z' suffix.

    Returns timestamps like: 2025-11-10T00:40:00.123456Z
    The 'Z' suffix explicitly indicates this is a UTC timestamp.
    """
    return datetime.utcnow().isoformat() + 'Z'


def extract_json_from_markdown(text: str) -> dict | None:
    """Extract JSON from markdown code block or raw JSON string.

    Handles formats like:
    - ```json {...} ```
    - ``` {...} ```
    - {...}

    Returns parsed dict or None if parsing fails.
    """
    if not text:
        return None

    if isinstance(text, dict):
        # Already parsed
        return text

    # Try to extract from markdown code block
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try parsing as raw JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    return None

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Initialize FastAPI app
app = FastAPI(
    title="NetGenius API",
    version="2.0.0",
    description="REST API for interactive lab generation with multi-turn Planner conversation"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local dev
        "https://netgenius-frontend-*.run.app",  # Production
        "https://*.run.app"  # Wildcard for Cloud Run
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (MVP)
labs: Dict[str, dict] = {}

# Global session service instance (shared across all requests)
_session_service = None

# ========== REQUEST/RESPONSE MODELS ==========

class CreateLabRequest(BaseModel):
    prompt: str = Field(..., min_length=10, description="Initial instructor prompt")
    dry_run: bool = Field(default=False, description="Skip headless validation")
    enable_rca: bool = Field(default=True, description="Enable RCA retry loop")


class CreateLabResponse(BaseModel):
    lab_id: str
    status: str


class UserMessage(BaseModel):
    content: str = Field(..., min_length=1, description="User's message content")


class MessageResponse(BaseModel):
    status: str
    conversation_status: str


# ========== ENDPOINTS ==========

@app.post("/api/labs/create", response_model=CreateLabResponse)
async def create_lab(request: CreateLabRequest, background_tasks: BackgroundTasks):
    """Create a new lab and start interactive Planner conversation."""

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
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "prompt": request.prompt,
        "pending_messages": deque(),
        "progress_messages": [],  # List of {"timestamp": ..., "message": ...} for canned updates
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
    """Send a message to continue the Planner conversation."""

    if lab_id not in labs:
        raise HTTPException(status_code=404, detail="Lab not found")

    if labs[lab_id]["status"] not in ["awaiting_user_input", "planner_running"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot send message when status is {labs[lab_id]['status']}"
        )

    # Add message to queue (background task is waiting for this)
    labs[lab_id]["pending_messages"].append(message.content)
    labs[lab_id]["updated_at"] = utc_now()

    return {
        "status": "message_received",
        "conversation_status": labs[lab_id]["status"]
    }


@app.get("/api/labs/{lab_id}/status")
async def get_lab_status(lab_id: str):
    """Get current lab status and conversation state."""

    if lab_id not in labs:
        raise HTTPException(status_code=404, detail="Lab not found")

    lab = labs[lab_id]
    global _session_service

    # Fetch conversation history from ADK session.events (NEW architecture)
    conversation_messages = []
    try:
        if _session_service is not None:
            session = await _session_service.get_session(
                app_name="adk_agents",
                user_id="api",
                session_id=lab_id
            )

            if session is not None:
                # Convert ADK session.events to conversation messages
                # Note: We generate timestamps based on event order and current time
                # to ensure consistent UTC timestamps across all messages
                base_time = datetime.fromisoformat(lab["created_at"].replace('Z', ''))
                time_offset_seconds = 0

                for idx, event in enumerate(session.events):
                    if event.content and event.content.parts:
                        # Extract text from parts
                        text_content = ""
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                text_content += part.text

                        if text_content:
                            # Map ADK roles to chat roles
                            role = "assistant" if event.content.role == "model" else "user"

                            # Filter out internal messages that shouldn't be shown to users
                            # 1. Trigger messages like "start", "generate"
                            # 2. Validation failure messages with execution IDs
                            # 3. Messages wrapped in triple backticks (duplicates of structured data)
                            # 4. Design output (topology_yaml) - already displayed in its own UI section
                            if role == "user" and text_content.strip().lower() in ["start", "generate"]:
                                continue
                            if "Validation FAILED: execution_id=" in text_content:
                                continue
                            if text_content.strip().startswith("```json") or text_content.strip().startswith("```"):
                                # Skip if it's a markdown-wrapped version of structured data
                                # (the actual structured data is already in progress fields)
                                continue
                            if '"topology_yaml"' in text_content or "'topology_yaml'" in text_content:
                                # Skip design_output messages - they're displayed in the topology viewer
                                continue

                            # Generate timestamp: increment by 1 second per message from lab creation time
                            # This preserves chronological order while using UTC timestamps
                            message_time = base_time + timedelta(seconds=time_offset_seconds)
                            time_offset_seconds += 1

                            conversation_messages.append({
                                "role": role,
                                "content": text_content,
                                "timestamp": message_time.isoformat() + 'Z'  # Explicit UTC marker
                            })

                # If validation_result is null, try to fetch from session state
                if (lab["progress"]["validation_result"] is None and
                    lab["status"] in ["completed", "validator_complete"]):
                    validation_result_json = session.state.get("validation_result_json")
                    if validation_result_json:
                        lab["progress"]["validation_result"] = json.loads(validation_result_json)
    except Exception as e:
        print(f"[DEBUG] Exception fetching session data: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    # Merge progress messages from local storage into conversation
    # These are canned messages sent during generation and are immediately visible
    if "progress_messages" in lab and lab["progress_messages"]:
        for progress_msg in lab["progress_messages"]:
            conversation_messages.append({
                "role": "assistant",
                "content": progress_msg["message"],
                "timestamp": progress_msg["timestamp"]
            })

    # Sort all messages by timestamp to maintain chronological order
    conversation_messages.sort(key=lambda msg: msg["timestamp"])

    # Fix ordering: Find the "Perfect!" message and the exercise_spec, swap if needed
    # The "Perfect!" message should come BEFORE the exercise_spec
    perfect_idx = None
    spec_idx = None

    for idx, msg in enumerate(conversation_messages):
        if msg["role"] == "assistant":
            if "Perfect! I have everything I need" in msg["content"]:
                perfect_idx = idx
            elif msg["content"].strip().startswith("{") and '"title"' in msg["content"] and '"objectives"' in msg["content"]:
                spec_idx = idx

    # If both found and spec comes before perfect, we need to reorder
    if perfect_idx is not None and spec_idx is not None and spec_idx < perfect_idx:
        # Adjust timestamps so perfect comes right before spec
        spec_msg = conversation_messages[spec_idx]
        perfect_msg = conversation_messages[perfect_idx]

        # Give perfect message a timestamp 1 second before spec
        spec_time = datetime.fromisoformat(spec_msg["timestamp"].replace('Z', ''))
        new_perfect_time = spec_time - timedelta(seconds=1)
        perfect_msg["timestamp"] = new_perfect_time.isoformat() + 'Z'

        # Re-sort with updated timestamps
        conversation_messages.sort(key=lambda msg: msg["timestamp"])

    # Build response
    response = {k: v for k, v in lab.items() if k not in ["pending_messages", "progress_messages"]}

    # Replace conversation with ADK-based messages if available, otherwise use existing
    if conversation_messages:
        response["conversation"] = {
            "messages": conversation_messages,
            "awaiting_user_input": lab.get("conversation", {}).get("awaiting_user_input", False)
        }

    return response


@app.get("/api/labs/{lab_id}")
async def get_lab(lab_id: str):
    """Get full lab details (same as status for MVP)."""

    if lab_id not in labs:
        raise HTTPException(status_code=404, detail="Lab not found")

    return {
        k: v for k, v in labs[lab_id].items()
        if k != "pending_messages"
    }


@app.get("/api/labs")
async def list_labs():
    """List all created labs."""

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


@app.post("/api/labs/{lab_id}/chat")
async def chat_with_planner(lab_id: str, request: dict, background_tasks: BackgroundTasks):
    """Interactive chat with Planner agent.

    The Planner agent runs independently to gather requirements through Q&A.
    When exercise_spec is ready, this endpoint automatically triggers the generation
    pipeline in the background.

    Args:
        lab_id: Lab identifier (also used as session_id)
        request: {"message": "user's message"}

    Returns:
        {
            "done": bool,  # True if exercise_spec is ready and generation started
            "response": str,  # Planner's response (question or completion message)
            "exercise_spec": dict,  # Only present if done=True
            "generation_started": bool  # Only present if done=True
        }
    """
    if lab_id not in labs:
        raise HTTPException(status_code=404, detail="Lab not found")

    message = request.get("message", "")
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Import ADK components
    from adk_agents.planner import planner_agent
    from google.adk import Runner
    from google.genai import types

    # Create Planner runner (uses global session service)
    global _session_service
    planner_runner = Runner(
        agent=planner_agent,
        app_name="adk_agents",
        session_service=_session_service
    )

    # Send user message to Planner
    user_message = types.Content(
        parts=[types.Part(text=message)],
        role="user"
    )

    events = list(planner_runner.run(
        user_id="api",
        session_id=lab_id,
        new_message=user_message
    ))

    # Get Planner's response
    planner_response = ""
    if events and events[-1].content:
        planner_response = str(events[-1].content)

    # Check if exercise_spec is ready
    session = await _session_service.get_session(
        app_name="adk_agents",
        user_id="api",
        session_id=lab_id
    )

    exercise_spec = session.state.get("exercise_spec")

    if exercise_spec:
        # Planner is done! Store exercise_spec in labs dict
        labs[lab_id]["progress"]["exercise_spec"] = exercise_spec
        labs[lab_id]["status"] = "planner_complete"
        labs[lab_id]["updated_at"] = utc_now()

        # Auto-trigger generation pipeline in background
        dry_run = labs[lab_id].get("dry_run", False)
        background_tasks.add_task(run_generation_pipeline, lab_id, dry_run)

        return {
            "done": True,
            "response": planner_response,
            "exercise_spec": exercise_spec,
            "generation_started": True
        }
    else:
        # Planner needs more information
        return {
            "done": False,
            "response": planner_response
        }


@app.post("/api/labs/{lab_id}/generate")
async def start_generation(lab_id: str, background_tasks: BackgroundTasks):
    """Start the generation pipeline after Planner completes.

    This endpoint triggers Designer → Author → Validator pipeline.
    Requires that exercise_spec exists in session.state.

    Args:
        lab_id: Lab identifier

    Returns:
        {"message": "Generation started", "lab_id": str}
    """
    if lab_id not in labs:
        raise HTTPException(status_code=404, detail="Lab not found")

    # Verify exercise_spec exists
    global _session_service
    session = await _session_service.get_session(
        app_name="adk_agents",
        user_id="api",
        session_id=lab_id
    )

    if "exercise_spec" not in session.state:
        raise HTTPException(
            status_code=400,
            detail="Cannot start generation: Planner hasn't completed yet (exercise_spec missing)"
        )

    # Check if already generating
    if labs[lab_id]["status"] not in ["planner_complete", "completed", "failed"]:
        raise HTTPException(
            status_code=409,
            detail=f"Generation already in progress (status: {labs[lab_id]['status']})"
        )

    # Start generation pipeline in background
    dry_run = labs[lab_id].get("dry_run", False)
    background_tasks.add_task(run_generation_pipeline, lab_id, dry_run)

    labs[lab_id]["status"] = "generation_starting"
    labs[lab_id]["updated_at"] = utc_now()

    return {"message": "Generation started", "lab_id": lab_id}


# ========== BACKGROUND TASK ==========

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
        # ========== PHASE 1: INTERACTIVE PLANNER CONVERSATION ==========

        labs[lab_id]["status"] = "planner_running"
        labs[lab_id]["current_agent"] = "planner"
        labs[lab_id]["updated_at"] = utc_now()

        # Import ADK components
        from adk_agents.planner import planner_agent
        from google.adk import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types

        # Initialize global session service if not already created
        global _session_service
        if _session_service is None:
            _session_service = InMemorySessionService()

        session_id = lab_id

        await _session_service.create_session(
            app_name="adk_agents",
            user_id="api",
            session_id=session_id
        )

        # Create Planner runner
        planner_runner = Runner(
            agent=planner_agent,
            app_name="adk_agents",
            session_service=_session_service
        )

        # Add initial prompt to conversation
        labs[lab_id]["conversation"]["messages"].append({
            "role": "user",
            "content": initial_prompt,
            "timestamp": utc_now()
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

                # Debug: Log all events
                print(f"[DEBUG] Planner turn {turn_count}: Got {len(events)} events")
                for i, event in enumerate(events):
                    print(f"[DEBUG] Event {i}: type={type(event).__name__}, has_content={hasattr(event, 'content')}")
                    if hasattr(event, 'content') and event.content:
                        print(f"[DEBUG]   content type={type(event.content).__name__}")
                        print(f"[DEBUG]   content={str(event.content)[:200]}")

                # Extract agent's response from events
                agent_response = ""
                for event in events:
                    if hasattr(event, 'content') and event.content:
                        if hasattr(event.content, 'parts'):
                            for part in event.content.parts:
                                if hasattr(part, 'text'):
                                    agent_response += part.text

                # Debug: Log what we got from planner
                print(f"[DEBUG] Planner turn {turn_count}: agent_response length = {len(agent_response)}")
                print(f"[DEBUG] First 200 chars: {agent_response[:200]}")

                # Add agent response to conversation
                if agent_response:
                    labs[lab_id]["conversation"]["messages"].append({
                        "role": "assistant",
                        "content": agent_response,
                        "timestamp": utc_now()
                    })
                    labs[lab_id]["updated_at"] = utc_now()
                else:
                    print(f"[DEBUG] WARNING: No agent response on turn {turn_count}!")

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
                            labs[lab_id]["updated_at"] = utc_now()
                            break
                    except json.JSONDecodeError:
                        pass

                # No complete spec yet - Planner is asking questions
                # Wait for user's response
                labs[lab_id]["status"] = "awaiting_user_input"
                labs[lab_id]["conversation"]["awaiting_user_input"] = True
                labs[lab_id]["updated_at"] = utc_now()

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
                    "timestamp": utc_now()
                })

                labs[lab_id]["status"] = "planner_running"
                labs[lab_id]["conversation"]["awaiting_user_input"] = False
                labs[lab_id]["updated_at"] = utc_now()

                # Create message for next turn
                message = types.Content(
                    parts=[types.Part(text=user_answer)],
                    role="user"
                )

        if exercise_spec is None:
            raise Exception("Planner failed to produce ExerciseSpec after max turns")

        # ========== PHASE 2: AUTOMATED PIPELINE ==========

        # Helper to send progress updates
        def send_progress_update(message: str):
            """Send a canned progress message to the conversation."""
            timestamp = utc_now()
            print(f"[DEBUG] send_progress_update (run_pipeline) for lab {lab_id}: {message}")
            labs[lab_id]["progress_messages"].append({
                "timestamp": timestamp,
                "message": message
            })
            labs[lab_id]["latest_planner_update"] = {
                "timestamp": timestamp,
                "message": message
            }

        # Send initial generation message
        send_progress_update("Perfect! I have everything I need. Let me start creating your lab...")

        # Import remaining agents
        from adk_agents.designer import designer_agent
        from adk_agents.author import author_agent
        from adk_agents.validator import validator_agent

        # Designer
        send_progress_update("I'm now designing your network topology and initial configurations...")
        labs[lab_id]["status"] = "designer_running"
        labs[lab_id]["current_agent"] = "designer"
        labs[lab_id]["updated_at"] = utc_now()
        await asyncio.sleep(2.0)  # Allow frontend to poll and see status and see status

        designer_runner = Runner(
            agent=designer_agent,
            app_name="adk_agents",
            session_service=_session_service
        )

        # Create trigger message for Designer
        designer_message = types.Content(
            parts=[types.Part(text="start")],
            role="user"
        )

        events = list(designer_runner.run(
            user_id="api",
            session_id=session_id,
            new_message=designer_message
        ))

        session = await _session_service.get_session(
            app_name="adk_agents",
            user_id="api",
            session_id=session_id
        )

        # Parse design_output from markdown-wrapped JSON to actual dict
        raw_design_output = session.state.get("design_output")
        parsed_design_output = extract_json_from_markdown(raw_design_output)
        labs[lab_id]["progress"]["design_output"] = parsed_design_output

        labs[lab_id]["status"] = "designer_complete"
        labs[lab_id]["updated_at"] = utc_now()
        await asyncio.sleep(2.0)  # Allow frontend to poll and see status and see status

        # Author
        send_progress_update("Network design complete! Now writing your lab guide...")
        labs[lab_id]["status"] = "author_running"
        labs[lab_id]["current_agent"] = "author"
        labs[lab_id]["updated_at"] = utc_now()
        await asyncio.sleep(2.0)  # Allow frontend to poll and see status and see status

        author_runner = Runner(
            agent=author_agent,
            app_name="adk_agents",
            session_service=_session_service
        )

        # Create trigger message for Author
        author_message = types.Content(
            parts=[types.Part(text="start")],
            role="user"
        )

        events = list(author_runner.run(
            user_id="api",
            session_id=session_id,
            new_message=author_message
        ))

        session = await _session_service.get_session(
            app_name="adk_agents",
            user_id="api",
            session_id=session_id
        )

        # Parse draft_lab_guide from markdown-wrapped JSON to actual dict
        raw_draft_lab_guide = session.state.get("draft_lab_guide")
        parsed_draft_lab_guide = extract_json_from_markdown(raw_draft_lab_guide)
        labs[lab_id]["progress"]["draft_lab_guide"] = parsed_draft_lab_guide

        # Read the generated markdown file from output directory
        markdown_path = os.path.join(os.path.dirname(__file__), "output", "draft_lab_guide.md")
        if os.path.exists(markdown_path):
            with open(markdown_path, "r") as f:
                labs[lab_id]["progress"]["draft_lab_guide_markdown"] = f.read()
        else:
            labs[lab_id]["progress"]["draft_lab_guide_markdown"] = None

        labs[lab_id]["status"] = "author_complete"
        labs[lab_id]["updated_at"] = utc_now()
        await asyncio.sleep(2.0)  # Allow frontend to poll and see status and see status

        # Validator (if not dry_run)
        if not dry_run:
            send_progress_update("Lab guide ready! Running automated validation to verify everything works...")
            labs[lab_id]["status"] = "validator_running"
            labs[lab_id]["current_agent"] = "validator"
            labs[lab_id]["updated_at"] = utc_now()
            await asyncio.sleep(2.0)  # Allow frontend to poll and see status and see status

            validator_runner = Runner(
                agent=validator_agent,
                app_name="adk_agents",
                session_service=_session_service
            )

            # Create trigger message for Validator
            validator_message = types.Content(
                parts=[types.Part(text="start")],
                role="user"
            )

            events = list(validator_runner.run(
                user_id="api",
                session_id=session_id,
                new_message=validator_message
            ))

            # Get validation_result directly from validator_agent instance variable
            print(f"[DEBUG API] Retrieving validation result from validator_agent.last_validation_result")
            validation_result = validator_agent.last_validation_result

            if validation_result:
                print(f"[DEBUG API] Found validation_result: execution_id={validation_result.get('execution_id')}, success={validation_result.get('success')}")
                labs[lab_id]["progress"]["validation_result"] = validation_result
            else:
                print(f"[DEBUG API] WARNING: validator_agent.last_validation_result is None!")
                labs[lab_id]["progress"]["validation_result"] = None

            labs[lab_id]["status"] = "validator_complete"
            labs[lab_id]["updated_at"] = utc_now()

            # Send final message based on validation result
            if validation_result and validation_result.get("success"):
                send_progress_update("Excellent! Your lab passed validation and is ready to use 🎉")
            else:
                send_progress_update("Validation found some issues. Your lab is complete but may need manual review.")
        else:
            # Dry-run mode: no validation
            send_progress_update("Your lab is ready! (Validation skipped in dry-run mode)")

        # Final status
        labs[lab_id]["status"] = "completed"
        labs[lab_id]["current_agent"] = None
        labs[lab_id]["updated_at"] = utc_now()

    except asyncio.TimeoutError:
        labs[lab_id]["status"] = "failed"
        labs[lab_id]["error"] = "Pipeline execution timed out"
        labs[lab_id]["current_agent"] = None
        labs[lab_id]["updated_at"] = utc_now()

    except Exception as e:
        labs[lab_id]["status"] = "failed"
        labs[lab_id]["error"] = str(e)
        labs[lab_id]["current_agent"] = None
        labs[lab_id]["updated_at"] = utc_now()


async def run_generation_pipeline(lab_id: str, dry_run: bool):
    """Run the generation pipeline using ADK's SequentialAgent.

    This function:
    1. Sends canned progress messages to Planner's conversation
    2. Runs Designer → Author → Validator using create_generation_pipeline()
    3. Updates lab status as pipeline progresses

    Args:
        lab_id: Lab identifier (also session_id)
        dry_run: If True, skip validation
    """
    try:
        from adk_agents.pipeline import create_generation_pipeline
        from google.adk import Runner

        global _session_service

        # Helper to inject canned message into Planner's conversation
        async def send_progress_update(message: str):
            """Inject a canned progress message as if Planner said it."""
            timestamp = utc_now()

            print(f"[DEBUG] send_progress_update called for lab {lab_id}: {message}")

            # Store in local progress_messages list (immediately visible to /status endpoint)
            labs[lab_id]["progress_messages"].append({
                "timestamp": timestamp,
                "message": message
            })

            print(f"[DEBUG] progress_messages now has {len(labs[lab_id]['progress_messages'])} items")

            # Also update latest_planner_update for compatibility
            labs[lab_id]["latest_planner_update"] = {
                "timestamp": timestamp,
                "message": message
            }

        # Send initial progress message
        await send_progress_update("Perfect! I have everything I need. Let me start creating your lab...")

        # Import agents
        from adk_agents.designer import designer_agent
        from adk_agents.author import author_agent
        from adk_agents.validator import validator_agent
        from google.genai import types

        # ========== DESIGNER ==========
        labs[lab_id]["status"] = "designer_running"
        labs[lab_id]["current_agent"] = "designer"
        labs[lab_id]["updated_at"] = utc_now()
        await send_progress_update("I'm now designing your network topology and initial configurations...")

        designer_runner = Runner(
            agent=designer_agent,
            app_name="adk_agents",
            session_service=_session_service
        )

        designer_message = types.Content(
            parts=[types.Part(text="start")],
            role="user"
        )

        list(designer_runner.run(
            user_id="api",
            session_id=lab_id,
            new_message=designer_message
        ))

        labs[lab_id]["status"] = "designer_complete"
        labs[lab_id]["updated_at"] = utc_now()
        await asyncio.sleep(2.0)  # Allow frontend to poll and see status

        # ========== AUTHOR ==========
        labs[lab_id]["status"] = "author_running"
        labs[lab_id]["current_agent"] = "author"
        labs[lab_id]["updated_at"] = utc_now()
        await send_progress_update("Network design complete! Now writing your lab guide...")
        await asyncio.sleep(1.0)  # Ensure status is visible before agent starts

        author_runner = Runner(
            agent=author_agent,
            app_name="adk_agents",
            session_service=_session_service
        )

        author_message = types.Content(
            parts=[types.Part(text="start")],
            role="user"
        )

        list(author_runner.run(
            user_id="api",
            session_id=lab_id,
            new_message=author_message
        ))

        labs[lab_id]["status"] = "author_complete"
        labs[lab_id]["updated_at"] = utc_now()
        await asyncio.sleep(2.0)  # Allow frontend to poll and see status

        # Get final session state
        session = await _session_service.get_session(
            app_name="adk_agents",
            user_id="api",
            session_id=lab_id
        )

        # Store outputs in labs dict
        if "design_output" in session.state:
            raw_design_output = session.state["design_output"]
            labs[lab_id]["progress"]["design_output"] = extract_json_from_markdown(raw_design_output)

        if "draft_lab_guide" in session.state:
            raw_draft_lab_guide = session.state["draft_lab_guide"]
            labs[lab_id]["progress"]["draft_lab_guide"] = extract_json_from_markdown(raw_draft_lab_guide)

        # Note: Status updates and progress messages are now handled by monitor_and_run_pipeline()
        # to ensure they happen at the right time during pipeline execution

        # Check validation result if not dry_run
        if not dry_run:
            labs[lab_id]["status"] = "validator_running"
            labs[lab_id]["current_agent"] = "validator"
            labs[lab_id]["updated_at"] = utc_now()
            await send_progress_update("Lab guide ready! Running automated validation to verify everything works...")

            # Run validator
            validator_runner = Runner(
                agent=validator_agent,
                app_name="adk_agents",
                session_service=_session_service
            )

            validator_message = types.Content(
                parts=[types.Part(text="start")],
                role="user"
            )

            list(validator_runner.run(
                user_id="api",
                session_id=lab_id,
                new_message=validator_message
            ))

            # Get validation result from validator_agent instance
            validation_result = validator_agent.last_validation_result

            if validation_result:
                labs[lab_id]["progress"]["validation_result"] = validation_result

                if validation_result.get("success"):
                    await send_progress_update("Excellent! Your lab passed validation and is ready to use 🎉")
                else:
                    await send_progress_update("Validation found some issues. Your lab is complete but may need manual review.")
            else:
                labs[lab_id]["progress"]["validation_result"] = None

            labs[lab_id]["status"] = "validator_complete"
            labs[lab_id]["updated_at"] = utc_now()
            await asyncio.sleep(2.0)  # Allow frontend to poll and see status

        # Final status
        labs[lab_id]["status"] = "completed"
        labs[lab_id]["current_agent"] = None
        labs[lab_id]["updated_at"] = utc_now()

        if dry_run:
            await send_progress_update("Your lab is ready! (Validation skipped in dry-run mode)")

    except Exception as e:
        labs[lab_id]["status"] = "failed"
        labs[lab_id]["error"] = str(e)
        labs[lab_id]["current_agent"] = None
        labs[lab_id]["updated_at"] = utc_now()

        # Send failure message to Planner conversation
        try:
            await send_progress_update(f"I encountered an error while generating your lab: {str(e)}")
        except:
            pass  # Don't fail on notification failure


# ========== STARTUP/SHUTDOWN ==========

@app.on_event("startup")
async def startup_event():
    """Run on server startup."""
    # Check for required environment variables
    if not os.getenv("GOOGLE_API_KEY"):
        print("WARNING: GOOGLE_API_KEY not set. API will fail when creating labs.")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "NetGenius API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
        "create_lab": "POST /api/labs/create",
        "send_message": "POST /api/labs/{id}/message",
        "get_status": "GET /api/labs/{id}/status",
        "get_lab": "GET /api/labs/{id}",
        "list_labs": "GET /api/labs"
        }
    }


# ========== MAIN ==========

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8081"))
    uvicorn.run(app, host="0.0.0.0", port=port)
