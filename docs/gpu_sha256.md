# gpu_sha256.py

## Overview
GPU-accelerated SHA256 implementation using CUDA and CuPy. This module provides high-performance hash computation leveraging NVIDIA GPUs for massive parallel processing.

## Key Components

### GPU Detection and Initialization
- Automatic CUDA availability checking
- GPU device enumeration and selection
- Graceful fallback to CPU mode
- Memory allocation optimization

### Batch Processing
- Efficient batch hash computation
- Memory transfer optimization
- Parallel kernel execution
- Result aggregation

## Features

### Performance Optimization
- Batch processing to minimize memory transfers
- Kernel optimization for SHA256 algorithm
- Multi-GPU support for scaling
- Asynchronous execution

### Hardware Support
- NVIDIA CUDA-capable GPUs
- Automatic device selection
- Memory management
- Temperature monitoring

## Functions and Classes

### GPU Initialization
Handles GPU device setup and capability checking.

**Process:**
1. Check CUDA availability
2. Enumerate available devices
3. Test device accessibility
4. Initialize CuPy context

### Hash Computation
Performs SHA256 calculation on GPU.

**Parameters:**
- Input data arrays
- Batch size configuration
- Device selection

**Returns:**
- Computed hash values
- Performance metrics

## Configuration

### Environment Variables
- `CUDA_VISIBLE_DEVICES`: Select specific GPU devices
- `CUDA_DEVICE_ORDER`: GPU enumeration order

### Performance Tuning
- Batch size optimization based on GPU memory
- Thread block configuration
- Memory pool settings

## Usage Example

```python
import gpu_sha256

# Initialize GPU hasher
hasher = gpu_sha256.GPUHasher(device_id=0)

# Prepare input data
inputs = [b"data1", b"data2", b"data3"]

# Compute hashes
hashes = hasher.compute_batch(inputs)
```

## Performance Characteristics

### GPU Performance
- Throughput: 1M+ hashes/second (RTX 3090)
- Memory usage: Scales with batch size
- Latency: ~10ms for 10K batch

### Comparison with CPU
- 10-100x faster than CPU implementation
- Better energy efficiency
- Scales with GPU cores

## Error Handling

- CUDA initialization failures
- Out of memory conditions
- Device availability checks
- Fallback mechanisms

## Dependencies

- `cupy`: CUDA Python bindings
- `numpy`: Array operations
- NVIDIA CUDA Toolkit
- Compatible GPU drivers