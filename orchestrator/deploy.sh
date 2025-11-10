#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="netgenius-orchestrator"
REGION="us-central1"
GCS_BUCKET="netgenius-artifacts-dev"
CLOUD_RUN_JOB_NAME="headless-runner"

# Load GOOGLE_API_KEY from .env if it exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | grep GOOGLE_API_KEY | xargs)
fi

# Check if GOOGLE_API_KEY is set
if [ -z "$GOOGLE_API_KEY" ]; then
    echo -e "${RED}Error: GOOGLE_API_KEY not set${NC}"
    echo "Please set GOOGLE_API_KEY in .env file or export it as an environment variable"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}NetGenius Orchestrator Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if PROJECT_ID is set
if [ -z "$PROJECT_ID" ]; then
    echo -e "${YELLOW}PROJECT_ID not set. Attempting to get from gcloud config...${NC}"
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

    if [ -z "$PROJECT_ID" ]; then
        echo -e "${RED}Error: PROJECT_ID not set and could not be determined from gcloud config${NC}"
        echo "Please set PROJECT_ID: export PROJECT_ID=your-gcp-project-id"
        exit 1
    fi
fi

echo -e "${GREEN}Using Project ID: ${PROJECT_ID}${NC}"
echo -e "${GREEN}Service Name: ${SERVICE_NAME}${NC}"
echo -e "${GREEN}Region: ${REGION}${NC}"
echo ""

# Set the project
echo -e "${YELLOW}Setting GCP project...${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}Enabling required GCP APIs...${NC}"
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com

echo -e "${GREEN}✓ APIs enabled${NC}"
echo ""

# Build and push the container
echo -e "${YELLOW}Building container image...${NC}"
echo "This may take several minutes..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

echo -e "${GREEN}✓ Container built and pushed to gcr.io/$PROJECT_ID/$SERVICE_NAME${NC}"
echo ""

# Deploy to Cloud Run
echo -e "${YELLOW}Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --concurrency 80 \
  --max-instances 10 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GCS_BUCKET=$GCS_BUCKET,CLOUD_RUN_JOB_NAME=$CLOUD_RUN_JOB_NAME,CLOUD_RUN_REGION=$REGION,GOOGLE_API_KEY=$GOOGLE_API_KEY"

echo -e "${GREEN}✓ Service deployed${NC}"
echo ""

# Get the service account
echo -e "${YELLOW}Configuring service account permissions...${NC}"
SERVICE_ACCOUNT=$(gcloud run services describe $SERVICE_NAME \
  --region $REGION \
  --format="value(spec.template.spec.serviceAccountName)")

echo "Service Account: $SERVICE_ACCOUNT"

# Grant necessary permissions
echo "Granting Cloud Run Developer role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/run.developer" \
  --condition=None \
  --quiet

echo "Granting Storage Object Admin role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/storage.objectAdmin" \
  --condition=None \
  --quiet

echo "Granting AI Platform User role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/aiplatform.user" \
  --condition=None \
  --quiet

echo -e "${GREEN}✓ Permissions configured${NC}"
echo ""

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --region $REGION \
  --format="value(status.url)")

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}Service URL: ${SERVICE_URL}${NC}"
echo ""
echo -e "${YELLOW}Test the deployment:${NC}"
echo "  curl ${SERVICE_URL}/api/labs"
echo ""
echo -e "${YELLOW}Create a test lab:${NC}"
echo "  curl -X POST ${SERVICE_URL}/api/labs/create \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"prompt\": \"Create a lab to teach basic router configuration\"}'"
echo ""
echo -e "${YELLOW}View logs:${NC}"
echo "  gcloud run services logs read $SERVICE_NAME --region $REGION"
echo ""
echo -e "${YELLOW}Update the frontend .env with:${NC}"
echo "  NEXT_PUBLIC_API_URL=${SERVICE_URL}"
echo ""
