# Testing Utilities Documentation

## Overview
Collection of testing and diagnostic utilities for validating system components, performance, and correctness.

---

## test_sha256.py

### Purpose
Comprehensive test suite for SHA256 implementation correctness.

### Test Cases
- **Known Vectors**: Tests against NIST standard test vectors
- **Edge Cases**: Empty input, large inputs, binary data
- **Performance**: Throughput and latency tests
- **Consistency**: CPU vs GPU implementation comparison

### Example Test Output
```
SHA256 Test Suite
=================
✓ Empty string hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
✓ 'abc' hash: ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad
✓ Large input (1MB): Passed
✓ Binary data: Passed
✓ GPU consistency: Matches CPU output

Performance Results:
- Single hash: 0.001ms
- 1000 hashes: 0.95ms
- Throughput: 1.05M hashes/sec
```

### Usage
```bash
python test_sha256.py
python test_sha256.py --verbose
python test_sha256.py --benchmark
```

---

## test_hex_format.py

### Purpose
Validates hexadecimal encoding/decoding and formatting.

### Test Coverage
- Hex string validation
- Case sensitivity handling
- Padding verification
- Character set validation
- Conversion accuracy

### Test Functions
- `test_hex_encoding()`: Validates byte to hex conversion
- `test_hex_decoding()`: Validates hex to byte conversion
- `test_format_consistency()`: Ensures formatting standards
- `test_invalid_inputs()`: Error handling for malformed hex

### Example Output
```
Hex Format Tests
================
✓ Encoding: b'hello' -> 68656c6c6f
✓ Decoding: 68656c6c6f -> b'hello'
✓ Uppercase handling: Passed
✓ Padding: Passed
✓ Invalid character detection: Passed

All hex format tests passed!
```

---

## test_push_hash.py

### Purpose
Tests hash upload functionality to monitoring server or storage backend.

### Test Scenarios
- Single hash upload
- Batch upload
- Network failure handling
- Retry mechanism
- Data integrity verification

### Configuration
```python
test_config = {
    "server_url": "http://localhost:5000",
    "batch_sizes": [1, 10, 100, 1000],
    "timeout": 30,
    "verify_storage": True
}
```

### Test Output
```
Hash Upload Tests
=================
Testing single upload... ✓
Testing batch (10)... ✓
Testing batch (100)... ✓
Testing batch (1000)... ✓
Testing network failure... ✓ (retry successful)
Testing data integrity... ✓

Upload Performance:
- Single: 5ms
- Batch (1000): 45ms
- Throughput: 22,222 uploads/sec
```

---

## test_gpu_access.py

### Purpose
Detailed GPU accessibility and functionality testing.

### Test Areas
- Device enumeration
- Memory allocation
- Kernel execution
- Data transfer
- Error conditions

### Test Functions
```python
def test_device_count()
def test_memory_allocation()
def test_kernel_execution()
def test_data_transfer()
def test_multi_gpu()
def test_error_handling()
```

### Output Example
```
GPU Access Tests
================
Device Count: 2 GPUs found ✓
Memory Allocation:
  - Device 0: 1GB allocated ✓
  - Device 1: 1GB allocated ✓
Kernel Execution:
  - Simple kernel: ✓
  - Complex kernel: ✓
Data Transfer:
  - Host to Device: 10GB/s ✓
  - Device to Host: 9.8GB/s ✓
Multi-GPU: Communication established ✓
Error Handling: All cases handled ✓
```

---

## diagnose_monitoring.py

### Purpose
Diagnoses issues with the monitoring system and provides troubleshooting information.

### Diagnostic Checks
- Network connectivity
- Server availability
- Authentication
- Data format validation
- Performance metrics

### Diagnostic Process
1. Check network connection
2. Verify server endpoint
3. Test authentication
4. Send test data
5. Verify data reception
6. Check response format

### Output Format
```
Monitoring System Diagnostics
=============================
[✓] Network connectivity: OK
[✓] Server reachable: http://monitoring.example.com
[✓] Authentication: Valid
[✓] Test data sent: Success
[✓] Data received: Confirmed
[✓] Response valid: JSON format OK

System Status: HEALTHY

Performance Metrics:
- Latency: 15ms
- Throughput: 1000 msg/sec
- Error rate: 0%
```

### Troubleshooting Guide
```
Common Issues:
--------------
[✗] Network connectivity: FAILED
  → Check internet connection
  → Verify firewall settings
  → Test DNS resolution

[✗] Server reachable: TIMEOUT
  → Verify server URL
  → Check server status
  → Test with curl/wget

[✗] Authentication: INVALID
  → Check API key
  → Verify credentials
  → Review permissions
```

---

## verify_binary_storage.py

### Purpose
Verifies binary data storage integrity in Bigtable.

### Verification Steps
1. Write test binary data
2. Read back and compare
3. Check data encoding
4. Verify compression (if used)
5. Test large binary objects

### Test Data Types
- Random binary data
- Structured binary (images, files)
- Edge cases (all zeros, all ones)
- Large objects (>1MB)

### Verification Output
```
Binary Storage Verification
===========================
Writing test data...
  - 1KB binary: ✓
  - 1MB binary: ✓
  - 10MB binary: ✓

Reading and verifying...
  - Data integrity: ✓
  - Encoding correct: ✓
  - Compression working: ✓

Performance:
  - Write speed: 50MB/s
  - Read speed: 100MB/s
  - Compression ratio: 2.5:1

Storage verification PASSED
```

---

## verify_inside_container.py

### Purpose
Verifies the execution environment when running inside a container.

### Environment Checks
- Container runtime detection
- Resource limits
- Network configuration
- Volume mounts
- Environment variables

### Container Information
```
Container Environment Check
===========================
Runtime: Docker ✓
Container ID: abc123def456
Image: hashgen:latest

Resources:
  - CPU Limit: 4 cores
  - Memory Limit: 8GB
  - GPU Access: Available (2 devices)

Network:
  - Hostname: hashgen-node-1
  - IP Address: 172.17.0.2
  - DNS: Working

Volumes:
  - /data: Mounted (RW)
  - /config: Mounted (RO)

Environment:
  - GCP_PROJECT_ID: Set ✓
  - CUDA_VISIBLE_DEVICES: 0,1 ✓
  - MONITORING_URL: Set ✓

Container environment: VERIFIED
```

### Usage Scenarios
- CI/CD pipelines
- Kubernetes deployments
- Docker Compose setups
- Development containers

---

## Running All Tests

### Test Suite Execution
```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest --cov=.

# Run specific category
python -m pytest tests/gpu/
python -m pytest tests/storage/
python -m pytest tests/network/

# Verbose output
python -m pytest -v

# Parallel execution
python -m pytest -n 4
```

### Test Report
```
Test Summary
============
GPU Tests: 15 passed
Storage Tests: 12 passed
Network Tests: 8 passed
Format Tests: 10 passed
Integration Tests: 5 passed

Total: 50 tests
Passed: 50
Failed: 0
Coverage: 92%
```