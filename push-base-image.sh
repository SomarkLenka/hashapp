#!/bin/bash

# Script to push base image to Docker Hub
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get Docker Hub username
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: $0 <dockerhub-username>${NC}"
    echo "Example: $0 myusername"
    exit 1
fi

DOCKER_USERNAME=$1
BASE_IMAGE_NAME="myapp-base"
IMAGE_TAG="latest"
REMOTE_IMAGE="${DOCKER_USERNAME}/${BASE_IMAGE_NAME}:${IMAGE_TAG}"

echo -e "${GREEN}[INFO]${NC} Checking Docker login status..."

# Check if logged in
if ! docker system info 2>/dev/null | grep -q "Username"; then
    echo -e "${YELLOW}[WARN]${NC} Not logged in to Docker Hub"
    echo -e "${GREEN}[INFO]${NC} Please log in to Docker Hub:"
    docker login
fi

echo -e "${GREEN}[INFO]${NC} Tagging image for Docker Hub..."
echo -e "${GREEN}[INFO]${NC} Local image: ${BASE_IMAGE_NAME}:${IMAGE_TAG}"
echo -e "${GREEN}[INFO]${NC} Remote image: ${REMOTE_IMAGE}"

# Tag the image
docker tag "${BASE_IMAGE_NAME}:${IMAGE_TAG}" "${REMOTE_IMAGE}"

echo -e "${GREEN}[INFO]${NC} Pushing image to Docker Hub..."
docker push "${REMOTE_IMAGE}"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}[SUCCESS]${NC} Image pushed successfully!"
    echo -e "${GREEN}[INFO]${NC} Image available at: docker.io/${REMOTE_IMAGE}"
    echo ""
    echo "To use this image in your Dockerfile:"
    echo "  ARG BASE_IMAGE=${REMOTE_IMAGE}"
    echo "  FROM \${BASE_IMAGE}"
else
    echo -e "${RED}[ERROR]${NC} Failed to push image"
    exit 1
fi