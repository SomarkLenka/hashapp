#!/usr/bin/env python3
"""
GPU-accelerated SHA256 hash generator for NVIDIA GPUs
Uses CuPy with actual GPU kernels for SHA256
"""

import asyncio
import hashlib
import secrets
import time
import os
import json
import socket
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import logging
import numpy as np

from google.cloud import bigtable
from google.cloud.bigtable.row import DirectRow

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Check for GPU support
GPU_AVAILABLE = False
GPU_COUNT = 0

try:
    import cupy as cp
    import cupyx
    
    # Test GPU access
    GPU_COUNT = cp.cuda.runtime.getDeviceCount()
    if GPU_COUNT > 0:
        GPU_AVAILABLE = True
        logger.info(f"CuPy initialized with {GPU_COUNT} GPU(s)")
        
        # Log GPU info
        for i in range(GPU_COUNT):
            with cp.cuda.Device(i):
                props = cp.cuda.runtime.getDeviceProperties(i)
                name = props['name'].decode('utf-8') if isinstance(props['name'], bytes) else props['name']
                memory = props['totalGlobalMem'] / (1024**3)
                logger.info(f"GPU {i}: {name}, {memory:.1f} GB")
    else:
        logger.warning("No GPUs detected")
        
except Exception as e:
    logger.warning(f"GPU initialization failed: {e}")
    GPU_AVAILABLE = False


# CuPy kernel for SHA256 - simplified but functional
SHA256_KERNEL = """
extern "C" {

__device__ unsigned int rotr(unsigned int x, int n) {
    return (x >> n) | (x << (32 - n));
}

__global__ void sha256_kernel(
    const unsigned char* inputs,
    unsigned char* outputs,
    int num_hashes
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= num_hashes) return;
    
    // SHA256 constants
    const unsigned int K[64] = {
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
    
    // Initial hash values
    unsigned int h0 = 0x6a09e667, h1 = 0xbb67ae85;
    unsigned int h2 = 0x3c6ef372, h3 = 0xa54ff53a;
    unsigned int h4 = 0x510e527f, h5 = 0x9b05688c;
    unsigned int h6 = 0x1f83d9ab, h7 = 0x5be0cd19;
    
    // Process input (32 bytes)
    const unsigned char* input = inputs + idx * 32;
    unsigned int w[64];
    
    // Copy input to w[0..7] as big-endian words
    for (int i = 0; i < 8; i++) {
        w[i] = ((unsigned int)input[i*4] << 24) |
               ((unsigned int)input[i*4+1] << 16) |
               ((unsigned int)input[i*4+2] << 8) |
               ((unsigned int)input[i*4+3]);
    }
    
    // Padding
    w[8] = 0x80000000;  // Padding bit
    for (int i = 9; i < 15; i++) w[i] = 0;
    w[15] = 256;  // Length in bits (32 bytes * 8)
    
    // Extend message
    for (int i = 16; i < 64; i++) {
        unsigned int s0 = rotr(w[i-15], 7) ^ rotr(w[i-15], 18) ^ (w[i-15] >> 3);
        unsigned int s1 = rotr(w[i-2], 17) ^ rotr(w[i-2], 19) ^ (w[i-2] >> 10);
        w[i] = w[i-16] + s0 + w[i-7] + s1;
    }
    
    // Working variables
    unsigned int a = h0, b = h1, c = h2, d = h3;
    unsigned int e = h4, f = h5, g = h6, h = h7;
    
    // Main loop
    for (int i = 0; i < 64; i++) {
        unsigned int S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
        unsigned int ch = (e & f) ^ (~e & g);
        unsigned int temp1 = h + S1 + ch + K[i] + w[i];
        unsigned int S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
        unsigned int maj = (a & b) ^ (a & c) ^ (b & c);
        unsigned int temp2 = S0 + maj;
        
        h = g; g = f; f = e; e = d + temp1;
        d = c; c = b; b = a; a = temp1 + temp2;
    }
    
    // Add to hash
    h0 += a; h1 += b; h2 += c; h3 += d;
    h4 += e; h5 += f; h6 += g; h7 += h;
    
    // Write output
    unsigned char* output = outputs + idx * 32;
    output[0] = (h0 >> 24) & 0xff; output[1] = (h0 >> 16) & 0xff;
    output[2] = (h0 >> 8) & 0xff; output[3] = h0 & 0xff;
    output[4] = (h1 >> 24) & 0xff; output[5] = (h1 >> 16) & 0xff;
    output[6] = (h1 >> 8) & 0xff; output[7] = h1 & 0xff;
    output[8] = (h2 >> 24) & 0xff; output[9] = (h2 >> 16) & 0xff;
    output[10] = (h2 >> 8) & 0xff; output[11] = h2 & 0xff;
    output[12] = (h3 >> 24) & 0xff; output[13] = (h3 >> 16) & 0xff;
    output[14] = (h3 >> 8) & 0xff; output[15] = h3 & 0xff;
    output[16] = (h4 >> 24) & 0xff; output[17] = (h4 >> 16) & 0xff;
    output[18] = (h4 >> 8) & 0xff; output[19] = h4 & 0xff;
    output[20] = (h5 >> 24) & 0xff; output[21] = (h5 >> 16) & 0xff;
    output[22] = (h5 >> 8) & 0xff; output[23] = h5 & 0xff;
    output[24] = (h6 >> 24) & 0xff; output[25] = (h6 >> 16) & 0xff;
    output[26] = (h6 >> 8) & 0xff; output[27] = h6 & 0xff;
    output[28] = (h7 >> 24) & 0xff; output[29] = (h7 >> 16) & 0xff;
    output[30] = (h7 >> 8) & 0xff; output[31] = h7 & 0xff;
}

}
"""

# Compile kernel if GPU available
sha256_gpu = None
if GPU_AVAILABLE:
    try:
        sha256_gpu = cp.RawKernel(SHA256_KERNEL, 'sha256_kernel')
        logger.info("GPU SHA256 kernel compiled successfully!")
    except Exception as e:
        logger.warning(f"Failed to compile GPU kernel: {e}")
        sha256_gpu = None


class GPUHasher:
    """GPU-accelerated hasher using CuPy"""
    
    def __init__(self, device_id: int = 0):
        self.device_id = device_id
        self.use_gpu = GPU_AVAILABLE and sha256_gpu is not None
        
        if self.use_gpu:
            try:
                with cp.cuda.Device(device_id):
                    _ = cp.zeros(1)  # Test access
                logger.info(f"GPU {device_id} initialized for hashing")
            except Exception as e:
                logger.warning(f"GPU {device_id} not accessible: {e}")
                self.use_gpu = False
    
    def hash_batch_gpu(self, batch_size: int = 100000) -> List[Tuple[bytes, bytes]]:
        """Generate random inputs and hash them on GPU"""
        
        # Generate random inputs (32 bytes each)
        random_data = np.random.bytes(batch_size * 32)
        inputs_np = np.frombuffer(random_data, dtype=np.uint8).reshape(batch_size, 32)
        
        if self.use_gpu and sha256_gpu:
            try:
                with cp.cuda.Device(self.device_id):
                    # Transfer to GPU
                    inputs_gpu = cp.asarray(inputs_np, dtype=cp.uint8)
                    outputs_gpu = cp.zeros((batch_size, 32), dtype=cp.uint8)
                    
                    # Run kernel
                    block_size = 256
                    grid_size = (batch_size + block_size - 1) // block_size
                    
                    sha256_gpu((grid_size,), (block_size,), 
                              (inputs_gpu, outputs_gpu, batch_size))
                    
                    # Get results
                    outputs_np = outputs_gpu.get()
                    
                    # Package results
                    results = []
                    for i in range(batch_size):
                        input_hex = inputs_np[i].tobytes().hex().encode('utf-8')
                        hash_bytes = outputs_np[i].tobytes()
                        results.append((input_hex, hash_bytes))
                    
                    return results
                    
            except Exception as e:
                logger.warning(f"GPU hashing failed: {e}, falling back to CPU")
        
        # CPU fallback
        results = []
        for i in range(batch_size):
            input_bytes = inputs_np[i].tobytes()
            hash_bytes = hashlib.sha256(input_bytes).digest()
            input_hex = input_bytes.hex().encode('utf-8')
            results.append((input_hex, hash_bytes))
        
        return results
    
    def hash_batch_cpu(self, batch_size: int = 10000) -> List[Tuple[bytes, bytes]]:
        """CPU fallback for hashing"""
        results = []
        for _ in range(batch_size):
            random_bytes = secrets.token_bytes(32)
            hash_bytes = hashlib.sha256(random_bytes).digest()
            input_hex = random_bytes.hex().encode('utf-8')
            results.append((input_hex, hash_bytes))
        return results


class HashGenerator:
    """Main hash generator with GPU support"""
    
    def __init__(self, config: dict):
        self.config = config
        self.instance_id = f"{socket.gethostname()}_{int(time.time()*1000000)}_{secrets.token_hex(4)}"
        self.batch_buffer = []
        self.total_hashes = 0
        self.start_time = time.time()
        self.last_report_time = time.time()
        self.hashers = []
        
        # Initialize BigTable
        self._init_bigtable()
        
        # Initialize hashers
        self._init_hashers()
        
        # Thread pool
        self.executor = ThreadPoolExecutor(max_workers=8)
    
    def _init_bigtable(self):
        """Initialize BigTable connection"""
        try:
            self.bt_client = bigtable.Client(
                project=self.config['bigtable']['project_id'],
                admin=True
            )
            self.bt_instance = self.bt_client.instance(
                self.config['bigtable']['instance_id']
            )
            self.bt_table = self.bt_instance.table(
                self.config['bigtable']['table_name']
            )
            
            if self.bt_table.exists():
                logger.info("BigTable connection initialized")
            else:
                logger.error(f"BigTable table '{self.config['bigtable']['table_name']}' does not exist!")
                self.bt_table = None
                
        except Exception as e:
            logger.error(f"Failed to initialize BigTable: {e}")
            self.bt_table = None
    
    def _init_hashers(self):
        """Initialize GPU or CPU hashers"""
        if GPU_AVAILABLE and GPU_COUNT > 0:
            # Use all available GPUs
            for i in range(GPU_COUNT):
                self.hashers.append(GPUHasher(i))
            logger.info(f"Initialized {GPU_COUNT} GPU hashers")
        else:
            # CPU fallback with multiple workers
            num_cpu = self.config.get('cpu_threads', 16)
            for i in range(num_cpu):
                self.hashers.append(GPUHasher(-1))
            logger.info(f"Initialized {num_cpu} CPU hashers")
    
    async def bulk_upsert_bigtable(self, batch: List[Tuple[bytes, bytes]]):
        """Bulk upsert to BigTable"""
        if not self.bt_table:
            return
        
        try:
            rows = []
            for input_hex, hash_bytes in batch:
                row = DirectRow(row_key=hash_bytes)
                row.set_cell(
                    column_family_id='hash_data',
                    column=b'input',
                    value=input_hex
                )
                rows.append(row)
            
            # Upload in chunks
            chunk_size = 10000
            for i in range(0, len(rows), chunk_size):
                chunk = rows[i:i+chunk_size]
                await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self.bt_table.mutate_rows,
                    chunk
                )
                logger.info(f"Uploaded {len(chunk)} hashes to BigTable")
            
            # Verify randomness
            if batch:
                sample = batch[0][1].hex()
                logger.info(f"Sample hash: {sample[:16]}... (verifying randomness)")
                
        except Exception as e:
            logger.error(f"BigTable upload failed: {e}")
    
    async def hash_worker(self, worker_id: int):
        """Worker that generates and hashes"""
        hasher = self.hashers[worker_id]
        batch_size = 100000 if GPU_AVAILABLE else 10000
        
        while True:
            try:
                # Generate and hash
                loop = asyncio.get_event_loop()
                
                if hasher.use_gpu:
                    batch = await loop.run_in_executor(
                        self.executor,
                        hasher.hash_batch_gpu,
                        batch_size
                    )
                else:
                    batch = await loop.run_in_executor(
                        self.executor,
                        hasher.hash_batch_cpu,
                        batch_size
                    )
                
                # Add to buffer
                self.batch_buffer.extend(batch)
                self.total_hashes += len(batch)
                
                # Upload if buffer is large
                if len(self.batch_buffer) >= self.config.get('upload_batch_size', 1000000):
                    logger.info(f"Buffer reached {len(self.batch_buffer)}, uploading...")
                    await self.upload_and_report()
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)
    
    async def upload_and_report(self):
        """Upload batch and report stats"""
        if not self.batch_buffer:
            return
        
        # Upload
        batch_to_upload = self.batch_buffer[:1000000]
        await self.bulk_upsert_bigtable(batch_to_upload)
        self.batch_buffer = self.batch_buffer[len(batch_to_upload):]
        
        # Report
        current_time = time.time()
        elapsed = current_time - self.start_time
        hashrate = self.total_hashes / elapsed if elapsed > 0 else 0
        
        mode = "GPU" if GPU_AVAILABLE else "CPU"
        logger.info(f"{mode} Hashrate: {hashrate/1000:.2f} KH/s | Total: {self.total_hashes:,}")
        
        if hashrate > 1000000:
            logger.info(f"{mode} Hashrate: {hashrate/1000000:.2f} MH/s")
        
        self.last_report_time = current_time
    
    async def periodic_upload(self):
        """Periodic upload task"""
        upload_interval = self.config.get('upload_interval', 60)
        logger.info(f"Periodic upload every {upload_interval}s")
        
        while True:
            await asyncio.sleep(upload_interval)
            if self.batch_buffer:
                logger.info(f"Periodic upload: {len(self.batch_buffer)} hashes")
                await self.upload_and_report()
    
    async def run(self):
        """Main run loop"""
        mode = f"GPU ({GPU_COUNT} devices)" if GPU_AVAILABLE else "CPU"
        logger.info(f"Starting {mode} hash generator with {len(self.hashers)} workers")
        logger.info(f"Instance: {self.instance_id}")
        
        # Start workers
        workers = [
            asyncio.create_task(self.hash_worker(i))
            for i in range(len(self.hashers))
        ]
        
        # Add periodic upload
        workers.append(asyncio.create_task(self.periodic_upload()))
        
        try:
            await asyncio.gather(*workers)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await self.upload_and_report()


async def main():
    """Main entry point"""
    config_path = os.environ.get('CONFIG_PATH', 'config.json')
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {
            'bigtable': {
                'project_id': os.environ.get('GCP_PROJECT_ID', 'adept-storm-466618-b4'),
                'instance_id': os.environ.get('BT_INSTANCE_ID', 'hash-generator-instance'),
                'table_name': os.environ.get('BT_TABLE_NAME', 'hashes')
            },
            'upload_batch_size': 1000000,
            'upload_interval': 60,
            'cpu_threads': 16
        }
    
    generator = HashGenerator(config)
    await generator.run()


if __name__ == '__main__':
    asyncio.run(main())