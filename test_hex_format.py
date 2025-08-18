#!/usr/bin/env python3
"""
Test script to verify hex string format
"""

import hashlib
import secrets

def test_hex_generation():
    """Test that we're generating proper 64-char hex strings"""
    
    # Generate a sample input like our generator does
    random_bytes = secrets.token_bytes(32)
    hex_string = random_bytes.hex().upper()
    
    print(f"Random bytes (32 bytes): {len(random_bytes)} bytes")
    print(f"Hex string: {hex_string}")
    print(f"Hex string length: {len(hex_string)} characters")
    print(f"All valid hex chars: {all(c in '0123456789ABCDEF' for c in hex_string)}")
    
    # Hash the hex string (as bytes)
    hex_bytes = hex_string.encode('utf-8')
    hash_result = hashlib.sha256(hex_bytes).digest()
    
    print(f"\nInput to SHA256: '{hex_string}'")
    print(f"Input as bytes: {hex_bytes[:20]}... ({len(hex_bytes)} bytes)")
    print(f"SHA256 hash: {hash_result.hex()}")
    
    # Verify format
    assert len(hex_string) == 64, f"Expected 64 chars, got {len(hex_string)}"
    assert all(c in '0123456789ABCDEF' for c in hex_string), "Invalid hex characters"
    
    print("\nFormat verification passed!")
    
    # Show a few examples
    print("\nExample inputs (64-char hex strings):")
    for i in range(5):
        example = secrets.token_bytes(32).hex().upper()
        print(f"  {i+1}. {example}")
        
if __name__ == "__main__":
    test_hex_generation()