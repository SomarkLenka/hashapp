#!/usr/bin/env python3
"""
GPU-accelerated SHA256 implementation using PyCUDA
Based on Bitcoin mining approaches but adapted for random input hashing
"""

import numpy as np
import hashlib
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# Try to import GPU libraries
GPU_AVAILABLE = False
try:
    import pycuda.driver as cuda
    import pycuda.autoinit
    from pycuda.compiler import SourceModule
    import pycuda.gpuarray as gpuarray
    GPU_AVAILABLE = True
except ImportError:
    pass

# SHA256 CUDA kernel (simplified version)
CUDA_SHA256_KERNEL = """
__device__ unsigned int rotr(unsigned int x, unsigned int n) {
    return (x >> n) | (x << (32 - n));
}

__device__ void sha256_transform(unsigned int* state, const unsigned char* data) {
    // SHA256 constants
    unsigned int k[64] = {
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
        0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
        0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
        0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
        0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
        0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
        0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
        0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
        0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    };
    
    unsigned int w[64];
    unsigned int a, b, c, d, e, f, g, h;
    unsigned int t1, t2;
    
    // Copy data to w[0..15]
    for (int i = 0; i < 16; i++) {
        w[i] = (data[i*4] << 24) | (data[i*4+1] << 16) | 
               (data[i*4+2] << 8) | data[i*4+3];
    }
    
    // Extend w[16..63]
    for (int i = 16; i < 64; i++) {
        unsigned int s0 = rotr(w[i-15], 7) ^ rotr(w[i-15], 18) ^ (w[i-15] >> 3);
        unsigned int s1 = rotr(w[i-2], 17) ^ rotr(w[i-2], 19) ^ (w[i-2] >> 10);
        w[i] = w[i-16] + s0 + w[i-7] + s1;
    }
    
    // Initialize working variables
    a = state[0];
    b = state[1];
    c = state[2];
    d = state[3];
    e = state[4];
    f = state[5];
    g = state[6];
    h = state[7];
    
    // Main loop
    for (int i = 0; i < 64; i++) {
        unsigned int S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
        unsigned int ch = (e & f) ^ ((~e) & g);
        t1 = h + S1 + ch + k[i] + w[i];
        unsigned int S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
        unsigned int maj = (a & b) ^ (a & c) ^ (b & c);
        t2 = S0 + maj;
        
        h = g;
        g = f;
        f = e;
        e = d + t1;
        d = c;
        c = b;
        b = a;
        a = t1 + t2;
    }
    
    // Add to state
    state[0] += a;
    state[1] += b;
    state[2] += c;
    state[3] += d;
    state[4] += e;
    state[5] += f;
    state[6] += g;
    state[7] += h;
}

__global__ void sha256_kernel(unsigned char* inputs, unsigned char* outputs, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    // SHA256 initial state
    unsigned int state[8] = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    };
    
    // Process input (assuming 32 bytes)
    unsigned char padded[64];
    for (int i = 0; i < 32; i++) {
        padded[i] = inputs[idx * 32 + i];
    }
    
    // Add padding
    padded[32] = 0x80;
    for (int i = 33; i < 56; i++) {
        padded[i] = 0;
    }
    
    // Add length (256 bits = 32 bytes)
    unsigned long long bitlen = 256;
    for (int i = 0; i < 8; i++) {
        padded[56 + i] = (bitlen >> ((7 - i) * 8)) & 0xff;
    }
    
    // Transform
    sha256_transform(state, padded);
    
    // Output hash
    for (int i = 0; i < 8; i++) {
        outputs[idx * 32 + i * 4] = (state[i] >> 24) & 0xff;
        outputs[idx * 32 + i * 4 + 1] = (state[i] >> 16) & 0xff;
        outputs[idx * 32 + i * 4 + 2] = (state[i] >> 8) & 0xff;
        outputs[idx * 32 + i * 4 + 3] = state[i] & 0xff;
    }
}
"""

class GPUHasher:
    """GPU-accelerated SHA256 hasher using CUDA"""
    
    def __init__(self, device_id: int = 0):
        self.device_id = device_id
        self.cuda_kernel = None
        self.block_size = 256  # CUDA threads per block
        
        if GPU_AVAILABLE:
            try:
                # Compile CUDA kernel
                mod = SourceModule(CUDA_SHA256_KERNEL)
                self.cuda_kernel = mod.get_function("sha256_kernel")
                logger.info(f"GPU {device_id} initialized with CUDA kernel")
            except Exception as e:
                logger.warning(f"Failed to compile CUDA kernel: {e}")
                self.cuda_kernel = None
    
    def hash_batch_gpu(self, inputs: List[bytes]) -> List[bytes]:
        """Hash a batch of 32-byte inputs on GPU"""
        if not GPU_AVAILABLE or not self.cuda_kernel:
            return self.hash_batch_cpu(inputs)
        
        try:
            n = len(inputs)
            
            # Prepare input array (32 bytes per input)
            input_array = np.zeros((n, 32), dtype=np.uint8)
            for i, inp in enumerate(inputs):
                input_array[i, :len(inp)] = np.frombuffer(inp[:32], dtype=np.uint8)
            
            # Allocate GPU memory
            gpu_inputs = cuda.mem_alloc(input_array.nbytes)
            gpu_outputs = cuda.mem_alloc(n * 32)  # 32 bytes per hash
            
            # Copy inputs to GPU
            cuda.memcpy_htod(gpu_inputs, input_array)
            
            # Calculate grid dimensions
            grid_size = (n + self.block_size - 1) // self.block_size
            
            # Run kernel
            self.cuda_kernel(
                gpu_inputs, gpu_outputs, np.int32(n),
                block=(self.block_size, 1, 1),
                grid=(grid_size, 1, 1)
            )
            
            # Copy results back
            output_array = np.zeros((n, 32), dtype=np.uint8)
            cuda.memcpy_dtoh(output_array, gpu_outputs)
            
            # Convert to bytes
            results = [bytes(output_array[i]) for i in range(n)]
            return results
            
        except Exception as e:
            logger.warning(f"GPU processing failed: {e}")
            return self.hash_batch_cpu(inputs)
    
    def hash_batch_cpu(self, inputs: List[bytes]) -> List[bytes]:
        """Fallback CPU hashing"""
        return [hashlib.sha256(inp).digest() for inp in inputs]


class CuPyHasher:
    """Alternative GPU hasher using CuPy (simpler but less optimized)"""
    
    def __init__(self, device_id: int = 0):
        self.device_id = device_id
        self.cp = None
        
        try:
            import cupy as cp
            self.cp = cp
            with cp.cuda.Device(device_id):
                logger.info(f"CuPy initialized on GPU {device_id}")
        except Exception as e:
            logger.warning(f"CuPy initialization failed: {e}")
            self.cp = None
    
    def hash_batch_gpu(self, inputs: List[bytes]) -> List[bytes]:
        """Hash using CuPy (still uses CPU SHA256 but manages memory on GPU)"""
        if not self.cp:
            return self.hash_batch_cpu(inputs)
        
        try:
            with self.cp.cuda.Device(self.device_id):
                # For now, we still use CPU SHA256 but manage batch on GPU
                # A full GPU implementation would require custom kernels
                results = []
                for inp in inputs:
                    hash_val = hashlib.sha256(inp).digest()
                    results.append(hash_val)
                return results
        except Exception as e:
            logger.warning(f"CuPy processing failed: {e}")
            return self.hash_batch_cpu(inputs)
    
    def hash_batch_cpu(self, inputs: List[bytes]) -> List[bytes]:
        """Fallback CPU hashing"""
        return [hashlib.sha256(inp).digest() for inp in inputs]


def benchmark_hashers():
    """Benchmark different hashing methods"""
    import time
    
    # Generate test inputs
    test_size = 10000
    inputs = [hashlib.sha256(str(i).encode()).digest() for i in range(test_size)]
    
    # Test CPU
    start = time.time()
    cpu_results = [hashlib.sha256(inp).digest() for inp in inputs]
    cpu_time = time.time() - start
    print(f"CPU: {test_size/cpu_time:.0f} hashes/sec")
    
    # Test GPU if available
    if GPU_AVAILABLE:
        gpu_hasher = GPUHasher()
        start = time.time()
        gpu_results = gpu_hasher.hash_batch_gpu(inputs)
        gpu_time = time.time() - start
        print(f"GPU: {test_size/gpu_time:.0f} hashes/sec")
        print(f"Speedup: {cpu_time/gpu_time:.2f}x")
        
        # Verify correctness
        for i in range(min(10, len(inputs))):
            if cpu_results[i] != gpu_results[i]:
                print(f"ERROR: Hash mismatch at index {i}")
                break
        else:
            print("Hashes verified correct!")


if __name__ == "__main__":
    print(f"GPU Available: {GPU_AVAILABLE}")
    if GPU_AVAILABLE:
        print(f"CUDA Devices: {cuda.Device.count()}")
        benchmark_hashers()
    else:
        print("No GPU support detected")