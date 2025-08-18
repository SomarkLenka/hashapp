#!/usr/bin/env python3
"""
Test GPU detection and CUDA availability
"""

import subprocess
import sys

print("=" * 60)
print("GPU Detection Test")
print("=" * 60)

# Test 1: Check nvidia-smi
print("\n1. Checking nvidia-smi...")
try:
    result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ nvidia-smi found")
        # Parse GPU info
        lines = result.stdout.split('\n')
        for line in lines:
            if 'NVIDIA' in line or 'GPU' in line:
                print(f"  {line.strip()}")
    else:
        print("✗ nvidia-smi not found or failed")
except FileNotFoundError:
    print("✗ nvidia-smi command not found")
except Exception as e:
    print(f"✗ Error running nvidia-smi: {e}")

# Test 2: Check PyTorch CUDA
print("\n2. Checking PyTorch CUDA...")
try:
    import torch
    print(f"✓ PyTorch version: {torch.__version__}")
    print(f"✓ CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"✓ CUDA version: {torch.version.cuda}")
        print(f"✓ GPU count: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
            props = torch.cuda.get_device_properties(i)
            print(f"    Memory: {props.total_memory / 1024**3:.1f} GB")
    else:
        print("✗ CUDA not available in PyTorch")
except ImportError:
    print("✗ PyTorch not installed")
except Exception as e:
    print(f"✗ Error with PyTorch: {e}")

# Test 3: Check CuPy
print("\n3. Checking CuPy...")
try:
    import cupy as cp
    print(f"✓ CuPy version: {cp.__version__}")
    print(f"✓ CUDA available: {cp.cuda.is_available()}")
    if cp.cuda.is_available():
        gpu_count = cp.cuda.runtime.getDeviceCount()
        print(f"✓ GPU count: {gpu_count}")
        for i in range(gpu_count):
            with cp.cuda.Device(i):
                props = cp.cuda.runtime.getDeviceProperties(i)
                print(f"  GPU {i}: {props['name'].decode()}")
                print(f"    Memory: {props['totalGlobalMem'] / 1024**3:.1f} GB")
except ImportError:
    print("✗ CuPy not installed")
except Exception as e:
    print(f"✗ Error with CuPy: {e}")

# Test 4: Check PyCUDA
print("\n4. Checking PyCUDA...")
try:
    import pycuda.driver as cuda_driver
    import pycuda.autoinit
    print("✓ PyCUDA imported")
    gpu_count = cuda_driver.Device.count()
    print(f"✓ GPU count: {gpu_count}")
    for i in range(gpu_count):
        device = cuda_driver.Device(i)
        print(f"  GPU {i}: {device.name()}")
        attrs = device.get_attributes()
        mem = device.total_memory() / 1024**3
        print(f"    Memory: {mem:.1f} GB")
except ImportError:
    print("✗ PyCUDA not installed")
except Exception as e:
    print(f"✗ Error with PyCUDA: {e}")

# Test 5: Check Numba CUDA
print("\n5. Checking Numba CUDA...")
try:
    from numba import cuda
    print("✓ Numba CUDA imported")
    if cuda.is_available():
        print("✓ CUDA available in Numba")
        gpus = cuda.gpus
        print(f"✓ GPU count: {len(gpus)}")
        for gpu in gpus:
            print(f"  GPU: {gpu}")
    else:
        print("✗ CUDA not available in Numba")
except ImportError:
    print("✗ Numba not installed")
except Exception as e:
    print(f"✗ Error with Numba: {e}")

# Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

available_libs = []
try:
    import torch
    if torch.cuda.is_available():
        available_libs.append("PyTorch CUDA")
except:
    pass

try:
    import cupy as cp
    if cp.cuda.is_available():
        available_libs.append("CuPy")
except:
    pass

try:
    import pycuda.driver
    available_libs.append("PyCUDA")
except:
    pass

try:
    from numba import cuda
    if cuda.is_available():
        available_libs.append("Numba CUDA")
except:
    pass

if available_libs:
    print(f"✓ GPU libraries available: {', '.join(available_libs)}")
    print("\nRecommendation: Use PyTorch or CuPy for GPU hashing")
else:
    print("✗ No GPU libraries with CUDA support found")
    print("\nTo enable GPU support in Docker:")
    print("1. Ensure NVIDIA Container Toolkit is installed")
    print("2. Run with: docker run --gpus all ...")
    print("3. Use CUDA base image (nvidia/cuda:*)")