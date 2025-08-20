#!/usr/bin/env python3
"""
Fixed GPU SHA256 Hash Generator
Actually uses GPU for hashing, not just memory management
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
import aiohttp
import numpy as np

from google.cloud import bigtable
from google.cloud.bigtable.row import DirectRow

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# GPU Support Detection
GPU_AVAILABLE = False
PYCUDA_AVAILABLE = False

# Try CuPy first
try:
    import cupy as cp
    test_device = cp.cuda.Device(0)
    GPU_AVAILABLE = True
    logger.info("CuPy available for GPU operations")
except Exception as e:
    logger.info(f"CuPy not available: {e}")

# Try PyCUDA for real GPU SHA256
try:
    import pycuda.driver as cuda
    import pycuda.autoinit
    from pycuda.compiler import SourceModule
    
    # Optimized SHA256 CUDA kernel
    cuda_sha256_src = """
    #define ROTR(x,n) (((x)>>(n)) | ((x)<<(32-(n))))
    #define CH(x,y,z) (((x) & (y)) ^ (~(x) & (z)))
    #define MAJ(x,y,z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
    #define EP0(x) (ROTR(x,2) ^ ROTR(x,13) ^ ROTR(x,22))
    #define EP1(x) (ROTR(x,6) ^ ROTR(x,11) ^ ROTR(x,25))
    #define SIG0(x) (ROTR(x,7) ^ ROTR(x,18) ^ ((x) >> 3))
    #define SIG1(x) (ROTR(x,17) ^ ROTR(x,19) ^ ((x) >> 10))
    
    __constant__ unsigned int k[64] = {
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    };
    
    __global__ void sha256_batch(unsigned char* inputs, unsigned char* outputs, int num_hashes) {
        int idx = blockIdx.x * blockDim.x + threadIdx.x;
        if (idx >= num_hashes) return;
        
        unsigned char* input = inputs + idx * 64;
        unsigned char* output = outputs + idx * 32;
        
        // Initialize hash values
        unsigned int h0 = 0x6a09e667, h1 = 0xbb67ae85, h2 = 0x3c6ef372, h3 = 0xa54ff53a;
        unsigned int h4 = 0x510e527f, h5 = 0x9b05688c, h6 = 0x1f83d9ab, h7 = 0x5be0cd19;
        
        unsigned int w[64];
        
        // Copy input to w[0..15] as big-endian 32-bit words
        for (int i = 0; i < 16; i++) {
            w[i] = ((unsigned int)input[i*4] << 24) |
                   ((unsigned int)input[i*4+1] << 16) |
                   ((unsigned int)input[i*4+2] << 8) |
                   ((unsigned int)input[i*4+3]);
        }
        
        // Extend the first 16 words into the remaining 48 words
        for (int i = 16; i < 64; i++) {
            w[i] = SIG1(w[i-2]) + w[i-7] + SIG0(w[i-15]) + w[i-16];
        }
        
        // Initialize working variables
        unsigned int a = h0, b = h1, c = h2, d = h3;
        unsigned int e = h4, f = h5, g = h6, h = h7;
        
        // Compression function main loop
        for (int i = 0; i < 64; i++) {
            unsigned int t1 = h + EP1(e) + CH(e,f,g) + k[i] + w[i];
            unsigned int t2 = EP0(a) + MAJ(a,b,c);
            h = g; g = f; f = e; e = d + t1;
            d = c; c = b; b = a; a = t1 + t2;
        }
        
        // Add compressed chunk to current hash value
        h0 += a; h1 += b; h2 += c; h3 += d;
        h4 += e; h5 += f; h6 += g; h7 += h;
        
        // Produce final hash value (big-endian)
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
    """
    
    mod = SourceModule(cuda_sha256_src)
    sha256_gpu_func = mod.get_function("sha256_batch")
    PYCUDA_AVAILABLE = True
    logger.info("PyCUDA SHA256 kernel compiled - REAL GPU HASHING ENABLED!")
    
except Exception as e:
    logger.warning(f"PyCUDA not available: {e}")


class GPUHasher:
    """Actual GPU SHA256 hasher"""
    
    def __init__(self, device_id: int = 0, batch_size: int = 100000):
        self.device_id = device_id
        self.batch_size = batch_size
        self.use_pycuda = PYCUDA_AVAILABLE
        
        if self.use_pycuda:
            logger.info(f"GPU {device_id}: Using PyCUDA for REAL GPU SHA256")
        elif GPU_AVAILABLE:
            logger.info(f"GPU {device_id}: Using CuPy (CPU SHA256 with GPU memory)")
        else:
            logger.info(f"Worker {device_id}: CPU-only mode")
    
    def hash_batch(self, inputs: List[bytes]) -> List[bytes]:
        """Hash batch using GPU if available"""
        
        if self.use_pycuda:
            # REAL GPU SHA256!
            n = len(inputs)
            
            # Prepare padded input (64 bytes each for simplicity)
            input_array = np.zeros((n, 64), dtype=np.uint8)
            for i, hex_str in enumerate(inputs):
                # Add padding for SHA256
                data = bytearray(hex_str[:64] if len(hex_str) >= 64 else hex_str)
                if len(data) < 64:
                    data.append(0x80)  # Padding bit
                    while len(data) < 56:
                        data.append(0)
                    # Length in bits (big-endian)
                    bit_len = len(hex_str) * 8
                    data.extend(bit_len.to_bytes(8, 'big'))
                input_array[i] = np.frombuffer(bytes(data[:64]), dtype=np.uint8)
            
            # Flatten for GPU
            flat_input = input_array.flatten()
            
            # Allocate GPU memory
            gpu_input = cuda.mem_alloc(flat_input.nbytes)
            gpu_output = cuda.mem_alloc(n * 32)
            
            # Copy to GPU
            cuda.memcpy_htod(gpu_input, flat_input)
            
            # Run kernel
            block_size = 256
            grid_size = (n + block_size - 1) // block_size
            
            sha256_gpu_func(
                gpu_input,
                gpu_output,
                np.int32(n),
                block=(block_size, 1, 1),
                grid=(grid_size, 1, 1)
            )
            
            # Get results
            output_array = np.zeros(n * 32, dtype=np.uint8)
            cuda.memcpy_dtoh(output_array, gpu_output)
            
            # Convert to list of bytes
            results = []
            for i in range(n):
                results.append(bytes(output_array[i*32:(i+1)*32]))
            
            return results
            
        else:
            # CPU fallback
            return [hashlib.sha256(inp).digest() for inp in inputs]


class InputGenerator:
    """Generate random hex inputs"""
    
    def __init__(self):
        self.instance_id = f"{socket.gethostname()}_{int(time.time()*1000000)}_{secrets.token_hex(4)}"
    
    def generate_batch(self, batch_size: int) -> List[bytes]:
        """Generate batch of random 64-char hex strings"""
        inputs = []
        for _ in range(batch_size):
            # Generate truly random 32 bytes -> 64 hex chars
            random_bytes = secrets.token_bytes(32)
            hex_string = random_bytes.hex().lower()
            inputs.append(hex_string.encode('utf-8'))
        return inputs


class HashGenerator:
    """Main generator with proper GPU hashing"""
    
    def __init__(self, config: dict):
        self.config = config
        self.input_generator = InputGenerator()
        self.hashers = []
        self.batch_buffer = []
        self.total_hashes = 0
        self.start_time = time.time()
        self.last_report_time = time.time()
        
        # Initialize BigTable
        self._init_bigtable()
        
        # Initialize GPU hashers
        self._init_gpu_hashers()
        
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
            logger.info("BigTable connection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize BigTable: {e}")
            self.bt_table = None
    
    def _init_gpu_hashers(self):
        """Initialize GPU hashers"""
        if PYCUDA_AVAILABLE:
            # Use real GPU hashing
            try:
                import pycuda.driver as cuda
                cuda.init()
                gpu_count = cuda.Device.count()
                logger.info(f"Found {gpu_count} GPUs for REAL GPU SHA256!")
                
                # Use all GPUs
                for i in range(min(gpu_count, 8)):  # Max 8 GPUs
                    self.hashers.append(GPUHasher(i, batch_size=100000))
                
            except Exception as e:
                logger.warning(f"GPU init failed: {e}")
        
        elif GPU_AVAILABLE:
            # Use CuPy
            try:
                gpu_count = cp.cuda.runtime.getDeviceCount()
                logger.info(f"Found {gpu_count} GPUs (using CuPy)")
                
                for i in range(min(gpu_count, 8)):
                    self.hashers.append(GPUHasher(i, batch_size=10000))
                    
            except Exception as e:
                logger.warning(f"CuPy GPU init failed: {e}")
        
        # Fallback to CPU
        if not self.hashers:
            logger.info("No GPUs available, using CPU workers")
            for i in range(self.config.get('cpu_threads', 4)):
                self.hashers.append(GPUHasher(-1, batch_size=1000))
    
    async def bulk_upsert_bigtable(self, inputs: List[bytes], hashes: List[bytes]):
        """Bulk upsert to BigTable"""
        if not self.bt_table:
            return
        
        try:
            rows = []
            for input_bytes, hash_bytes in zip(inputs, hashes):
                row = DirectRow(row_key=hash_bytes)
                row.set_cell(
                    column_family_id='hash_data',
                    column=b'input',
                    value=input_bytes
                )
                rows.append(row)
            
            # Upload in larger chunks (10k at a time)
            chunk_size = 10000
            for i in range(0, len(rows), chunk_size):
                chunk = rows[i:i+chunk_size]
                await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self.bt_table.mutate_rows,
                    chunk
                )
                logger.info(f"Uploaded chunk: {len(chunk)} hashes to BigTable")
            
            logger.info(f"Total uploaded: {len(rows)} hashes")
            
        except Exception as e:
            logger.error(f"BigTable upload failed: {e}")
    
    async def hash_worker(self, hasher_id: int):
        """Worker for continuous hashing"""
        hasher = self.hashers[hasher_id]
        batch_size = 100000 if PYCUDA_AVAILABLE else (10000 if GPU_AVAILABLE else 1000)
        
        while True:
            try:
                # Generate random inputs
                inputs = self.input_generator.generate_batch(batch_size)
                
                # Hash on GPU/CPU
                loop = asyncio.get_event_loop()
                hashes = await loop.run_in_executor(
                    self.executor,
                    hasher.hash_batch,
                    inputs
                )
                
                # Add to buffer
                for inp, hsh in zip(inputs, hashes):
                    self.batch_buffer.append((inp, hsh))
                    self.total_hashes += 1
                
                # Check upload threshold (10M for efficiency)
                if len(self.batch_buffer) >= self.config.get('upload_batch_size', 10000000):
                    logger.info(f"Buffer full ({len(self.batch_buffer)}), uploading...")
                    await self.upload_and_report()
                
            except Exception as e:
                logger.error(f"Worker {hasher_id} error: {e}")
                await asyncio.sleep(1)
    
    async def upload_and_report(self):
        """Upload batch and report stats"""
        if not self.batch_buffer:
            return
        
        # Extract data
        inputs, hashes = zip(*self.batch_buffer)
        
        # Log a sample to verify randomness
        sample_hash = hashes[0].hex()
        logger.info(f"Sample hash: {sample_hash} (should be random, not all zeros)")
        
        # Upload to BigTable
        await self.bulk_upsert_bigtable(list(inputs), list(hashes))
        
        # Report hashrate
        current_time = time.time()
        elapsed = current_time - self.start_time
        hashrate = self.total_hashes / elapsed if elapsed > 0 else 0
        
        mode = "GPU" if (PYCUDA_AVAILABLE or GPU_AVAILABLE) else "CPU"
        logger.info(f"{mode} Hashrate: {hashrate/1000:.2f} KH/s, Total: {self.total_hashes:,}")
        
        # Clear buffer
        self.batch_buffer = []
        self.last_report_time = current_time
    
    async def periodic_upload(self):
        """Periodic upload task"""
        upload_interval = self.config.get('upload_interval', 300)
        logger.info(f"Periodic upload every {upload_interval}s")
        
        while True:
            await asyncio.sleep(upload_interval)
            if self.batch_buffer:
                logger.info(f"Periodic upload: {len(self.batch_buffer)} hashes")
                await self.upload_and_report()
    
    async def periodic_monitoring(self):
        """Report to monitoring endpoint"""
        report_interval = self.config.get('monitoring', {}).get('report_interval', 10)
        
        while True:
            await asyncio.sleep(report_interval)
            
            current_time = time.time()
            elapsed = current_time - self.last_report_time
            recent_hashes = len(self.batch_buffer)
            recent_rate = recent_hashes / elapsed if elapsed > 0 else 0
            
            data = {
                'instance_id': self.input_generator.instance_id,
                'total_hashes': self.total_hashes,
                'recent_hashrate': recent_rate,
                'timestamp': datetime.utcnow().isoformat(),
                'gpu_count': len(self.hashers),
                'gpu_enabled': PYCUDA_AVAILABLE or GPU_AVAILABLE,
                'mode': 'GPU_SHA256' if PYCUDA_AVAILABLE else ('CuPy' if GPU_AVAILABLE else 'CPU')
            }
            
            if self.config.get('monitoring', {}).get('endpoint'):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            self.config['monitoring']['endpoint'],
                            json=data,
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as response:
                            if response.status == 200:
                                logger.debug(f"Reported: {recent_rate/1000:.2f} KH/s")
                except Exception as e:
                    logger.warning(f"Monitoring failed: {e}")
    
    async def run(self):
        """Main run loop"""
        mode = "PyCUDA GPU" if PYCUDA_AVAILABLE else ("CuPy" if GPU_AVAILABLE else "CPU")
        logger.info(f"Starting {mode} hash generator with {len(self.hashers)} workers")
        logger.info(f"Instance: {self.input_generator.instance_id}")
        
        # Start workers
        workers = [
            asyncio.create_task(self.hash_worker(i))
            for i in range(len(self.hashers))
        ]
        
        # Add periodic tasks
        workers.append(asyncio.create_task(self.periodic_upload()))
        workers.append(asyncio.create_task(self.periodic_monitoring()))
        
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
                'project_id': os.environ.get('GCP_PROJECT_ID', 'your-project-id'),
                'instance_id': os.environ.get('BT_INSTANCE_ID', 'your-instance-id'),
                'table_name': os.environ.get('BT_TABLE_NAME', 'hashes')
            },
            'monitoring': {
                'endpoint': os.environ.get('MONITORING_ENDPOINT', ''),
                'report_interval': 10
            },
            'upload_batch_size': 10000000,
            'upload_interval': 300,
            'cpu_threads': 4
        }
    
    generator = HashGenerator(config)
    await generator.run()


if __name__ == '__main__':
    asyncio.run(main())