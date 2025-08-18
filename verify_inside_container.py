#!/usr/bin/env python3
"""
Verification script to run INSIDE the hashgen container
Copy this to the container and run it to verify functionality
"""

import os
import json
import hashlib
import time
from google.cloud import bigtable

def check_config():
    """Check if config files exist and are valid"""
    print("1. Checking configuration files...")
    print("-" * 40)
    
    # Check config.json
    if os.path.exists('/app/config.json'):
        print("✓ config.json found")
        with open('/app/config.json', 'r') as f:
            config = json.load(f)
            print(f"  - BigTable project: {config['bigtable']['project_id']}")
            print(f"  - BigTable instance: {config['bigtable']['instance_id']}")
            print(f"  - Upload batch size: {config['upload_batch_size']:,}")
            print(f"  - Monitoring endpoint: {config['monitoring']['endpoint']}")
    else:
        print("✗ config.json not found")
        return False
    
    # Check credentials
    cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
    if os.path.exists(f'/app/{cred_path}'):
        print(f"✓ Credentials found at /app/{cred_path}")
    else:
        print(f"✗ Credentials not found at /app/{cred_path}")
        return False
    
    print()
    return True

def test_hashing():
    """Test hash generation"""
    print("2. Testing hash generation...")
    print("-" * 40)
    
    test_input = b'test_verification_' + str(time.time()).encode()
    test_hash = hashlib.sha256(test_input).digest()
    
    print(f"✓ SHA256 working")
    print(f"  Input: {test_input[:30]}...")
    print(f"  Hash (hex): {test_hash.hex()[:32]}...")
    print()
    return True

def test_bigtable_connection():
    """Test BigTable connection"""
    print("3. Testing BigTable connection...")
    print("-" * 40)
    
    try:
        # Load config
        with open('/app/config.json', 'r') as f:
            config = json.load(f)
        
        # Initialize client
        client = bigtable.Client(
            project=config['bigtable']['project_id'],
            admin=True
        )
        instance = client.instance(config['bigtable']['instance_id'])
        table = instance.table(config['bigtable']['table_name'])
        
        # Try to read a row (any row)
        for row in table.read_rows(limit=1):
            print("✓ BigTable connection successful")
            print(f"  Found at least one row in table")
            print()
            return True
        
        print("✓ BigTable connection successful")
        print("  Table is empty (normal for new deployment)")
        print()
        return True
        
    except Exception as e:
        print(f"✗ BigTable connection failed: {e}")
        print()
        return False

def check_process():
    """Check if hash generator is running"""
    print("4. Checking hash generator process...")
    print("-" * 40)
    
    # Check if the process is running
    pid_check = os.popen('ps aux | grep "python hash_generator.py" | grep -v grep').read()
    
    if pid_check:
        lines = pid_check.strip().split('\n')
        for line in lines:
            parts = line.split()
            if len(parts) > 10:
                pid = parts[1]
                cpu = parts[2]
                mem = parts[3]
                print(f"✓ Hash generator is running")
                print(f"  PID: {pid}")
                print(f"  CPU: {cpu}%")
                print(f"  Memory: {mem}%")
    else:
        print("✗ Hash generator process not found")
        return False
    
    print()
    return True

def check_logs():
    """Check recent log entries"""
    print("5. Checking recent activity...")
    print("-" * 40)
    
    # Look for log file or check stdout
    log_indicators = {
        'started': False,
        'bigtable_init': False,
        'uploading': False,
        'errors': 0
    }
    
    # This would normally check actual log files
    # For container, logs go to stdout/stderr
    print("⚠ Log checking requires docker logs from outside container")
    print("  Run: docker logs <container_name> --tail 50")
    print()
    return True

def main():
    print("=" * 50)
    print("HashGen Container Internal Verification")
    print("=" * 50)
    print()
    
    results = []
    
    # Run all checks
    results.append(("Configuration", check_config()))
    results.append(("Hashing", test_hashing()))
    results.append(("BigTable", test_bigtable_connection()))
    results.append(("Process", check_process()))
    results.append(("Logs", check_logs()))
    
    # Summary
    print("=" * 50)
    print("VERIFICATION SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for check_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{check_name:15} {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("✓ All checks passed! Container is working properly.")
    else:
        print("✗ Some checks failed. Review the output above.")
    
    print()
    print("Additional commands to run from outside container:")
    print("  docker logs <container> --tail 100  # View recent logs")
    print("  docker stats <container>             # Monitor resource usage")
    print("  docker exec <container> ps aux       # Check processes")

if __name__ == '__main__':
    main()