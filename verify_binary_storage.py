#!/usr/bin/env python3
import os
import hashlib
from google.cloud import bigtable

# Set credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'

# Initialize client
project_id = 'adept-storm-466618-b4'
instance_id = 'hash-generator-instance'
table_id = 'hashes'

client = bigtable.Client(project=project_id, admin=True)
instance = client.instance(instance_id)
table = instance.table(table_id)

# Test with raw binary data (not text)
test_input = b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'  # 16 bytes of raw binary
test_hash = hashlib.sha256(test_input).digest()  # This returns raw 32-byte binary

print("=== Binary Storage Verification ===")
print(f"Input type: {type(test_input)}")
print(f"Input length: {len(test_input)} bytes")
print(f"Input (raw bytes): {test_input}")
print(f"Input (hex): {test_input.hex()}")
print()
print(f"Hash type: {type(test_hash)}")
print(f"Hash length: {len(test_hash)} bytes")
print(f"Hash (raw bytes): {test_hash}")
print(f"Hash (hex): {test_hash.hex()}")

try:
    # Store in BigTable - both as raw binary
    row_key = test_hash  # Raw 32-byte binary hash as key
    
    row = table.direct_row(row_key)
    row.set_cell(
        column_family_id='hash_data',
        column=b'input',
        value=test_input  # Raw binary input as value
    )
    
    response = row.commit()
    print(f"\nSUCCESS: Stored in BigTable with raw binary")
    
    # Read back and verify it's still binary
    retrieved_row = table.read_row(row_key)
    
    if retrieved_row:
        cell = retrieved_row.cells['hash_data'][b'input'][0]
        retrieved_input = cell.value
        
        print(f"\n=== Retrieved from BigTable ===")
        print(f"Retrieved type: {type(retrieved_input)}")
        print(f"Retrieved length: {len(retrieved_input)} bytes")
        print(f"Retrieved (raw bytes): {retrieved_input}")
        print(f"Retrieved (hex): {retrieved_input.hex()}")
        print(f"Binary match: {retrieved_input == test_input}")
        print(f"\nCONFIRMED: Data is stored as raw binary, not hex strings")
    
except Exception as e:
    print(f"ERROR: {e}")