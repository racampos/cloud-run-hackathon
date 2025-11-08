# Frontend Implementation Plan - NetGenius MVP

**Status:** Ready for Implementation
**Framework:** Next.js 14 (App Router)
**Deployment:** Google Cloud Run
**Deadline:** Hackathon submission
**Target:** Desktop-only, MVP feature set

---

## 1. Scope & Constraints

### In Scope
- Lab creation wizard with prompt input
- Real-time progress tracking (polling-based)
- Multi-panel review interface (topology YAML, configs, draft guide)
- Validation results display (headless runner artifacts)
- Lab history/library view
- Basic feedback mechanism for instructor corrections

### Out of Scope (MVP)
- Parser-linter integration (backend feature not ready)
- Topology visualization diagrams (show YAML only)
- Direct markdown editing in UI (feedback-only)
- User authentication (single-user tool)
- Mobile/tablet responsive design
- Advanced search/filtering

---

## 2. Architecture

```
frontend/
├── app/                          # Next.js 14 App Router
│   ├── page.tsx                 # Home / Lab library
│   ├── create/page.tsx          # Lab creation wizard
│   ├── labs/[id]/page.tsx       # Lab detail view
│   ├── layout.tsx               # Root layout
│   └── api/                     # API route proxies
│       └── orchestrator/[...path]/route.ts
├── components/
│   ├── LabWizard/
│   │   ├── PromptInput.tsx      # Initial prompt entry
│   │   ├── PlanningQA.tsx       # Q&A with Planner agent
│   │   └── ProgressTracker.tsx  # Agent status pipeline
│   ├── LabReview/
│   │   ├── TopologyPanel.tsx    # YAML display
│   │   ├── ConfigsPanel.tsx     # Initial/target configs
│   │   ├── GuidePanel.tsx       # Draft Lab Guide markdown
│   │   └── ValidationPanel.tsx  # Runner results + artifacts
│   ├── LabLibrary/
│   │   ├── LabCard.tsx          # Individual lab item
│   │   └── LabList.tsx          # Grid/list view
│   └── shared/
│       ├── StatusBadge.tsx      # Agent/job status indicators
│       ├── CodeBlock.tsx        # Syntax-highlighted YAML/configs
│       └── ErrorDisplay.tsx     # Validation errors
├── lib/
│   ├── api.ts                   # API client for orchestrator
│   ├── polling.ts               # Polling utilities
│   └── types.ts                 # TypeScript interfaces
├── public/                       # Static assets
├── styles/                       # Global CSS
├── Dockerfile                    # Cloud Run deployment
├── .dockerignore
├── next.config.js
├── package.json
├── tailwind.config.ts
└── tsconfig.json
```

---

## 3. Data Flow

### Lab Creation Flow
```
User enters prompt
    ↓
POST /api/labs/create { prompt }
    ↓
← { lab_id, status: "planner_running" }
    ↓
Poll GET /api/labs/{id}/status every 3s
    ↓
Receive updates:
  - planner_complete → exercise_spec
  - designer_running → designer_complete
  - author_running → author_complete
  - validator_running → validator_complete
    ↓
Display results in review interface
    ↓
[Optional] POST /api/labs/{id}/feedback if failures
```

### Orchestrator API Endpoints (Backend Requirements)
- `POST /api/labs/create` → `{ lab_id, status }`
- `GET /api/labs/{id}/status` → `{ lab_id, current_agent, progress, data }`
- `GET /api/labs/{id}` → Full lab object with all outputs
- `POST /api/labs/{id}/feedback` → `{ feedback_text, target_agent? }`
- `GET /api/labs` → `[ { lab_id, title, status, created_at }, ... ]`
- `GET /api/artifacts/{exercise_id}/{build_id}/{path}` → GCS artifact proxy

---

## 4. Component Specifications

### 4.1 Lab Creation Wizard (`/create`)

**PromptInput.tsx**
- Large textarea for instructor prompt
- Examples/templates (optional)
- "Generate Lab" button → POST /api/labs/create
- Redirect to `/labs/{id}` on success

**PlanningQA.tsx** (if Planner requires interaction)
- Display questions from Planner agent
- Input fields for objectives, constraints, level
- Submit responses back to `/api/labs/{id}/planning`

**ProgressTracker.tsx**
- Horizontal stepper: Planner → Designer → Author → Validator → Publisher
- Real-time status updates via polling
- Show spinner + elapsed time for current agent
- Display interim outputs (e.g., exercise_spec, topology snippet)

### 4.2 Lab Review Interface (`/labs/{id}`)

**Layout:** 4-panel grid
```
┌─────────────────┬─────────────────┐
│  Topology YAML  │  Configs Panel  │
│                 │  (tabs: R1, R2) │
├─────────────────┴─────────────────┤
│  Draft Lab Guide (Markdown)       │
├───────────────────────────────────┤
│  Validation Results / Artifacts   │
└───────────────────────────────────┘
```

**TopologyPanel.tsx**
- Syntax-highlighted YAML display (react-syntax-highlighter)
- Copy to clipboard button
- Collapsible/expandable

**ConfigsPanel.tsx**
- Tabs for each device (R1, R2, etc.)
- Sub-tabs: Initial Config | Target Config
- Line-numbered code blocks

**GuidePanel.tsx**
- Rendered markdown preview (react-markdown)
- Show inline verification steps clearly
- Download as .md button

**ValidationPanel.tsx**
- Headless runner job status
- Link to GCS artifacts (execution.log, device_histories.json)
- summary.json display: success/failure, timings
- If failure: Show RCA analysis + feedback form

### 4.3 Lab Library (`/`)

**LabList.tsx**
- Grid of LabCard components
- Filter by status: All | Draft | Validated | Failed | Published
- "Create New Lab" button → `/create`

**LabCard.tsx**
- Title, status badge, creation date
- Quick actions: View, Re-validate, Clone
- Click → `/labs/{id}`

---

## 5. Styling & UI Kit

**Tailwind CSS** with custom theme:
- Primary color: Blue (Cloud Run brand alignment)
- Status colors:
  - Running: Yellow/Amber
  - Success: Green
  - Failed: Red
  - Pending: Gray
- Monospace font for code blocks
- Sans-serif for UI text (Inter or system fonts)

**Component Library:** Headless UI or Shadcn UI for modals, dropdowns, tabs

---

## 6. State Management

**React Query (TanStack Query)**
- Polling: `useQuery` with `refetchInterval: 3000` for `/api/labs/{id}/status`
- Mutations: `useMutation` for create, feedback
- Cache labs list and individual lab data

**Zustand** (optional, if needed)
- UI state: selected tab, panel visibility
- User preferences: polling interval

---

## 7. API Integration

**lib/api.ts**
```typescript
const ORCHESTRATOR_URL = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8080';

export async function createLab(prompt: string) {
  const res = await fetch(`${ORCHESTRATOR_URL}/api/labs/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  });
  return res.json();
}

export async function getLabStatus(labId: string) {
  const res = await fetch(`${ORCHESTRATOR_URL}/api/labs/${labId}/status`);
  return res.json();
}

// ... more methods
```

**Next.js API Routes** (optional proxy for CORS/auth)
- `/app/api/orchestrator/[...path]/route.ts` → Proxy to backend

---

## 8. Polling Strategy

**lib/polling.ts**
```typescript
export function useLabPolling(labId: string) {
  return useQuery({
    queryKey: ['lab-status', labId],
    queryFn: () => getLabStatus(labId),
    refetchInterval: (data) => {
      // Stop polling if terminal state
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false;
      }
      return 3000; // Poll every 3 seconds
    },
  });
}
```

---

## 9. Docker Deployment (Cloud Run)

**Dockerfile**
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
```

**Build & Deploy**
```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/PROJECT/netgenius/frontend
gcloud run deploy netgenius-frontend \
  --image us-central1-docker.pkg.dev/PROJECT/netgenius/frontend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ORCHESTRATOR_URL=https://orchestrator-xxx.run.app
```

---

## 10. Environment Variables

```env
# .env.local (development)
NEXT_PUBLIC_ORCHESTRATOR_URL=http://localhost:8080

# Cloud Run (production)
ORCHESTRATOR_URL=https://orchestrator-xxx-uc.a.run.app
```

---

## 11. Implementation Phases

### Phase 1: Foundation (2-3 hours)
- [x] Create frontend/ directory
- [ ] Initialize Next.js 14 with TypeScript + Tailwind
- [ ] Set up basic routing: /, /create, /labs/[id]
- [ ] Create API client stub (lib/api.ts)
- [ ] Set up React Query provider

### Phase 2: Lab Creation Wizard (3-4 hours)
- [ ] PromptInput component
- [ ] ProgressTracker component with polling
- [ ] Basic status display (agent names + spinners)
- [ ] Test with mock data / local orchestrator

### Phase 3: Lab Review Interface (4-5 hours)
- [ ] 4-panel layout with TopologyPanel, ConfigsPanel, GuidePanel, ValidationPanel
- [ ] Syntax highlighting for YAML/configs
- [ ] Markdown rendering for lab guide
- [ ] Artifact links to GCS

### Phase 4: Lab Library (2-3 hours)
- [ ] LabList + LabCard components
- [ ] Status filtering
- [ ] Navigation to detail view

### Phase 5: Feedback & Polish (2-3 hours)
- [ ] Feedback form in ValidationPanel
- [ ] Error handling + toast notifications
- [ ] Loading states
- [ ] Basic responsive tweaks (even though desktop-only)

### Phase 6: Deployment (1-2 hours)
- [ ] Dockerfile + .dockerignore
- [ ] Cloud Run deployment script
- [ ] Environment variable configuration
- [ ] Smoke test on Cloud Run

**Total Estimated Time:** 14-20 hours

---

## 12. Testing Strategy

**Manual Testing (MVP)**
- Test lab creation with sample prompt
- Verify polling updates in real-time
- Check artifact downloads from GCS
- Test feedback submission

**Automated Testing (Post-MVP)**
- Jest + React Testing Library for components
- Playwright for E2E flows

---

## 13. Open Questions for Backend Team

1. **Orchestrator API readiness:** Are the endpoints `/api/labs/create`, `/api/labs/{id}/status` implemented?
2. **Data format:** What does the `status` response look like? Need exact schema.
3. **Artifacts:** Can frontend get signed URLs for GCS artifacts, or should backend proxy them?
4. **CORS:** Will orchestrator allow requests from `https://frontend-xxx.run.app`?
5. **Long-running jobs:** What's the expected max duration for validator jobs? (impacts polling timeout)

---

## 14. Success Criteria

- [ ] Instructor can submit prompt and see lab creation progress
- [ ] Real-time updates (via polling) show agent transitions
- [ ] Review interface displays all outputs: YAML, configs, guide, validation results
- [ ] Artifact links work and download from GCS
- [ ] Lab library shows history of created labs
- [ ] Feedback form submits corrections to orchestrator
- [ ] Frontend deploys to Cloud Run and connects to backend

---

## 15. Future Enhancements (Post-Hackathon)

- WebSocket/SSE for true real-time updates
- Direct markdown editing with live preview
- Topology visualization (network diagram)
- Parser-linter integration (when backend ready)
- User authentication + multi-tenant support
- Advanced filtering/search in lab library
- Export labs as PDF or ZIP
- Mobile/tablet responsive design

---

**Ready to start implementation!** 🚀
