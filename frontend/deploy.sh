#!/bin/bash
# Deploy NetGenius Frontend to Cloud Run

set -e

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"your-project-id"}
REGION=${REGION:-"us-central1"}
SERVICE_NAME="netgenius-frontend"
IMAGE_NAME="us-central1-docker.pkg.dev/${PROJECT_ID}/netgenius/${SERVICE_NAME}"

# Backend orchestrator URL (update this when backend is deployed)
ORCHESTRATOR_URL=${ORCHESTRATOR_URL:-"https://orchestrator-${PROJECT_ID}.a.run.app"}

echo "🚀 Deploying NetGenius Frontend to Cloud Run"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "Orchestrator URL: ${ORCHESTRATOR_URL}"
echo ""

# Build and push image
echo "📦 Building Docker image..."
gcloud builds submit --tag "${IMAGE_NAME}" --project "${PROJECT_ID}"

# Deploy to Cloud Run
echo "🌐 Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_NAME}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --set-env-vars "NEXT_PUBLIC_ORCHESTRATOR_URL=${ORCHESTRATOR_URL}" \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --port 3000 \
  --project "${PROJECT_ID}"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Service URL:"
gcloud run services describe "${SERVICE_NAME}" \
  --platform managed \
  --region "${REGION}" \
  --format 'value(status.url)' \
  --project "${PROJECT_ID}"
