#!/usr/bin/env python3
"""Test SHA256 to see why all hashes start with 0x0700"""

import hashlib
import secrets

# Test standard SHA256
for i in range(10):
    # Generate random 32 bytes -> 64 hex chars
    random_bytes = secrets.token_bytes(32)
    hex_string = random_bytes.hex().lower()
    
    # Hash the hex string
    hash_result = hashlib.sha256(hex_string.encode('utf-8')).digest()
    hash_hex = hash_result.hex()
    
    print(f"Input: {hex_string[:16]}...")
    print(f"Hash:  {hash_hex}")
    print(f"First bytes: {hash_result[:4].hex()}")
    print()

# Test with actual bytes instead of hex string
print("\n--- Testing with raw bytes ---")
for i in range(5):
    random_bytes = secrets.token_bytes(32)
    hash_result = hashlib.sha256(random_bytes).digest()
    hash_hex = hash_result.hex()
    
    print(f"Hash: {hash_hex}")
    print(f"First bytes: {hash_result[:4].hex()}")