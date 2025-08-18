#!/usr/bin/env python3
"""
Diagnostic script for monitoring endpoint issues
"""
import asyncio
import aiohttp
import json
import time

async def test_monitoring_endpoint():
    """Test the monitoring endpoint"""
    endpoint = "https://hash-production-3375.up.railway.app/api/hashrate"
    
    # Test data similar to what the hash generator sends
    test_data = {
        'instance_id': 'test_diagnostic_12345',
        'hashrate': 1000.0,
        'total_hashes': 5000,
        'runtime': 60.0,
        'timestamp': time.time()
    }
    
    print(f"Testing monitoring endpoint: {endpoint}")
    print(f"Sending test data: {json.dumps(test_data, indent=2)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint,
                json=test_data,
                timeout=aiohttp.ClientTimeout(total=10),
                headers={'Content-Type': 'application/json'}
            ) as response:
                status = response.status
                text = await response.text()
                
                print(f"\nResponse Status: {status}")
                print(f"Response Headers: {dict(response.headers)}")
                print(f"Response Body: {text}")
                
                if status == 200:
                    print("\n✓ Monitoring endpoint is working correctly")
                else:
                    print(f"\n✗ Unexpected status code: {status}")
                    
    except aiohttp.ClientError as e:
        print(f"\n✗ Connection error: {e}")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")

async def test_wrong_endpoint():
    """Test if the server is misconfigured"""
    # Test if the server might be trying to connect back
    print("\n" + "="*60)
    print("Testing if server expects a different endpoint...")
    
    # Try the base URL without /api/hashrate
    base_url = "https://hash-production-3375.up.railway.app/"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                base_url,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                status = response.status
                print(f"Base URL ({base_url}) status: {status}")
                
                if status == 200:
                    text = await response.text()
                    print(f"Response preview: {text[:200]}...")
    except Exception as e:
        print(f"Base URL error: {e}")

async def main():
    print("Monitoring Endpoint Diagnostic Tool")
    print("="*60)
    
    await test_monitoring_endpoint()
    await test_wrong_endpoint()
    
    print("\n" + "="*60)
    print("Diagnosis complete.")
    print("\nIf you're seeing SSH errors on VastAI, it means:")
    print("1. The web server is trying to connect TO your container (wrong direction)")
    print("2. The web server should only receive POST requests FROM your container")
    print("3. Check if the web server has any webhook or callback configuration")
    print("4. The container should not expose port 22 or accept incoming HTTP on port 22")

if __name__ == '__main__':
    asyncio.run(main())