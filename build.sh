#!/bin/bash

# Build script for managing Docker images
set -e

# Configuration
BASE_IMAGE_NAME="${BASE_IMAGE_NAME:-myapp-base}"
APP_IMAGE_NAME="${APP_IMAGE_NAME:-hash-generator}"
REGISTRY="${REGISTRY:-}"  # Set to your registry URL if using one
VERSION="${VERSION:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to build base image
build_base() {
    log_info "Building base image: ${BASE_IMAGE_NAME}:${VERSION}"
    
    docker build \
        -f Dockerfile.base \
        --target base-runtime \
        -t "${BASE_IMAGE_NAME}:${VERSION}" \
        -t "${BASE_IMAGE_NAME}:latest" \
        .
    
    if [ $? -eq 0 ]; then
        log_info "Base image built successfully"
        
        # Push to registry if configured
        if [ -n "${REGISTRY}" ]; then
            log_info "Pushing base image to registry: ${REGISTRY}/${BASE_IMAGE_NAME}:${VERSION}"
            docker tag "${BASE_IMAGE_NAME}:${VERSION}" "${REGISTRY}/${BASE_IMAGE_NAME}:${VERSION}"
            docker tag "${BASE_IMAGE_NAME}:latest" "${REGISTRY}/${BASE_IMAGE_NAME}:latest"
            docker push "${REGISTRY}/${BASE_IMAGE_NAME}:${VERSION}"
            docker push "${REGISTRY}/${BASE_IMAGE_NAME}:latest"
        fi
    else
        log_error "Failed to build base image"
        exit 1
    fi
}

# Function to build application image
build_app() {
    local base_ref="${BASE_IMAGE_NAME}:latest"
    
    # Use registry base image if configured
    if [ -n "${REGISTRY}" ]; then
        base_ref="${REGISTRY}/${BASE_IMAGE_NAME}:latest"
    fi
    
    log_info "Building app image: ${APP_IMAGE_NAME}:${VERSION}"
    log_info "Using base image: ${base_ref}"
    
    docker build \
        --build-arg BASE_IMAGE="${base_ref}" \
        -t "${APP_IMAGE_NAME}:${VERSION}" \
        -t "${APP_IMAGE_NAME}:latest" \
        .
    
    if [ $? -eq 0 ]; then
        log_info "Application image built successfully"
        
        # Push to registry if configured
        if [ -n "${REGISTRY}" ]; then
            log_info "Pushing app image to registry: ${REGISTRY}/${APP_IMAGE_NAME}:${VERSION}"
            docker tag "${APP_IMAGE_NAME}:${VERSION}" "${REGISTRY}/${APP_IMAGE_NAME}:${VERSION}"
            docker tag "${APP_IMAGE_NAME}:latest" "${REGISTRY}/${APP_IMAGE_NAME}:latest"
            docker push "${REGISTRY}/${APP_IMAGE_NAME}:${VERSION}"
            docker push "${REGISTRY}/${APP_IMAGE_NAME}:latest"
        fi
    else
        log_error "Failed to build application image"
        exit 1
    fi
}

# Function to check if base image exists
check_base_exists() {
    local base_ref="${BASE_IMAGE_NAME}:latest"
    
    if [ -n "${REGISTRY}" ]; then
        base_ref="${REGISTRY}/${BASE_IMAGE_NAME}:latest"
    fi
    
    if docker image inspect "${base_ref}" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Main script
case "${1:-}" in
    base)
        build_base
        ;;
    app)
        if ! check_base_exists; then
            log_warn "Base image not found, building it first..."
            build_base
        fi
        build_app
        ;;
    all)
        build_base
        build_app
        ;;
    check)
        if check_base_exists; then
            log_info "Base image exists"
        else
            log_warn "Base image not found"
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 {base|app|all|check}"
        echo ""
        echo "Commands:"
        echo "  base   - Build only the base image"
        echo "  app    - Build the application image (builds base if missing)"
        echo "  all    - Build both base and application images"
        echo "  check  - Check if base image exists"
        echo ""
        echo "Environment variables:"
        echo "  BASE_IMAGE_NAME - Name for base image (default: myapp-base)"
        echo "  APP_IMAGE_NAME  - Name for app image (default: hash-generator)"
        echo "  REGISTRY        - Registry URL (optional)"
        echo "  VERSION         - Image version tag (default: latest)"
        exit 1
        ;;
esac

log_info "Build completed successfully!"