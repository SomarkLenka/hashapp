#!/usr/bin/env python3
import os
from google.cloud import bigtable
from google.cloud.bigtable import column_family, row_filters

# Set credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'

# Initialize client
project_id = 'adept-storm-466618-b4'
instance_id = 'hash-generator-instance'
table_id = 'hashes'

client = bigtable.Client(project=project_id, admin=True)
instance = client.instance(instance_id)
table = instance.table(table_id)

try:
    # Test write
    row_key = b'test_row_123'
    row = table.direct_row(row_key)
    row.set_cell('hash_data', 'sha256', 'test_hash_value')
    row.set_cell('hash_data', 'input', 'test_input')
    
    response = row.commit()
    print(f"SUCCESS: Test row written to BigTable!")
    print(f"Row key: {row_key}")
    
    # Try to read it back
    row = table.read_row(row_key)
    if row:
        print(f"Verified: Row successfully read back from BigTable")
    
except Exception as e:
    print(f"ERROR: {e}")