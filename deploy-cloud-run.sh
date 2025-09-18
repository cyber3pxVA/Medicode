#!/bin/bash

# Cloud Run Deployment Script for Medicode
# Usage: ./deploy-cloud-run.sh PROJECT_ID [REGION]

set -e

PROJECT_ID=${1}
REGION=${2:-us-central1}
SERVICE_NAME="medicodeweb"

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: PROJECT_ID is required"
    echo "Usage: $0 PROJECT_ID [REGION]"
    echo "Example: $0 my-gcp-project us-central1"
    exit 1
fi

echo "🚀 Deploying Medicode to Cloud Run..."
echo "   Project ID: $PROJECT_ID"
echo "   Region: $REGION"
echo "   Service: $SERVICE_NAME"
echo ""

# Build and submit to Container Registry
echo "📦 Building and submitting container image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME ./medical-coding-app

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region=$REGION \
  --allow-unauthenticated \
  --timeout=900 \
  --memory=2Gi \
  --cpu=2 \
  --max-instances=10

echo "✅ Deployment complete!"
echo ""
echo "🌐 Your application should be available at:"
gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)'