#!/bin/bash

# Script to run hash generator with Google Cloud credentials
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Hash Generator Docker Runner${NC}"
echo "================================"

# Check for credentials file
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: $0 <path-to-service-account-key.json>${NC}"
    echo ""
    echo "To get a service account key:"
    echo "1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts"
    echo "2. Select your project: adept-storm-466618-b4"
    echo "3. Create a service account or use existing one"
    echo "4. Grant roles: 'Bigtable User' or 'Bigtable Admin'"
    echo "5. Create and download JSON key"
    echo ""
    echo -e "${YELLOW}Alternative: Use gcloud auth${NC}"
    echo "Run: gcloud auth application-default login"
    echo "Then use: ~/.config/gcloud/application_default_credentials.json"
    exit 1
fi

CREDS_FILE="$1"

# Verify credentials file exists
if [ ! -f "$CREDS_FILE" ]; then
    echo -e "${RED}Error: Credentials file not found: $CREDS_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}Using credentials: $CREDS_FILE${NC}"

# Stop existing container if running
if docker ps -a | grep -q hash-gen; then
    echo "Stopping existing container..."
    docker stop hash-gen 2>/dev/null || true
    docker rm hash-gen 2>/dev/null || true
fi

# Run container with credentials
echo -e "${GREEN}Starting hash generator with BigTable access...${NC}"
docker run -d \
    --name hash-gen \
    -v "$(realpath $CREDS_FILE)":/app/credentials.json:ro \
    -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
    -e GCP_PROJECT_ID=adept-storm-466618-b4 \
    -e BT_INSTANCE_ID=hash-generator-instance \
    -e BT_TABLE_NAME=hashes \
    hash-generator:latest

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Container started successfully!${NC}"
    echo ""
    echo "Commands:"
    echo "  View logs:    docker logs -f hash-gen"
    echo "  Check status: docker ps | grep hash-gen"
    echo "  Stop:         docker stop hash-gen"
    echo "  Remove:       docker rm hash-gen"
else
    echo -e "${RED}Failed to start container${NC}"
    exit 1
fi