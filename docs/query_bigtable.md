# query_bigtable.py

## Overview
Utility script for querying and retrieving stored hashes from Google Cloud Bigtable. Provides various query patterns and data export capabilities.

## Functions

### query_by_hash(hash_value)
Retrieves the original input for a given SHA256 hash.

**Parameters:**
- `hash_value` (str): 64-character SHA256 hash

**Returns:**
- Original input value or None if not found

### query_recent(limit=100)
Retrieves the most recently stored hashes.

**Parameters:**
- `limit` (int): Maximum number of results

**Returns:**
- List of (hash, input) tuples

### query_range(start_hash, end_hash)
Retrieves hashes within a specific range.

**Parameters:**
- `start_hash` (str): Starting hash value
- `end_hash` (str): Ending hash value

**Returns:**
- List of hashes in range

### export_data(output_file, format='csv')
Exports hash data to file.

**Parameters:**
- `output_file` (str): Output file path
- `format` (str): Export format (csv, json, txt)

### get_statistics()
Retrieves statistics about stored hashes.

**Returns:**
- Dictionary with count, size, and distribution metrics

## Query Patterns

### Single Hash Lookup
```python
result = query_by_hash("abc123...")
print(f"Input for hash: {result}")
```

### Batch Lookup
```python
hashes = ["hash1", "hash2", "hash3"]
results = batch_query(hashes)
```

### Pattern Matching
```python
# Find hashes starting with specific prefix
results = query_prefix("00000")
```

### Time-based Queries
```python
# Get hashes from last hour
from datetime import datetime, timedelta
since = datetime.now() - timedelta(hours=1)
results = query_since(since)
```

## Command Line Usage

### Basic Query
```bash
python query_bigtable.py --hash abc123...
```

### Export Data
```bash
python query_bigtable.py --export hashes.csv --format csv
```

### Get Statistics
```bash
python query_bigtable.py --stats
```

### Recent Entries
```bash
python query_bigtable.py --recent 50
```

## Output Formats

### CSV Format
```csv
hash,input,timestamp
abc123...,input_value,2024-01-01T00:00:00
```

### JSON Format
```json
{
  "hashes": [
    {
      "hash": "abc123...",
      "input": "input_value",
      "timestamp": "2024-01-01T00:00:00"
    }
  ]
}
```

## Performance Considerations

### Query Optimization
- Use row key (hash) for fastest lookups
- Limit range scans to necessary data
- Batch queries for multiple lookups
- Use filters to reduce data transfer

### Caching
- Implements local cache for repeated queries
- Cache TTL configurable
- Memory-based for performance

## Error Handling

- Connection failures
- Query timeouts
- Invalid hash formats
- Permission errors

## Dependencies

- `google-cloud-bigtable`: Client library
- `pandas`: Data manipulation (optional)
- Valid GCP credentials