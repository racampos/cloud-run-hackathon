"""Root-Cause Analysis (RCA) Agent - ADK Implementation.

This agent analyzes validation failures and routes patches back to the
appropriate agent (Designer or Author) for targeted fixes.
"""

from google.adk.agents import LlmAgent
from schemas import PatchPlan


def create_rca_agent() -> LlmAgent:
    """Create the RCA agent for validation failure analysis."""

    return LlmAgent(
        model="gemini-2.5-flash",
        name="RCAAgent",
        description="Analyzes validation failures and creates patch plans for targeted fixes",
        instruction="""
You are a Root-Cause Analysis expert for network lab validation failures.

CRITICAL: Parse validation_result from this JSON input:

{validation_result_json?}

STEP 1: Parse the validation_result JSON above
- If empty or missing, return PatchPlan with should_retry=false and analysis="No validation result available"
- If success == true, return PatchPlan with should_retry=false and analysis="Validation passed"

STEP 2: If validation_result.success == false, also read from session state:
- exercise_spec: Learning objectives, title, level, prerequisites
- design_output: Topology YAML, device configs, initial configs, platforms
- draft_lab_guide: Student-facing lab guide with configuration steps

YOUR TASK:
1. Analyze the validation failure (validation_result.success == false)
2. Classify the root cause into one of three categories:
   - **DESIGN**: Topology or configuration issues
     Examples: Wrong IP addresses, missing routes, incorrect interface configs,
               OSPF area mismatches, subnet errors, missing "no shutdown"
   - **INSTRUCTION**: Lab guide issues
     Examples: Wrong commands, incorrect sequence, missing steps,
               typos in commands, wrong interface names
   - **OBJECTIVES**: Specification issues (unrealistic/impossible requirements)
     Examples: Constraints that can't be met, contradictory requirements,
               time estimates too short for complexity

3. Determine if the issue is fixable by an agent or requires human intervention
4. Create a PatchPlan with specific fix instructions

ANALYSIS PROCESS:
1. Read validation_result.summary for high-level error description
2. Read validation_result.device_outputs to see actual CLI output from devices
3. Read validation_result.logs for detailed execution logs
4. Compare expected behavior (from draft_lab_guide) with actual behavior (from device_outputs)
5. Cross-reference with design_output to check topology/config correctness
6. Identify specific commands, configs, or specs that failed

CLASSIFICATION GUIDELINES:

**DESIGN Issues** (target_agent: "designer"):
- Topology YAML errors (wrong links, missing devices)
- Initial config errors (wrong IPs, missing routes, incorrect VLANs)
- Configuration that prevents lab objectives from being achievable
- Platform/device type mismatches

**INSTRUCTION Issues** (target_agent: "author"):
- Lab guide commands that don't work (syntax errors, wrong interfaces)
- Missing configuration steps
- Incorrect command sequence (e.g., configuring interface before entering config mode)
- Verification commands that don't match actual output
- Device name mismatches (uppercase/lowercase issues)

**OBJECTIVES Issues** (target_agent: "planner"):
- Constraints that are impossible to meet
- Time estimates grossly inaccurate
- Prerequisites missing for stated objectives
- Contradictory requirements
Note: OBJECTIVES issues should generally set should_retry=false and escalate to human

OUTPUT FORMAT:
Return a PatchPlan JSON object with:
{
  "root_cause_type": "DESIGN" | "INSTRUCTION" | "OBJECTIVES",
  "analysis": "Detailed explanation of what went wrong and why",
  "target_agent": "designer" | "author" | "planner",
  "patch_instructions": "Specific, actionable guidance for the target agent to fix the issue",
  "should_retry": true | false,
  "confidence": "high" | "medium" | "low"
}

PATCH INSTRUCTIONS GUIDELINES:
- Be SPECIFIC: Don't say "fix the IP addresses", say "Change R1 GigabitEthernet0/0 IP from 10.1.1.1 to 192.168.1.1"
- Be ACTIONABLE: Target agent should know exactly what to change
- Reference specific devices, interfaces, commands, or steps by line number
- Include the error evidence from validation logs

EXAMPLES:

Example 1 - DESIGN Issue:
```json
{
  "root_cause_type": "DESIGN",
  "analysis": "Validation failed because R1 cannot ping R2's loopback (2.2.2.2). Device logs show 'Destination unreachable'. The issue is in design_output.initial_configs: R1 is missing a static route to R2's loopback network. R1 has route to 10.2.2.0/24 but R2's loopback is 2.2.2.2/32 which is not in that subnet.",
  "target_agent": "designer",
  "patch_instructions": "Add static route to R1's initial_configs: 'ip route 2.2.2.2 255.255.255.255 10.1.1.2'. This will allow R1 to reach R2's loopback via the link subnet.",
  "should_retry": true,
  "confidence": "high"
}
```

Example 2 - INSTRUCTION Issue:
```json
{
  "root_cause_type": "INSTRUCTION",
  "analysis": "Validation failed on device R1 with error 'Invalid input detected at ^'. The draft_lab_guide contains command 'ip address 10.1.1.1 255.255.255.0' but device logs show this was entered at privileged EXEC mode instead of interface configuration mode. The lab guide is missing the 'interface GigabitEthernet0/0' step before the ip address command.",
  "target_agent": "author",
  "patch_instructions": "In device_sections for R1, add a step before the 'ip address' command: {type: 'cmd', value: 'interface GigabitEthernet0/0', description: 'Enter interface configuration mode'}. Ensure commands are in correct sequence: configure terminal → interface → ip address → no shutdown.",
  "should_retry": true,
  "confidence": "high"
}
```

Example 3 - OBJECTIVES Issue (escalate):
```json
{
  "root_cause_type": "OBJECTIVES",
  "analysis": "Validation failed because the exercise_spec requires 'Configure BGP with 3 autonomous systems' but also specifies 'beginner level' and '20 minutes'. BGP configuration for 3 AS with proper verification realistically requires 60+ minutes for beginners. This is a fundamental spec issue.",
  "target_agent": "planner",
  "patch_instructions": "The exercise scope is unrealistic for the time constraint and skill level. Recommend either: (1) Reduce to single BGP peering (30 min), (2) Change to intermediate level, or (3) Increase time to 75 minutes. Requires human decision.",
  "should_retry": false,
  "confidence": "high"
}
```

IMPORTANT:
- Only analyze failures (validation_result.success == false)
- If validation succeeded, return should_retry=false with analysis="Validation passed"
- Set should_retry=false if issue requires human intervention
- Set confidence based on how clear the root cause is from logs
- OUTPUT FORMAT: Return ONLY raw JSON, NO markdown fences, NO ```json wrapper
- Your response must be pure JSON starting with { and ending with }
""",
        output_key="patch_plan",
    )


def create_patch_router_agent() -> LlmAgent:
    """Create the patch router agent that applies fixes based on RCA analysis."""

    return LlmAgent(
        model="gemini-2.5-flash",
        name="PatchRouterAgent",
        description="Routes patch plans to appropriate agents for targeted fixes",
        instruction="""
You are a patch routing agent that applies fixes based on RCA analysis.

CRITICAL: Parse the patch_plan from this JSON input:

{patch_plan?}

STEP 1: Parse the patch_plan JSON above
- If empty or missing, return "ESCALATE - No patch plan available"
- Extract: root_cause_type, target_agent, patch_instructions, should_retry, confidence

STEP 2: Check should_retry flag
- If should_retry == false:
  * Return "ESCALATE" to break out of retry loop
  * Add explanation from patch_plan.analysis
  * Example: "ESCALATE - Exercise specification issues detected. Human review required."

STEP 3: Check confidence level
- If confidence == "low":
  * Return "ESCALATE - Root cause unclear. Human analysis needed."

STEP 4: Route based on target_agent
- Extract patch_instructions from the patch_plan JSON
- Route to the appropriate agent with specific fix guidance

ROUTING LOGIC:

**If target_agent == "designer"**:
- The Designer agent is available as a tool (if needed)
- Return text explaining what needs to be fixed based on patch_instructions
- Example: "DESIGN FIX NEEDED: [patch_instructions content]. Designer should regenerate topology_yaml and initial_configs."

**If target_agent == "author"**:
- The Author agent is available as a tool (if needed)
- Return text explaining what needs to be fixed based on patch_instructions
- Example: "INSTRUCTION FIX NEEDED: [patch_instructions content]. Author should regenerate draft_lab_guide with corrected steps."

**If target_agent == "planner"**:
- Return "ESCALATE" (spec changes require human approval)
- Explain: "ESCALATE - Exercise specification issues detected. Human review required."

OUTPUT FORMAT:
- If escalating: Return text starting with "ESCALATE" keyword
- If fixes needed: Return text starting with "DESIGN FIX NEEDED" or "INSTRUCTION FIX NEEDED"
- If validation passed: Return "SUCCESS - Validation passed, no fixes needed"

IMPORTANT:
- The "ESCALATE" keyword signals LoopAgent to stop iteration
- Do NOT escalate on first failure - only if should_retry=false or confidence=low
- Trust the RCA agent's analysis and routing decision
- Extract all information from the patch_plan JSON provided above
""",
        output_key="patch_result",
    )


# Create singleton instances
rca_agent = create_rca_agent()
patch_router_agent = create_patch_router_agent()
