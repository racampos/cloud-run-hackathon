#!/bin/bash
# Deploy Parser-Linter service to Cloud Run

set -e

PROJECT_ID="${GCP_PROJECT_ID:-netgenius-hackathon}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="parser-linter"
IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/netgenius/$SERVICE_NAME"

echo "=== Deploying Parser-Linter Service ==="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Image: $IMAGE_NAME"
echo ""

# Build and push image
echo "1. Building Docker image..."
cd ../../parser-linter
gcloud builds submit \
  --tag="$IMAGE_NAME:latest" \
  --project="$PROJECT_ID" \
  .

# Deploy to Cloud Run
echo ""
echo "2. Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE_NAME:latest" \
  --region="$REGION" \
  --platform=managed \
  --no-allow-unauthenticated \
  --service-account="netgenius-parser-linter@$PROJECT_ID.iam.gserviceaccount.com" \
  --min-instances=0 \
  --max-instances=10 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=30s \
  --port=8080 \
  --project="$PROJECT_ID"

# Get service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --format="value(status.url)")

echo ""
echo "=== Deployment Complete! ==="
echo "Service URL: $SERVICE_URL"
echo ""
echo "Test with:"
echo "curl -H \"Authorization: Bearer \$(gcloud auth print-identity-token)\" \\"
echo "  $SERVICE_URL/health"
