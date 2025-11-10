# NetGenius Instructor Copilot - Frontend

Web interface for the NetGenius Instructor Copilot AI-powered networking lab generator.

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **State Management:** React Query (TanStack Query) + Zustand
- **Syntax Highlighting:** react-syntax-highlighter
- **Markdown Rendering:** react-markdown
- **Deployment:** Google Cloud Run

## Features

- **Lab Library** - Browse and filter generated labs
- **Lab Creation Wizard** - Simple prompt-based lab generation
- **Real-time Progress Tracking** - Watch agents work through pipeline stages
- **Multi-panel Review Interface** - View topology, configs, lab guide, and validation results
- **Polling-based Updates** - Automatic status updates every 3 seconds
- **Mock Data Mode** - Full frontend functionality without backend (for development)

## Project Structure

```
frontend/
├── app/
│   ├── page.tsx              # Home page (lab library)
│   ├── create/page.tsx       # Lab creation wizard
│   ├── labs/[id]/page.tsx    # Lab detail view
│   └── layout.tsx            # Root layout with providers
├── components/
│   ├── LabWizard/
│   │   ├── PromptInput.tsx   # Lab prompt input form
│   │   └── ProgressTracker.tsx # Pipeline stage tracker
│   ├── LabReview/
│   │   ├── TopologyPanel.tsx    # YAML topology display
│   │   ├── ConfigsPanel.tsx     # Device configs with tabs
│   │   ├── GuidePanel.tsx       # Lab guide markdown
│   │   └── ValidationPanel.tsx  # Validation results
│   ├── LabLibrary/
│   │   ├── LabCard.tsx       # Individual lab card
│   │   └── LabList.tsx       # Lab grid with filters
│   └── shared/
│       ├── StatusBadge.tsx   # Status indicator
│       └── CodeBlock.tsx     # Syntax-highlighted code
├── lib/
│   ├── types.ts              # TypeScript types
│   ├── api.ts                # API client (with mock data)
│   ├── hooks.ts              # React Query hooks
│   ├── providers.tsx         # React Query provider
│   └── mockData.ts           # Mock lab storage
├── Dockerfile                # Cloud Run deployment
├── deploy.sh                 # Deployment script
└── next.config.ts            # Next.js config (standalone output)
```

## Getting Started

### Prerequisites

- Node.js 20+
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
# Run development server
npm run dev

# Open http://localhost:3000
```

The frontend will run in **mock data mode** by default, simulating the full lab creation pipeline without a backend.

### Mock Data Mode

By default, the frontend uses mock data to simulate backend interactions. This allows you to:
- Create labs and watch the simulated pipeline progress
- View all UI components with realistic data
- Test polling and real-time updates
- Develop frontend features independently

To switch to real backend mode, update `lib/api.ts`:
```typescript
const USE_MOCK_DATA = false; // Connect to real backend
```

And set the backend URL in `.env.local`:
```bash
NEXT_PUBLIC_ORCHESTRATOR_URL=https://your-backend-url.run.app
```

## Building

```bash
# Production build
npm run build

# Start production server
npm start
```

## Deployment to Cloud Run

### Prerequisites

- Google Cloud Project with billing enabled
- gcloud CLI installed and authenticated
- Artifact Registry repository created

### Deploy

```bash
# Set environment variables
export GCP_PROJECT_ID="your-project-id"
export REGION="us-central1"
export ORCHESTRATOR_URL="https://orchestrator-xxx.run.app"

# Run deployment script
./deploy.sh
```

Or manually:

```bash
# Build and push image
gcloud builds submit --tag us-central1-docker.pkg.dev/PROJECT/netgenius/netgenius-frontend

# Deploy to Cloud Run
gcloud run deploy netgenius-frontend \
  --image us-central1-docker.pkg.dev/PROJECT/netgenius/netgenius-frontend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "NEXT_PUBLIC_ORCHESTRATOR_URL=https://orchestrator-xxx.run.app" \
  --memory 512Mi \
  --cpu 1 \
  --port 3000
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_ORCHESTRATOR_URL` | Backend orchestrator API URL | `http://localhost:8080` |

## API Integration

The frontend expects the backend to expose these endpoints:

- `POST /api/labs/create` - Create new lab
- `GET /api/labs/{id}/status` - Get lab status (for polling)
- `GET /api/labs/{id}` - Get full lab details
- `GET /api/labs` - List all labs

See `lib/types.ts` for complete API contracts.

## Development Notes

### Polling Strategy

The frontend polls the backend every 3 seconds when a lab is in progress. Polling stops when the lab reaches a terminal state (`completed` or `failed`).

### TypeScript Types

All types are centralized in `lib/types.ts` and match the backend Pydantic schemas exactly.

### Styling

Uses Tailwind CSS with a custom color scheme:
- Primary: Blue (Cloud Run branding)
- Success: Green
- Running: Yellow/Amber
- Failed: Red

## Troubleshooting

### Build fails with TypeScript errors

```bash
# Clean and rebuild
rm -rf .next node_modules
npm install
npm run build
```

### Mock data not updating

Check browser console for errors. Mock data updates happen in `lib/api.ts` via `setTimeout` chains.

### Cloud Run deployment fails

Ensure:
1. Artifact Registry repository exists
2. `next.config.ts` has `output: 'standalone'`
3. Dockerfile uses correct Node.js version
4. Service account has necessary permissions

## License

Part of the NetGenius project. See root README for license information.
