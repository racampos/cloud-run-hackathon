# ADK Interactive Planner - Deep Research Style Q&A

## Overview

The Pedagogy Planner agent must engage in **multi-turn Q&A** with the instructor (similar to ChatGPT Deep Research) to refine vague initial prompts into a complete `ExerciseSpec`.

**User Experience:**
```
Instructor: "I want to design an exercise to teach static routing"

Agent: "I'll help you design a static routing lab. Let me ask a few questions:

1. How many routers would you like in the topology? (2-4 recommended for beginners)
2. Would you like to teach floating static routes?
3. Should we include default static routes (0.0.0.0/0)?
4. What difficulty level? (Beginner / Intermediate / Advanced)
5. Estimated completion time? (30 min / 45 min / 60 min)

Please answer these questions so I can create the perfect lab for you."

Instructor: "Let's use 3 routers, include floating routes, intermediate level, 45 minutes"

Agent: "Perfect! I'll create an intermediate static routing lab with:
- 3 Cisco routers (R1, R2, R3)
- Floating static routes for redundancy
- Default route configuration
- 45 minute completion time

Proceeding to design phase..."
```

---

## ADK Implementation Strategy

### Option 1: Single LlmAgent with Conversation History (Recommended)

Use ADK's **session management** to track conversation state. The Planner agent asks questions, waits for user response, then continues.

```python
# orchestrator/adk_agents/planner.py
from google.adk.agents import LlmAgent
from pydantic import BaseModel

class ExerciseSpec(BaseModel):
    title: str
    objectives: list[str]
    devices: list[dict]
    lab_type: str
    level: str
    estimated_time_minutes: int
    include_floating_routes: bool = False
    include_default_route: bool = False
    # ... other fields

planner_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="PedagogyPlanner",
    description="Interactive planner that clarifies instructor requirements through Q&A",
    instruction="""
You are an expert networking instructor helping design lab exercises.

CONVERSATION FLOW:
1. When the user provides an initial prompt (e.g., "teach static routing"), analyze what's missing
2. Ask 3-5 targeted clarifying questions to gather:
   - Number of devices (routers/switches)
   - Specific topics to cover (e.g., floating routes, default routes, route summarization)
   - Difficulty level (beginner/intermediate/advanced)
   - Estimated completion time
   - Any constraints (e.g., "no more than 3 routers", "must include verification steps")

3. Wait for the user's answers
4. If answers are incomplete, ask follow-up questions
5. Once you have enough information, generate a complete ExerciseSpec JSON

QUESTION EXAMPLES BY LAB TYPE:

Static Routing:
- How many routers? (2-4 recommended)
- Include floating static routes for redundancy?
- Include default route (0.0.0.0/0)?
- Should students configure recursive vs directly connected routes?

OSPF:
- How many routers? How many areas?
- Single-area or multi-area OSPF?
- Include route summarization?
- Teach DR/BDR election?

VLANs:
- How many switches? How many VLANs?
- Include inter-VLAN routing (router-on-a-stick or L3 switch)?
- Teach VLAN Trunking Protocol (VTP)?

IMPORTANT:
- Keep questions concise (5 max per turn)
- Use friendly, professional tone
- If user provides all info upfront, skip questions
- Once you have enough info, output ONLY the ExerciseSpec JSON with no additional text

OUTPUT FORMAT (when ready):
Return a JSON object matching the ExerciseSpec schema. Do NOT include markdown code fences, just raw JSON.
""",
    output_key="exercise_spec",
    output_schema=ExerciseSpec,
)
```

### How the Multi-Turn Works

ADK's **Runner** and **Session** handle conversation history automatically:

```python
# orchestrator/main_adk.py
from google.adk.runner import Runner
from google.adk.session import InMemorySessionService

def interactive_planner_cli():
    """CLI for multi-turn Q&A with Planner"""

    session_service = InMemorySessionService()
    runner = Runner(
        agent=planner_agent,
        app_name="netgenius",
        session_service=session_service
    )

    user_id = "instructor"
    session_id = f"planning_{int(time.time())}"

    print("NetGenius Interactive Lab Planner")
    print("=" * 50)

    # Turn 1: Initial prompt
    initial_prompt = input("\nWhat lab would you like to create? ")

    events = runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=initial_prompt
    )

    # Print agent's response (questions)
    for event in events:
        if event.type == "agent_message":
            print(f"\n{event.content}\n")

    # Check if ExerciseSpec is ready
    session = session_service.get_session(user_id, session_id)

    # Multi-turn loop
    while "exercise_spec" not in session.state:
        # Get user's answers
        user_response = input("\nYour answers: ")

        # Continue conversation (session preserves history)
        events = runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=user_response
        )

        # Print agent's response
        for event in events:
            if event.type == "agent_message":
                print(f"\n{event.content}\n")

        # Check if done
        session = session_service.get_session(user_id, session_id)

        if "exercise_spec" in session.state:
            print("\n✓ Exercise specification complete!")
            print(json.dumps(session.state["exercise_spec"], indent=2))
            break

    return session.state["exercise_spec"]
```

**Key ADK Features Used:**
- **Session Persistence**: `runner.run()` with same `session_id` preserves conversation
- **State Management**: Agent writes to `session.state["exercise_spec"]` when ready
- **Automatic History**: ADK passes full conversation to LLM on each turn

---

### Option 2: Structured Form-Filling with Custom Tool

Create a custom tool that the LLM can call to ask questions:

```python
from google.adk.tools import Tool

class QuestionTool(Tool):
    """Tool for agent to ask clarifying questions"""

    def __init__(self):
        super().__init__(
            name="ask_questions",
            description="Ask the instructor clarifying questions about the lab requirements"
        )

    async def run_async(self, questions: list[str]) -> dict:
        """
        Ask questions and wait for user input

        Args:
            questions: List of questions to ask

        Returns:
            Dictionary of question -> answer
        """
        print("\nPlease answer the following questions:")
        answers = {}
        for i, q in enumerate(questions, 1):
            print(f"{i}. {q}")
            answer = input("   Answer: ")
            answers[q] = answer

        return answers

question_tool = QuestionTool()

planner_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="PedagogyPlanner",
    instruction="""
When the user provides an initial prompt about creating a lab:
1. Use ask_questions tool to gather missing information
2. Analyze the answers
3. If more clarification needed, ask_questions again
4. Once you have enough info, generate ExerciseSpec JSON
""",
    tools=[question_tool],
    output_key="exercise_spec",
    output_schema=ExerciseSpec
)
```

**Pros:** More structured, agent explicitly controls question flow
**Cons:** Requires custom tool implementation, less conversational

---

### Option 3: LoopAgent for Iterative Refinement

Use a `LoopAgent` that repeats until the spec is complete:

```python
from google.adk.agents import LoopAgent, LlmAgent

# Question asker
question_agent = LlmAgent(
    name="QuestionAsker",
    instruction="Ask 3-5 clarifying questions based on the current spec",
    output_key="temp:questions"
)

# Spec builder
spec_builder = LlmAgent(
    name="SpecBuilder",
    instruction="Build ExerciseSpec from user answers. Set 'complete' flag when done.",
    output_key="exercise_spec"
)

# Loop until complete
planner_loop = LoopAgent(
    name="PlannerLoop",
    sub_agents=[question_agent, spec_builder],
    max_iterations=5,
    description="Iteratively refine exercise spec through Q&A"
)
```

**Pros:** Explicit iteration logic
**Cons:** More complex, requires careful state management

---

## Recommended Approach: **Option 1 (Single LlmAgent with Session)**

This is the cleanest and most ADK-idiomatic approach:

✅ **Natural conversation flow** - LLM handles when to ask vs when to output
✅ **Automatic history** - ADK session manages conversation context
✅ **Simple implementation** - Just one agent, no custom tools needed
✅ **Gemini excels at this** - Modern LLMs are great at conversational Q&A

---

## Integration with Full Pipeline

Once the Planner agent has the complete `ExerciseSpec`, it should set a flag or output schema that signals "ready to proceed":

```python
class PlanningStatus(BaseModel):
    status: str  # "gathering_info" | "complete"
    exercise_spec: Optional[ExerciseSpec]
    questions: Optional[list[str]]

planner_agent = LlmAgent(
    name="PedagogyPlanner",
    output_key="planning_status",
    output_schema=PlanningStatus,
    instruction="""
Return a PlanningStatus object:
- If you need more info: status="gathering_info", questions=[...]
- If you have enough info: status="complete", exercise_spec={...}
"""
)
```

Then the orchestrator checks the status:

```python
# In main pipeline orchestrator
def run_planning_phase():
    while True:
        events = runner.run(user_id, session_id, new_message=user_input)

        status = session.state["planning_status"]

        if status["status"] == "gathering_info":
            # Print questions, get user input
            print(status["questions"])
            user_input = input("Your answers: ")
            continue

        elif status["status"] == "complete":
            # Proceed to Designer
            exercise_spec = status["exercise_spec"]
            break
```

---

## Web UI Integration (ADK Web)

ADK provides a built-in web UI that supports multi-turn conversations out of the box:

```bash
# Start ADK web UI
adk web --port 8000
```

Navigate to `http://localhost:8000` and you get a **ChatGPT-like interface** automatically!

The web UI:
- Handles conversation history
- Displays agent responses
- Accepts user input
- Shows when agents are "thinking"
- Perfect for demoing the interactive planner

---

## Example Conversation Flow (Full)

```
Turn 1:
User: "I want to design an exercise to teach static routing"

Agent: "Great! I'll help you design a static routing lab. Let me ask a few clarifying questions:

1. How many routers would you like in the topology? (2-4 recommended for beginners)
2. Would you like to teach floating static routes for redundancy?
3. Should we include default static routes (0.0.0.0/0)?
4. What difficulty level are you targeting? (Beginner/Intermediate/Advanced)
5. Estimated completion time? (30/45/60 minutes)

Please provide your answers."

---

Turn 2:
User: "Let's use 3 routers, include floating routes, intermediate level, 45 minutes"

Agent: "Perfect! Just one more question:

6. Should the lab include verification steps like traceroute and ping to test connectivity?

And should we demonstrate the concept of administrative distance with the floating routes?"

---

Turn 3:
User: "Yes to both"

Agent: {
  "title": "Intermediate Static Routing with Redundancy",
  "objectives": [
    "Configure basic static routes between three routers",
    "Implement floating static routes for path redundancy",
    "Configure default static routes",
    "Understand administrative distance",
    "Verify connectivity using ping and traceroute"
  ],
  "devices": [
    {"hostname": "R1", "platform": "cisco_2911", "role": "edge"},
    {"hostname": "R2", "platform": "cisco_2911", "role": "core"},
    {"hostname": "R3", "platform": "cisco_2911", "role": "edge"}
  ],
  "lab_type": "static_routing",
  "level": "intermediate",
  "estimated_time_minutes": 45,
  "include_floating_routes": true,
  "include_default_route": true,
  "verification_commands": ["ping", "traceroute", "show ip route"]
}

Proceeding to design phase...
```

---

## Implementation Checklist

### Planner Agent Setup:
- [ ] Define `ExerciseSpec` Pydantic model with all fields
- [ ] Create `PlanningStatus` wrapper for conversation state
- [ ] Write detailed `instruction` with question examples per lab type
- [ ] Set `output_schema=ExerciseSpec` for structured output
- [ ] Test with `adk web` for interactive debugging

### CLI Integration:
- [ ] Create `interactive_planner_cli()` function
- [ ] Implement conversation loop checking `session.state`
- [ ] Add pretty printing for questions/answers
- [ ] Save final `ExerciseSpec` to file for inspection

### Pipeline Integration:
- [ ] Create conditional logic: if `status == "complete"`, proceed to Designer
- [ ] Pass `exercise_spec` from Planner to Designer via session state
- [ ] Handle user interruption (save partial state)

### Testing:
- [ ] Test with minimal prompt: "teach OSPF"
- [ ] Test with detailed prompt: "3 router OSPF lab, multi-area, 60 min, advanced"
- [ ] Test edge case: user provides conflicting requirements
- [ ] Test abort: user wants to start over mid-conversation

---

## ADK Session State Example

After planning phase completes:

```python
session.state = {
    "planning_status": {
        "status": "complete",
        "exercise_spec": {
            "title": "Intermediate Static Routing with Redundancy",
            "objectives": [...],
            "devices": [...],
            "lab_type": "static_routing",
            # ... full spec
        },
        "questions": None  # No more questions needed
    },

    # Conversation history automatically managed by ADK
    "conversation_history": [
        {"role": "user", "content": "I want to teach static routing"},
        {"role": "assistant", "content": "Great! Let me ask..."},
        {"role": "user", "content": "3 routers, floating routes..."},
        {"role": "assistant", "content": "{...JSON...}"}
    ]
}
```

---

## Benefits of This Approach

✅ **Better UX**: Instructors provide minimal input, agent asks smart questions
✅ **Higher Quality**: Complete specs lead to better designs
✅ **Flexibility**: Handles both vague ("teach VLANs") and detailed prompts
✅ **ADK-Native**: Uses session management, conversation history, structured output
✅ **Demo-Friendly**: Web UI makes this impressive in hackathon presentation

---

## Next Steps

1. **Set up Gemini API key** in `.env`
2. **Implement Planner agent** with conversation logic
3. **Test with `adk web`** for interactive debugging
4. **Integrate into main pipeline** with conditional flow
5. **Create demo script** showing vague → refined → complete spec

This Deep Research-style interaction will be a **killer feature** for the hackathon demo! 🚀
