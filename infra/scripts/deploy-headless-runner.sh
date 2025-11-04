#!/bin/bash
# Deploy Headless Runner as Cloud Run Job

set -e

PROJECT_ID="${GCP_PROJECT_ID:-netgenius-hackathon}"
REGION="${REGION:-us-central1}"
JOB_NAME="headless-runner"
IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/netgenius/$JOB_NAME"
GCS_BUCKET="${GCS_BUCKET:-netgenius-artifacts-dev}"

echo "=== Deploying Headless Runner Job ==="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Image: $IMAGE_NAME"
echo ""

# Build and push image
echo "1. Building Docker image..."
cd ../../headless-runner
gcloud builds submit \
  --tag="$IMAGE_NAME:latest" \
  --project="$PROJECT_ID" \
  .

# Check if job exists
if gcloud run jobs describe "$JOB_NAME" \
  --region="$REGION" \
  --project="$PROJECT_ID" &>/dev/null; then

  echo ""
  echo "2. Updating existing Cloud Run Job..."
  gcloud run jobs update "$JOB_NAME" \
    --image="$IMAGE_NAME:latest" \
    --region="$REGION" \
    --project="$PROJECT_ID"
else
  echo ""
  echo "2. Creating Cloud Run Job..."
  gcloud run jobs create "$JOB_NAME" \
    --image="$IMAGE_NAME:latest" \
    --region="$REGION" \
    --service-account="netgenius-runner@$PROJECT_ID.iam.gserviceaccount.com" \
    --memory=2Gi \
    --cpu=1 \
    --task-timeout=2h \
    --max-retries=0 \
    --parallelism=1 \
    --set-env-vars="GCS_BUCKET=$GCS_BUCKET,REGION=$REGION" \
    --project="$PROJECT_ID"
fi

echo ""
echo "=== Deployment Complete! ==="
echo ""
echo "Test job execution:"
echo "gcloud run jobs execute $JOB_NAME \\"
echo "  --region=$REGION \\"
echo "  --project=$PROJECT_ID \\"
echo "  --wait"
