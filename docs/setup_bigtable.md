# setup_bigtable.py

## Overview
Setup script to create and configure Google Cloud Bigtable resources for hash storage. This script handles the creation of Bigtable instances, clusters, and tables with appropriate schema for efficient hash storage and retrieval.

## Functions

### create_bigtable_resources(project_id, instance_id, table_name, recreate_table=False)
Creates or validates Bigtable instance and table with appropriate schema.

**Parameters:**
- `project_id` (str): Google Cloud Project ID
- `instance_id` (str): Bigtable instance identifier
- `table_name` (str): Name of the table to create
- `recreate_table` (bool): Whether to recreate existing table

**Returns:**
- `bool`: True if setup successful

**Process:**
1. Creates Bigtable client with admin privileges
2. Checks if instance exists, creates if needed
3. Configures production-ready cluster with SSD storage
4. Creates table with optimized column family
5. Sets up garbage collection rules

### main()
Main setup function that orchestrates the Bigtable resource creation.

**Process:**
1. Reads configuration from environment variables
2. Validates required settings
3. Handles command-line arguments
4. Executes resource creation
5. Reports setup status

## Configuration

### Instance Configuration
- **Cluster ID**: `cluster-main`
- **Location**: `us-central1-a`
- **Nodes**: 3 (minimum for production)
- **Storage Type**: SSD for high performance

### Table Schema
- **Row Key**: SHA256 hash (64 characters)
  - Provides fast lookups
  - Ensures even distribution
- **Column Family**: `hash_data`
  - `input`: Original input value that generated the hash
  - Max versions: 1 (garbage collection rule)

## Environment Variables

- `GCP_PROJECT_ID`: Google Cloud project identifier
  - Default: `adept-storm-466618-b4`
- `BT_INSTANCE_ID`: Bigtable instance name
  - Default: `hash-generator-instance`
- `BT_TABLE_NAME`: Table name for hash storage
  - Default: `hashes`

## Command Line Arguments

### --recreate-table
Forces recreation of existing table. Use with caution as this will delete all existing data.

```bash
python setup_bigtable.py --recreate-table
```

## Usage Examples

### Basic Setup
```bash
# Set environment variables
export GCP_PROJECT_ID="your-project-id"
export BT_INSTANCE_ID="hash-instance"
export BT_TABLE_NAME="hash-table"

# Run setup
python setup_bigtable.py
```

### Recreate Table
```bash
# Force table recreation (deletes existing data)
python setup_bigtable.py --recreate-table
```

## Error Handling

- Validates project ID is set and not default
- Checks for existing resources before creation
- Provides detailed error messages
- Returns appropriate exit codes

## Output

The script provides detailed console output:
- Configuration being used
- Creation status for each resource
- Final schema description
- Success/failure messages

Example output:
```
Setting up BigTable resources...
Project: your-project-id
Instance: hash-generator-instance
Table: hashes
Instance hash-generator-instance already exists
Creating table hashes...
Table hashes created with column family 'hash_data'

Setup completed successfully!

Table schema:
  Row Key: SHA256 hash (for fast lookups)
  Column Family: hash_data
    - input: The original input value
```

## Production Considerations

### Scaling
- Instance configured with 3 nodes (minimum for production)
- Can be scaled up through Cloud Console or API
- SSD storage provides consistent low latency

### Cost Optimization
- Node count affects hourly billing
- Consider development instances with 1 node for testing
- Use HDD storage for cost-sensitive, low-performance requirements

### Security
- Requires appropriate IAM permissions
- Service account needs Bigtable Admin role for setup
- Consider using separate service accounts for setup vs runtime

## Dependencies

- `google-cloud-bigtable`: Bigtable client library
- Valid Google Cloud credentials
- Appropriate IAM permissions

## Troubleshooting

### Common Issues

1. **Authentication Error**
   - Ensure GOOGLE_APPLICATION_CREDENTIALS is set
   - Verify service account has Bigtable Admin role

2. **Instance Creation Fails**
   - Check project quota for Bigtable instances
   - Verify billing is enabled

3. **Table Already Exists**
   - Use `--recreate-table` flag to force recreation
   - Or manually delete through Cloud Console