#!/usr/bin/env python3
"""
Query script for BigTable hash storage
Usage:
    python query_bigtable.py --by-hash <hash_hex>
    python query_bigtable.py --by-input <input_text>
    python query_bigtable.py --scan [--limit N]
    python query_bigtable.py --count
"""

import os
import sys
import hashlib
import argparse
from google.cloud import bigtable
from google.cloud.bigtable import row_filters

# Set credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'

# Initialize client
project_id = 'adept-storm-466618-b4'
instance_id = 'hash-generator-instance'
table_id = 'hashes'

def init_table():
    """Initialize BigTable connection"""
    client = bigtable.Client(project=project_id, admin=True)
    instance = client.instance(instance_id)
    table = instance.table(table_id)
    return table

def query_by_hash(table, hash_hex):
    """Query by hash (row key)"""
    try:
        # Convert hex to binary
        hash_bytes = bytes.fromhex(hash_hex)
        if len(hash_bytes) != 32:
            print(f"Error: Hash must be 32 bytes (64 hex chars), got {len(hash_bytes)} bytes")
            return
        
        print(f"Querying for hash: {hash_hex}")
        
        # Read row directly by key
        row = table.read_row(hash_bytes)
        
        if row:
            input_value = row.cells['hash_data'][b'input'][0].value
            print(f"\nFound!")
            print(f"Hash (hex): {hash_hex}")
            print(f"Input (hex): {input_value.hex()}")
            print(f"Input (raw): {input_value}")
            try:
                print(f"Input (text): {input_value.decode('utf-8')}")
            except:
                print(f"Input (text): [binary data, cannot decode as UTF-8]")
        else:
            print(f"No entry found for hash: {hash_hex}")
            
    except Exception as e:
        print(f"Error: {e}")

def query_by_input(table, input_text):
    """Query by input value (requires computing hash first)"""
    try:
        # Convert input to bytes
        if input_text.startswith('0x'):
            # Hex input
            input_bytes = bytes.fromhex(input_text[2:])
        else:
            # Text input
            input_bytes = input_text.encode('utf-8')
        
        # Compute hash
        hash_bytes = hashlib.sha256(input_bytes).digest()
        
        print(f"Input: {input_text}")
        print(f"Input (hex): {input_bytes.hex()}")
        print(f"Computed hash: {hash_bytes.hex()}")
        
        # Query by hash
        row = table.read_row(hash_bytes)
        
        if row:
            stored_input = row.cells['hash_data'][b'input'][0].value
            print(f"\nFound in BigTable!")
            print(f"Stored input matches: {stored_input == input_bytes}")
        else:
            print(f"\nNot found in BigTable")
            
    except Exception as e:
        print(f"Error: {e}")

def scan_table(table, limit=10):
    """Scan and display rows from the table"""
    try:
        print(f"Scanning table (limit: {limit})...")
        print("-" * 80)
        
        count = 0
        for row in table.read_rows(limit=limit):
            count += 1
            hash_hex = row.row_key.hex()
            input_value = row.cells['hash_data'][b'input'][0].value
            
            print(f"Row {count}:")
            print(f"  Hash (key): {hash_hex}")
            print(f"  Input (hex): {input_value.hex()}")
            
            # Try to decode as text
            try:
                if len(input_value) < 100:  # Only try for reasonable sizes
                    text = input_value.decode('utf-8')
                    if text.isprintable():
                        print(f"  Input (text): {text}")
            except:
                pass
            
            print()
        
        print(f"Displayed {count} rows")
        
    except Exception as e:
        print(f"Error: {e}")

def count_rows(table):
    """Count total rows in the table"""
    try:
        print("Counting rows in table...")
        
        # Use a filter that passes everything but only returns row keys
        filter_ = row_filters.StripValueTransformerFilter(True)
        
        count = 0
        for row in table.read_rows(filter_=filter_):
            count += 1
            if count % 100000 == 0:
                print(f"  Counted {count} rows so far...")
        
        print(f"\nTotal rows: {count:,}")
        
    except Exception as e:
        print(f"Error: {e}")

def main():
    parser = argparse.ArgumentParser(description='Query BigTable hash storage')
    parser.add_argument('--by-hash', help='Query by hash (hex format)')
    parser.add_argument('--by-input', help='Query by input value (text or 0x... for hex)')
    parser.add_argument('--scan', action='store_true', help='Scan and display rows')
    parser.add_argument('--count', action='store_true', help='Count total rows')
    parser.add_argument('--limit', type=int, default=10, help='Limit for scan operation (default: 10)')
    
    args = parser.parse_args()
    
    # Initialize table
    table = init_table()
    
    # Execute requested operation
    if args.by_hash:
        query_by_hash(table, args.by_hash)
    elif args.by_input:
        query_by_input(table, args.by_input)
    elif args.scan:
        scan_table(table, args.limit)
    elif args.count:
        count_rows(table)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()