# test_bigtable.py

## Overview
Test suite for Google Cloud Bigtable connectivity and operations. This module verifies Bigtable setup, tests CRUD operations, and validates performance characteristics.

## Test Categories

### Connection Tests
- Client initialization
- Authentication validation
- Instance connectivity
- Table accessibility

### Operation Tests
- Write operations
- Read operations
- Batch operations
- Delete operations

### Performance Tests
- Throughput measurements
- Latency analysis
- Batch size optimization
- Concurrent access

## Test Functions

### test_connection()
Verifies Bigtable client can connect to the specified instance.

**Validates:**
- Project ID configuration
- Instance existence
- Authentication credentials
- Network connectivity

### test_write_operations()
Tests hash storage functionality.

**Tests:**
- Single row insertion
- Batch insertions
- Update operations
- Error handling

### test_read_operations()
Validates data retrieval capabilities.

**Tests:**
- Single row reads
- Range scans
- Filter applications
- Not found handling

### test_performance()
Measures Bigtable performance characteristics.

**Metrics:**
- Write throughput
- Read latency
- Batch efficiency
- Concurrent operations

## Configuration

### Test Environment
- Uses test instance/table if available
- Can run against production with care
- Cleans up test data after execution

### Environment Variables
- `GCP_PROJECT_ID`: Target project
- `BT_INSTANCE_ID`: Test instance
- `BT_TABLE_NAME`: Test table
- `TEST_MODE`: Enable test mode

## Usage

### Run All Tests
```bash
python test_bigtable.py
```

### Run Specific Test
```bash
python test_bigtable.py --test connection
python test_bigtable.py --test performance
```

### Verbose Mode
```bash
python test_bigtable.py --verbose
```

## Test Output

### Success Output
```
Testing Bigtable connection... ✓
Testing write operations... ✓
Testing read operations... ✓
Testing performance... ✓

All tests passed successfully!
Performance Summary:
- Write throughput: 10,000 ops/sec
- Read latency: 5ms average
- Batch efficiency: 95%
```

### Failure Output
```
Testing Bigtable connection... ✗
Error: Failed to connect to instance
Details: Authentication failed
```

## Error Scenarios

### Common Issues Tested
1. Invalid credentials
2. Non-existent instance
3. Table not found
4. Network timeouts
5. Quota exceeded
6. Permission denied

## Performance Benchmarks

### Expected Results
- Single write: < 10ms
- Batch write (1000): < 100ms
- Single read: < 5ms
- Range scan (1000): < 50ms

## Dependencies

- `google-cloud-bigtable`: Client library
- `pytest`: Test framework (optional)
- Valid GCP credentials
- Network access to Bigtable