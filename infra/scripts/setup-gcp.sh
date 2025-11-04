#!/bin/bash
# GCP Infrastructure Setup Script for NetGenius

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-netgenius-hackathon}"
REGION="${REGION:-us-central1}"
BUCKET_NAME="${GCS_BUCKET:-netgenius-artifacts-dev}"
REGISTRY_NAME="netgenius"

echo "=== NetGenius GCP Setup ==="
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Enable required APIs
echo "1. Enabling required GCP APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  cloudbuild.googleapis.com \
  --project="$PROJECT_ID"

# Create Artifact Registry repository
echo ""
echo "2. Creating Artifact Registry repository..."
gcloud artifacts repositories create "$REGISTRY_NAME" \
  --repository-format=docker \
  --location="$REGION" \
  --description="NetGenius Docker images" \
  --project="$PROJECT_ID" \
  || echo "Repository already exists"

# Create GCS bucket
echo ""
echo "3. Creating GCS bucket for artifacts..."
gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://$BUCKET_NAME" \
  || echo "Bucket already exists"

# Set bucket lifecycle (delete old artifacts after 30 days)
cat > /tmp/lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 30}
      }
    ]
  }
}
EOF
gsutil lifecycle set /tmp/lifecycle.json "gs://$BUCKET_NAME"

# Create service accounts
echo ""
echo "4. Creating service accounts..."

# Orchestrator SA
gcloud iam service-accounts create netgenius-orchestrator \
  --display-name="NetGenius Orchestrator" \
  --project="$PROJECT_ID" \
  || echo "Orchestrator SA already exists"

# Parser-Linter SA
gcloud iam service-accounts create netgenius-parser-linter \
  --display-name="NetGenius Parser-Linter" \
  --project="$PROJECT_ID" \
  || echo "Parser-Linter SA already exists"

# Runner SA
gcloud iam service-accounts create netgenius-runner \
  --display-name="NetGenius Headless Runner" \
  --project="$PROJECT_ID" \
  || echo "Runner SA already exists"

# Grant permissions
echo ""
echo "5. Configuring IAM permissions..."

# Runner SA can write to GCS
gsutil iam ch \
  "serviceAccount:netgenius-runner@${PROJECT_ID}.iam.gserviceaccount.com:roles/storage.objectAdmin" \
  "gs://$BUCKET_NAME"

# Orchestrator SA can read from GCS
gsutil iam ch \
  "serviceAccount:netgenius-orchestrator@${PROJECT_ID}.iam.gserviceaccount.com:roles/storage.objectViewer" \
  "gs://$BUCKET_NAME"

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Next steps:"
echo "1. Deploy parser-linter: ./deploy-parser-linter.sh"
echo "2. Deploy headless-runner: ./deploy-headless-runner.sh"
echo "3. Configure OIDC auth between services"
echo ""
echo "Artifact Registry: $REGION-docker.pkg.dev/$PROJECT_ID/$REGISTRY_NAME"
echo "GCS Bucket: gs://$BUCKET_NAME"
