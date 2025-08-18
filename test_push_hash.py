#!/usr/bin/env python3
import os
import hashlib
from google.cloud import bigtable
from google.cloud.bigtable.row import DirectRow

# Set credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'

# Initialize client
project_id = 'adept-storm-466618-b4'
instance_id = 'hash-generator-instance'
table_id = 'hashes'

client = bigtable.Client(project=project_id, admin=True)
instance = client.instance(instance_id)
table = instance.table(table_id)

# Test data
test_input = b'test_input_12345'
test_hash = hashlib.sha256(test_input).digest()

print(f"Test Input (hex): {test_input.hex()}")
print(f"SHA256 Hash (hex): {test_hash.hex()}")
print(f"Input length: {len(test_input)} bytes")
print(f"Hash length: {len(test_hash)} bytes")

try:
    # Use hash as row key
    row_key = test_hash
    
    # Create row
    row = table.direct_row(row_key)
    row.set_cell(
        column_family_id='hash_data',
        column=b'input',
        value=test_input
    )
    
    # Commit the row
    response = row.commit()
    print(f"\nSUCCESS: Test hash pushed to BigTable!")
    print(f"Row key (hash): {row_key.hex()}")
    
    # Read it back to verify
    print("\nReading back from BigTable...")
    retrieved_row = table.read_row(row_key)
    
    if retrieved_row:
        # Get the input value from the hash_data column family
        cell = retrieved_row.cells['hash_data'][b'input'][0]
        retrieved_input = cell.value
        
        print(f"SUCCESS: Row retrieved from BigTable")
        print(f"Retrieved input (hex): {retrieved_input.hex()}")
        print(f"Retrieved input (text): {retrieved_input.decode('utf-8', errors='ignore')}")
        print(f"Match: {retrieved_input == test_input}")
    else:
        print("ERROR: Could not retrieve row from BigTable")
    
except Exception as e:
    print(f"ERROR: {e}")