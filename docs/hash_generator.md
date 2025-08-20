# hash_generator.py

## Overview
Main asynchronous SHA256 hash generator with GPU support and BigTable integration. This is the primary implementation that combines all features including GPU acceleration, cloud storage, and monitoring.

## Key Components

### GPUHasher Class
Batch SHA256 hasher for GPU/CPU processing.

**Attributes:**
- `device_id`: GPU device identifier (-1 for CPU mode)
- `batch_size`: Number of hashes to process in a single batch (default: 10000)

**Methods:**
- `__init__(device_id, batch_size)`: Initialize hasher with specific GPU device
- `hash_batch(inputs)`: Process a batch of inputs and return SHA256 hashes

### AsyncHashGenerator Class
Main asynchronous hash generation engine.

**Attributes:**
- `bigtable_client`: Google Cloud Bigtable client instance
- `table`: Bigtable table reference for hash storage
- `instance_id`: Unique identifier for this generator instance
- `total_hashes`: Counter for total hashes generated
- `start_time`: Timestamp when generation started
- `recent_hashes`: Queue for calculating recent hashrate
- `gpu_count`: Number of available GPUs
- `hashers`: List of GPUHasher instances
- `executor`: Thread pool for parallel processing
- `monitoring_url`: URL for sending monitoring data

**Methods:**
- `__init__()`: Initialize generator with Bigtable connection
- `generate_hash_async(input_data)`: Generate single SHA256 hash
- `generate_batch_async(batch_size)`: Generate batch of hashes
- `store_hash_async(hash_value, input_value)`: Store hash in Bigtable
- `send_monitoring_data()`: Send performance metrics to monitoring server
- `run()`: Main execution loop

## Features

### GPU Acceleration
- Automatic detection of CUDA-capable GPUs
- Fallback to CPU when GPU unavailable
- Multi-GPU support with load distribution
- Batch processing for improved throughput

### Cloud Storage
- Integration with Google Cloud Bigtable
- Asynchronous storage operations
- SHA256 hash used as row key for fast lookups
- Automatic retry on storage failures

### Monitoring
- Real-time hashrate calculation
- Overall and recent hashrate metrics
- GPU utilization tracking
- Periodic reporting to monitoring server

## Configuration

### Environment Variables
- `GCP_PROJECT_ID`: Google Cloud project identifier
- `BT_INSTANCE_ID`: Bigtable instance name
- `BT_TABLE_NAME`: Table name for hash storage
- `MONITORING_URL`: Endpoint for monitoring data
- `INSTANCE_ID`: Unique identifier for this generator
- `CUDA_VISIBLE_DEVICES`: GPU device selection

### Default Values
- Batch size: 10000 hashes
- Monitoring interval: 10 seconds
- Worker threads: 4
- Queue size: 100000

## Usage Example

```python
import asyncio
from hash_generator import AsyncHashGenerator

async def main():
    generator = AsyncHashGenerator()
    await generator.run()

if __name__ == "__main__":
    asyncio.run(main())
```

## Performance Characteristics

### CPU Mode
- Throughput: ~50,000 hashes/second (varies by CPU)
- Memory usage: ~100MB base + batch buffer
- Scales with CPU cores

### GPU Mode
- Throughput: ~500,000+ hashes/second (varies by GPU)
- Memory usage: ~500MB including GPU buffers
- Scales with GPU count and capabilities

## Error Handling

- Graceful fallback from GPU to CPU on initialization failure
- Automatic retry for Bigtable operations
- Continuous operation despite storage failures
- Comprehensive logging for debugging

## Dependencies

- `asyncio`: Asynchronous operations
- `hashlib`: SHA256 computation
- `cupy`: GPU acceleration (optional)
- `google.cloud.bigtable`: Cloud storage
- `aiohttp`: HTTP client for monitoring
- `numpy`: Numerical operations
- `concurrent.futures`: Thread pool execution