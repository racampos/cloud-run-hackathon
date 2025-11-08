"""NetGenius REST API Server

FastAPI wrapper around the ADK lab creation pipeline.
Provides HTTP endpoints for the Next.js frontend.

Based on BACKEND_REQUIREMENTS_V2.md (APPROVED)
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from collections import deque
import time
import asyncio
import re
import json
import os
import sys
from dotenv import load_dotenv


# ========== UTILITY FUNCTIONS ==========

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
    labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()

    return {
        "status": "message_received",
        "conversation_status": labs[lab_id]["status"]
    }


@app.get("/api/labs/{lab_id}/status")
async def get_lab_status(lab_id: str):
    """Get current lab status and conversation state."""

    if lab_id not in labs:
        raise HTTPException(status_code=404, detail="Lab not found")

    # Return everything except internal queue
    return {
        k: v for k, v in labs[lab_id].items()
        if k != "pending_messages"
    }


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
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()
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
        await asyncio.sleep(0.5)  # Allow frontend to poll and see status

        designer_runner = Runner(
            agent=designer_agent,
            app_name="adk_agents",
            session_service=session_service
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

        session = await session_service.get_session(
            app_name="adk_agents",
            user_id="api",
            session_id=session_id
        )

        # Parse design_output from markdown-wrapped JSON to actual dict
        raw_design_output = session.state.get("design_output")
        parsed_design_output = extract_json_from_markdown(raw_design_output)
        labs[lab_id]["progress"]["design_output"] = parsed_design_output

        labs[lab_id]["status"] = "designer_complete"
        labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()
        await asyncio.sleep(0.5)  # Allow frontend to poll and see status

        # Author
        labs[lab_id]["status"] = "author_running"
        labs[lab_id]["current_agent"] = "author"
        labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()
        await asyncio.sleep(0.5)  # Allow frontend to poll and see status

        author_runner = Runner(
            agent=author_agent,
            app_name="adk_agents",
            session_service=session_service
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

        session = await session_service.get_session(
            app_name="adk_agents",
            user_id="api",
            session_id=session_id
        )

        # Parse draft_lab_guide from markdown-wrapped JSON to actual dict
        raw_draft_lab_guide = session.state.get("draft_lab_guide")
        parsed_draft_lab_guide = extract_json_from_markdown(raw_draft_lab_guide)
        labs[lab_id]["progress"]["draft_lab_guide"] = parsed_draft_lab_guide

        labs[lab_id]["status"] = "author_complete"
        labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()
        await asyncio.sleep(0.5)  # Allow frontend to poll and see status

        # Validator (if not dry_run)
        if not dry_run:
            labs[lab_id]["status"] = "validator_running"
            labs[lab_id]["current_agent"] = "validator"
            labs[lab_id]["updated_at"] = datetime.utcnow().isoformat()
            await asyncio.sleep(0.5)  # Allow frontend to poll and see status

            validator_runner = Runner(
                agent=validator_agent,
                app_name="adk_agents",
                session_service=session_service
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
