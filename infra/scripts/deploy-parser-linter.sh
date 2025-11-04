#!/bin/bash
# Deploy Parser-Linter service to Cloud Run
#
# NOTE: This script deploys a pre-built image from Artifact Registry.
# The parser-linter service is built and pushed from a separate private repository.

set -e

PROJECT_ID="${GCP_PROJECT_ID:-netgenius-hackathon}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="parser-linter"
IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/netgenius/$SERVICE_NAME"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo "=== Deploying Parser-Linter Service ==="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Image: $IMAGE_NAME:$IMAGE_TAG"
echo ""

# Check if image exists
echo "1. Verifying image exists in Artifact Registry..."
if ! gcloud artifacts docker images describe "$IMAGE_NAME:$IMAGE_TAG" \
  --project="$PROJECT_ID" &>/dev/null; then
  echo ""
  echo "ERROR: Image not found in Artifact Registry"
  echo "Expected: $IMAGE_NAME:$IMAGE_TAG"
  echo ""
  echo "The parser-linter image must be built and pushed from the private repository."
  echo "Run the following in the netgenius-parser-linter repository:"
  echo ""
  echo "  cd /path/to/netgenius-parser-linter"
  echo "  gcloud builds submit --tag=$IMAGE_NAME:$IMAGE_TAG"
  echo ""
  exit 1
fi

echo "✓ Image found"

# Deploy to Cloud Run
echo ""
echo "2. Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE_NAME:$IMAGE_TAG" \
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
