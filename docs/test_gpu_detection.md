# test_gpu_detection.py

## Overview
Comprehensive GPU detection and capability testing utility. This script identifies available NVIDIA GPUs, tests their accessibility, and reports detailed hardware information.

## Test Functions

### detect_gpus()
Enumerates all available CUDA-capable GPUs.

**Returns:**
- List of GPU devices with properties
- Device IDs and names
- Compute capabilities

### test_gpu_access(device_id)
Tests if a specific GPU is accessible and functional.

**Parameters:**
- `device_id` (int): GPU device index

**Returns:**
- Success/failure status
- Error details if failed

### get_gpu_properties(device_id)
Retrieves detailed GPU specifications.

**Parameters:**
- `device_id` (int): GPU device index

**Returns:**
- Dictionary of GPU properties:
  - Name and model
  - Memory (total/free)
  - Compute capability
  - Clock speeds
  - Temperature
  - Power limits

### benchmark_gpu(device_id)
Performs basic performance benchmark.

**Parameters:**
- `device_id` (int): GPU device index

**Returns:**
- Performance metrics:
  - Memory bandwidth
  - Compute throughput
  - Hash rate estimate

## Output Information

### Device Summary
```
GPU Detection Report
====================
Found 2 CUDA devices:

Device 0: NVIDIA GeForce RTX 3090
  - Compute Capability: 8.6
  - Memory: 24GB (23GB free)
  - Temperature: 45°C
  - Status: ✓ Accessible

Device 1: NVIDIA GeForce RTX 3080
  - Compute Capability: 8.6
  - Memory: 10GB (9GB free)
  - Temperature: 42°C
  - Status: ✓ Accessible
```

### Performance Results
```
Performance Benchmark Results
============================
Device 0 (RTX 3090):
  - Memory Bandwidth: 936 GB/s
  - FP32 Performance: 35.6 TFLOPS
  - Hash Rate: ~1.2M hashes/sec

Device 1 (RTX 3080):
  - Memory Bandwidth: 760 GB/s
  - FP32 Performance: 29.8 TFLOPS
  - Hash Rate: ~1.0M hashes/sec
```

## Command Line Usage

### Basic Detection
```bash
python test_gpu_detection.py
```

### Specific Device Test
```bash
python test_gpu_detection.py --device 0
```

### Verbose Mode
```bash
python test_gpu_detection.py --verbose
```

### Benchmark Mode
```bash
python test_gpu_detection.py --benchmark
```

## Error Scenarios

### No GPUs Found
```
No CUDA-capable GPUs detected.
Possible reasons:
- No NVIDIA GPU installed
- CUDA drivers not installed
- GPU not visible to system
```

### GPU Access Denied
```
GPU 0 detected but not accessible.
Error: CUDA_ERROR_NO_DEVICE
Check CUDA_VISIBLE_DEVICES environment variable
```

## Environment Checks

### Driver Version
- Checks NVIDIA driver version
- Verifies CUDA toolkit compatibility
- Reports version mismatches

### CUDA Configuration
- CUDA_VISIBLE_DEVICES setting
- CUDA_DEVICE_ORDER configuration
- Memory allocation mode

## Dependencies

- `cupy` or `pycuda`: CUDA Python bindings
- NVIDIA drivers (>= 450.0)
- CUDA Toolkit (>= 11.0)
- `nvidia-ml-py`: NVIDIA Management Library