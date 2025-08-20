#!/usr/bin/env python3
"""Test GPU access in container"""

import os
import sys

print("=" * 60)
print("GPU ACCESS TEST")
print("=" * 60)

# Check environment variables
print("\n1. Environment Variables:")
print(f"CUDA_VISIBLE_DEVICES: {os.environ.get('CUDA_VISIBLE_DEVICES', 'Not set')}")
print(f"NVIDIA_VISIBLE_DEVICES: {os.environ.get('NVIDIA_VISIBLE_DEVICES', 'Not set')}")
print(f"CUDA_VERSION: {os.environ.get('CUDA_VERSION', 'Not set')}")

# Check nvidia-smi
print("\n2. NVIDIA-SMI Output:")
os.system("nvidia-smi --list-gpus 2>/dev/null || echo 'nvidia-smi not available'")

# Try CuPy
print("\n3. CuPy GPU Detection:")
try:
    import cupy as cp
    
    # Method 1: getDeviceCount
    try:
        count = cp.cuda.runtime.getDeviceCount()
        print(f"getDeviceCount: {count} GPUs")
    except Exception as e:
        print(f"getDeviceCount failed: {e}")
    
    # Method 2: Try each device
    print("\nTesting each GPU:")
    accessible = []
    for i in range(8):
        try:
            with cp.cuda.Device(i):
                mem = cp.cuda.runtime.memGetInfo()
                accessible.append(i)
                print(f"  GPU {i}: ✓ Accessible (Memory: {mem[1]//1024//1024} MB)")
        except Exception as e:
            print(f"  GPU {i}: ✗ {str(e)[:50]}")
    
    print(f"\nAccessible GPUs: {accessible}")
    
    # Test actual computation
    if accessible:
        print(f"\n4. Testing computation on GPU {accessible[0]}:")
        try:
            with cp.cuda.Device(accessible[0]):
                a = cp.array([1, 2, 3])
                b = cp.array([4, 5, 6])
                c = a + b
                print(f"  Computation test: {a.get()} + {b.get()} = {c.get()}")
                print("  ✓ GPU computation working!")
        except Exception as e:
            print(f"  ✗ Computation failed: {e}")
    
except ImportError:
    print("CuPy not installed")
except Exception as e:
    print(f"CuPy error: {e}")

print("\n" + "=" * 60)