# Hash Generator Library Documentation

## Overview
This library provides a comprehensive suite of tools for SHA256 hash generation, GPU-accelerated hashing, and monitoring capabilities. The system includes integration with Google Cloud Bigtable for distributed hash storage and a web-based monitoring dashboard.

## Project Structure

### Core Hash Generation Components
- **hash_generator.py** - Main asynchronous SHA256 hash generator with GPU support and BigTable integration
- **hash_generator_gpu.py** - GPU-optimized hash generation implementation
- **hash_generator_gpu_nvidia.py** - NVIDIA CUDA-specific hash generation
- **hash_generator_real_gpu.py** - Real GPU implementation for hash generation
- **hash_generator_simple.py** - Simplified hash generator for basic use cases
- **hash_generator_fixed.py** - Fixed implementation of hash generator
- **hash_generator_monitored.py** - Hash generator with built-in monitoring capabilities
- **hash_generator_throttled.py** - Rate-limited hash generation implementation
- **hash_generator_fixed_upload.py** - Hash generator with fixed upload mechanism

### GPU-Specific Components
- **gpu_sha256.py** - GPU-accelerated SHA256 implementation
- **gpu_sha256_miner.py** - Mining-oriented GPU SHA256 implementation
- **test_gpu_detection.py** - GPU detection and capability testing
- **test_gpu_access.py** - GPU access verification utility

### Database & Storage
- **setup_bigtable.py** - Setup script for Google Cloud Bigtable instance and tables
- **test_bigtable.py** - Bigtable connection and operation testing
- **query_bigtable.py** - Utilities for querying stored hashes from Bigtable
- **verify_binary_storage.py** - Binary data storage verification

### Testing & Diagnostics
- **test_sha256.py** - SHA256 implementation tests
- **test_hex_format.py** - Hexadecimal formatting tests
- **test_push_hash.py** - Hash upload/push functionality tests
- **diagnose_monitoring.py** - Monitoring system diagnostics
- **verify_inside_container.py** - Container environment verification

## Key Features

### 1. GPU Acceleration
- Support for NVIDIA CUDA GPUs via CuPy
- Automatic fallback to CPU when GPU is unavailable
- Batch processing for improved performance
- Multi-GPU support

### 2. Cloud Integration
- Google Cloud Bigtable for distributed hash storage
- Scalable storage with automatic table management
- Fast hash lookups using SHA256 as row key

### 3. Monitoring & Analytics
- Real-time hash generation monitoring
- Performance metrics tracking
- GPU utilization monitoring
- Web-based dashboard (in hashrate-monitor subdirectory)

### 4. Flexible Implementations
- Multiple hash generator variants for different use cases
- Throttled generation for rate limiting
- Monitored generation for performance tracking
- Simple implementation for basic needs

## Getting Started

1. **Setup Bigtable**: Run `python setup_bigtable.py` to create necessary cloud resources
2. **Test GPU Access**: Run `python test_gpu_detection.py` to verify GPU availability
3. **Run Hash Generator**: Execute `python hash_generator.py` to start generating hashes
4. **Monitor Performance**: Use the monitoring dashboard to track hash generation metrics

## Requirements

- Python 3.7+
- Google Cloud SDK and credentials
- CuPy (for GPU support, optional)
- NumPy
- aiohttp
- google-cloud-bigtable

## Environment Variables

- `GCP_PROJECT_ID`: Google Cloud Project ID
- `BT_INSTANCE_ID`: Bigtable Instance ID
- `BT_TABLE_NAME`: Bigtable Table Name
- `CUDA_VISIBLE_DEVICES`: GPU device selection
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to GCP service account credentials

## Testing

The library includes comprehensive test suites:
- Unit tests for SHA256 implementation
- GPU detection and access tests
- Bigtable connectivity tests
- Hexadecimal formatting validation
- Container environment verification

## Architecture

The system follows a modular architecture:
1. **Hash Generation Layer**: Multiple implementations for different requirements
2. **GPU Acceleration Layer**: CUDA-based acceleration when available
3. **Storage Layer**: Bigtable integration for persistent storage
4. **Monitoring Layer**: Real-time metrics and performance tracking
5. **API Layer**: RESTful endpoints for external integration