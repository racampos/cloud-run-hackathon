# NetGenius — Teaching Assistant for Networking Instructors (Full PRD)

**Status:** Draft v0.9
**Owner:** Rafael Campos
**Scope:** Hackathon-ready MVP with a clear path to production
**Target platform:** Google Cloud (Cloud Run + Cloud Run Jobs + Artifact Registry + GCS)
**Public repo:** Orchestrator (open-source)
**Private services:** Parser-Linter + Headless Runner (closed-source, private Docker images)

---

## 1) Executive Summary

Networking instructors spend excessive time devising, validating, and grading hands-on labs. NetGenius automates the full lifecycle: planning objectives, designing the topology/configs, authoring student-facing instructions, **validating the Draft Lab Guide headlessly**, and publishing a final, solvable lab. The result is a higher throughput of high‑quality labs with fewer instructor hours.

**Key differentiators**

- Validates **the actual Draft Lab Guide** (not a proxy spec) via a fast parser‑linter + ephemeral simulation run.
- Uses a **multi‑agent graph** (Google’s ADK) with explicit tools and data contracts for reliable orchestration.
- Headless simulator runs as **Cloud Run Job** (ephemeral, no inbound traffic) with artifacts in GCS.

---

## 2) Goals & Non‑Goals

### 2.1 Goals

- Generate instructor‑quality, student‑facing **Final Lab Guides** that are **actually solvable**.
- Make validation **cheap and fast**: parser‑lint first, then a single headless job.
- Provide a clean API and artifacts so instructors can review and publish with confidence.

### 2.2 Non‑Goals

- No student grading engine (out of scope for MVP).
- No real hardware orchestration (simulator-only).
- No open‑sourcing of the parser engine (kept private due to IP).

---

## 3) Personas & Primary Use Cases

- **Instructor (primary):** “Create a lab for OSPF on two routers + two networks. Level: CCNA. Time: 30–45 min.”
- **Content Team Lead:** Curates a course catalog, needs solvable, consistent labs.
- **Hackathon Judge:** Evaluates technical architecture, reliability, and dev‑experience polish.

---

## 4) Success Criteria / KPIs

- ≥ 90% of Draft Lab Guides pass headless validation on first or second iteration.
- End‑to‑end lab creation time ≤ 10 minutes for typical CCNA exercises.
- Parser‑lint completes in ≤ 3 seconds for ≤ 200 commands.
- Headless job completes in ≤ 5 minutes for typical topologies.

---

## 5) System Overview

High‑level components:

1. **Orchestrator (ADK)** — multi‑agent graph coordinating tool calls and data hand‑offs.
2. **Parser‑Linter Service (private, Cloud Run)** — `/lint/topology`, `/lint/cli` (stateful/stateless).
3. **Headless Runner (private, Cloud Run Job)** — executes the lab end‑to‑end against the **proprietary simulator** (linked as a dependency), outputs GCS artifacts.
4. **Publisher (part of Orchestrator)** — produces Final Lab Guide + metadata and stores artifact pointers.

Data flows:

- Instructor → Planner → Designer → Author → **Linter** (fast) → **Headless Job** (Go/No‑Go) → Publisher.
- Failures routed by **RCA Agent** back to the right stage, then re-validated.

---

## 6) Data Contracts (Top‑Level)

### 6.1 ExerciseSpec (Planner → Designer)

```json
{
  "title": "OSPF basics on two routers",
  "objectives": ["enable OSPF", "adjacency up", "inter‑LAN reachability"],
  "constraints": { "devices": 4, "time_minutes": 45 },
  "level": "CCNA"
}
```

### 6.2 DesignOutput (Designer → Author)

```json
{
  "topology_yaml": "<YAML>",
  "initial_configs": { "r1": ["configure terminal", "..."], "r2": ["..."] },
  "target_configs": { "r1": ["..."], "r2": ["..."] },
  "platforms": { "r1": "cisco_2911", "r2": "cisco_2911" }
}
```

### 6.3 DraftLabGuide (Author → Validator)

Markdown + machine-readable blocks per device with command sequences and inline verification steps (syntax shown in §10.2 runner payload mapping).

### 6.4 Headless Job Artifacts (Validator → Publisher)

- `execution.log` (streamed job log)
- `device_histories.json` (per‑device CLI timeline)
- `topology.yaml`, `initial_config/`, `final_config/`
- `summary.json` (success/failure, timings)

---

## 7) Agent System (ADK) — **Revised**

**We validate the actual Draft Lab Guide.** A dual‑mode linter catches syntax/submode errors before an ephemeral simulator run.

### 7.1 Agents

1. **Pedagogy Planner** — multi‑turn Q&A with instructor → **ExerciseSpec**.
2. **Designer** — produces **Topology YAML**, **InitialConfig**, **TargetConfig**; preflight lint:

   - `POST /lint/topology`
   - `POST /lint/cli` **stateful** over full InitialConfig (includes `configure terminal`, `interface ...`, `router ...`)
   - _(optional)_ `POST /lint/cli` **stateless** for granular bucketing per mode

3. **Lab Guide Author** — writes **Draft Lab Guide** with **inline verification steps**; preflight lint:

   - `POST /lint/cli` **stateful** per device section exactly as written

4. **Validator (Headless Runner Orchestrator)** — translates Draft Lab Guide → headless job payload, launches **Cloud Run Job**, collects artifacts, computes **Go/No‑Go**.
5. **Root‑Cause & Triage (RCA)** — on failure, classifies cause (Design vs Instruction vs Objectives) and routes patch to the right agent with a minimal **PatchPlan**.
6. **Publisher** — converts **Draft → Final Lab Guide**, publishes, and notifies instructor.
7. **Orchestrator (ADK)** — manages tools: `parser_linter.topology`, `parser_linter.cli`, `headless_runner.submit_job`, `artifacts.read`, `publisher.publish`.

### 7.2 Inline Verification (Author best‑practice)

- Interleave verifies like `show ip interface brief`, `show ip route`, `ping`.
- These verifies are **also linted** (stateful) to catch typos early.

### 7.3 Linting discipline

- Default `stop_on_error=false` to surface all issues in one pass.
- Run headless only after **all lints pass**.

---

## 8) Headless Runner (Cloud Run Job)

- **Image/module:** `headless_runner` (private repo), Python 3.11.
- **Input:** JSON payload mapped from Draft Lab Guide (per‑device sequences, topology YAML, options).
- **Behavior:**

  1. Start simulator processes via internal IPC;
  2. Apply initial configs;
  3. Execute Author steps with inline verifies;
  4. Capture per‑device histories;
  5. Write artifacts to GCS;
  6. Exit 0/1 with summary.

- **Timeout:** ≤ 2h (typical runs in minutes).
- **Resources:** start with 1 vCPU / 1–2 GiB RAM (tunable).
- **Concurrency:** 1 (single simulation per job).
- **No inbound traffic**; invoked via Cloud Run Jobs API / gcloud.

---

## 9) Simulator Interface (existing, proprietary)

- Local Python package providing `SimulationManager` + device/CLI IPC.
- No HTTP/WS required in headless mode.
- Stays private; distributed to the job container via dependency.

---

## 10) APIs — **Revised**

### 10.1 Parser‑Linter Service (private, Cloud Run)

**Purpose:** fast preflight validation mirroring Cisco IOS behavior.

#### POST `/lint/topology`

**Request**

```json
{ "topology_yaml": "<raw YAML>" }
```

**Response**

```json
{ "ok": true, "issues": [] }
```

_Notes:_ human‑readable messages; `ok=true` with empty issues means pass.

#### POST `/lint/cli`

**Two execution strategies in a single endpoint.**

**Request**

```json
{
  "device_type": "cisco_2911",
  "sequence_mode": "stateful", // "stateful" (default) | "stateless"
  "start_mode": { "type": "privileged" }, // optional; default privileged exec
  "commands": [
    // stateful: raw script including mode transitions
    { "command": "configure terminal" },
    { "command": "interface GigabitEthernet0/0" },
    { "command": "ip address 10.0.0.1 255.255.255.0" },
    { "command": "no shutdown" },

    // stateless: explicit mode per line, no transitions
    { "mode": { "type": "global" }, "command": "hostname R1" },
    {
      "mode": { "type": "interface", "name": "GigabitEthernet0/0" },
      "command": "ip address 10.0.0.2 255.255.255.0"
    }
  ],
  "options": { "stop_on_error": false }
}
```

**Response**

```json
{
  "results": [
    {
      "ok": true,
      "command": "configure terminal",
      "mode_before": { "type": "privileged" },
      "mode_after": { "type": "global" },
      "message": ""
    },
    {
      "ok": false,
      "command": "interface GigabitEthernet0/0",
      "mode_before": { "type": "global" },
      "mode_after": { "type": "global" },
      "message": "% Invalid input detected at '^' marker.\n                           ^"
    },
    {
      "ok": true,
      "command": "hostname R1",
      "mode": { "type": "global" },
      "message": ""
    }
  ],
  "parser_version": "ng-parser-2025.11.01"
}
```

**Usage guidance**

- **Designer:** `stateful` over full InitialConfig; optional `stateless` for granular bucketing.
- **Author:** `stateful` per device section exactly as written in the Draft Lab Guide.
- Batch ≤ 200–300 commands; prefer `stop_on_error=false` to surface all issues.

**Auth:** Cloud Run↔Cloud Run via **OIDC**; only Orchestrator SA has `roles/run.invoker`.

### 10.2 Headless Runner API (private repo component)

- `POST headless_runner.submit_job(payload)` → `{ job_id, status_url }`
- `GET artifacts.read({ job_id, path })` → stream artifact from GCS

**Runner payload (abridged)**

```json
{
  "exercise_id": "ex-123",
  "topology_yaml": "<raw YAML>",
  "devices": {
    "r1": {
      "platform": "cisco_2911",
      "initial": ["configure terminal", "..."],
      "steps": [
        { "type": "cmd", "value": "interface Gi0/0" },
        { "type": "cmd", "value": "ip address 10.0.0.1 255.255.255.0" },
        { "type": "verify", "value": "show ip interface brief" }
      ]
    },
    "r2": { "platform": "cisco_2911", "initial": ["..."], "steps": ["..."] }
  },
  "options": { "non_interactive": true }
}
```

**Artifacts (GCS)**

```
/artifacts/{exercise_id}/{build_id}/
  execution.log
  device_histories.json
  topology.yaml
  initial_config/
  final_config/
  summary.json
```

### 10.3 Publisher API (public)

- `publisher.publish({ exercise_id, build_id, guide_markdown, metadata })` → `{ url, version }`

---

## 11) GCP Deployment & DevOps

- **Regions:** use `us-central1` for simplicity.
- **Artifact Registry:** `docker.pkg.dev/<project>/netgenius/*`.
- **Cloud Run Job (headless):** no ingress, 1 vCPU, 1–2GiB RAM, timeout ≤ 2h, SA = `netgenius-orchestrator@<project>.iam.gserviceaccount.com` with:

  - `roles/run.invoker` (for orchestrator to start jobs)
  - `roles/storage.objectAdmin` on artifacts bucket

- **Cloud Run Service (parser‑linter):** min 0, max N; SA with `roles/run.invoker` limited to orchestrator; no public unauthenticated access.
- **GCS:** bucket `netgenius-artifacts-<env>` with lifecycle on logs/histories.
- **CI/CD:** GitHub Actions: build → push → deploy via `gcloud run deploy` / `gcloud run jobs update`.

---

## 12) Security & Compliance

- Service‑to‑service auth with **OIDC**.
- Principle of least privilege on SAs.
- No PII beyond instructor account metadata.

---

## 13) Telemetry, Logging, and Observability

- **JSON logs** across services; include `exercise_id`, `build_id`, `job_id`.
- Basic metrics: lint time, job time, pass/fail rate.
- Error budgets for linter 5xx and runner failures.

---

## 14) UX Flows (abridged)

1. Instructor starts with a prompt → Planner Q&A → Objectives.
2. Designer produces topology/configs → Lints.
3. Author drafts guide with inline verifies → Lints.
4. Validator launches headless job → artifacts → Go/No‑Go.
5. Publisher emits Final Lab Guide and notifies instructor.

---

## 15) Acceptance Tests

- **Smoke:** minimal 2‑router static routing lab passes end‑to‑end.
- **Negative:** invalid interface name caught by `/lint/cli` (stateful).
- **Resilience:** simulator crash returns structured failure with actionable artifacts.

---

## 16) Risks & Mitigations

- **Parser false negatives/positives:** use stateful + optional stateless passes; add golden tests.
- **Simulator nondeterminism:** seed fixed timing where possible; retry once.
- **GCP quotas:** keep small regions, request increases only if needed.

---

## 17) Milestones (Hackathon cadence)

- **M1 (Day 1–2):** Orchestrator skeleton, linter service stub, runner skeleton.
- **M2 (Day 3–4):** Designer/Author agents + linter integration (stateful).
- **M3 (Day 5):** Headless validation end‑to‑end + artifacts.
- **M4 (Day 6):** RCA routing + Publisher + polish.
- **Demo (Day 7):** 2–3 example labs (static routing, VLAN, RIP/OSPF basic).

---

## 18) Open Questions

- Do we enforce a canonical per‑device section format in the Draft Lab Guide Markdown?
- Any need for graded "checkpoints" for future student‑side validation?
- Should we surface partial simulator timelines in the instructor UI before the final Go/No‑Go?

---

## Appendix A — Draft Lab Guide → Runner Mapping (example)

```
# Draft Lab Guide (excerpt)
Device R1
1) configure terminal
2) interface Gi0/0
3) ip address 10.0.0.1 255.255.255.0
4) no shutdown
5) verify: show ip interface brief

Device R2
...
```

→

```json
{
  "exercise_id": "ex-001",
  "topology_yaml": "...",
  "devices": {
    "r1": {
      "platform": "cisco_2911",
      "initial": ["configure terminal", "! optional seed"],
      "steps": [
        { "type": "cmd", "value": "configure terminal" },
        { "type": "cmd", "value": "interface Gi0/0" },
        { "type": "cmd", "value": "ip address 10.0.0.1 255.255.255.0" },
        { "type": "cmd", "value": "no shutdown" },
        { "type": "verify", "value": "show ip interface brief" }
      ]
    }
  },
  "options": { "non_interactive": true }
}
```
