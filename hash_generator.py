#!/usr/bin/env python3
"""
Asynchronous SHA256 Hash Generator with GPU Support and BigTable Integration
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

# GPU imports - will handle gracefully if not available
try:
    import cupy as cp
    from numba import cuda
    import pycuda.driver as cuda_driver
    import pycuda.autoinit
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    cp = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GPUHasher:
    """GPU-accelerated SHA256 hasher using CUDA"""
    
    def __init__(self, device_id: int):
        self.device_id = device_id
        if GPU_AVAILABLE:
            with cp.cuda.Device(device_id):
                self.device = cp.cuda.Device(device_id)
                self.stream = cp.cuda.Stream()
    
    def hash_batch_gpu(self, inputs: np.ndarray) -> List[bytes]:
        """Hash a batch of inputs on GPU"""
        if not GPU_AVAILABLE:
            return self.hash_batch_cpu(inputs)
        
        with cp.cuda.Device(self.device_id):
            # Convert to GPU array
            gpu_inputs = cp.asarray(inputs)
            results = []
            
            # Process on GPU (simplified - in production would use custom CUDA kernel)
            for inp in inputs:
                # For now, fall back to CPU SHA256
                # In production, you'd implement a CUDA kernel for SHA256
                hash_val = hashlib.sha256(inp).digest()
                results.append(hash_val)
            
            return results
    
    def hash_batch_cpu(self, inputs: np.ndarray) -> List[bytes]:
        """Fallback CPU hashing"""
        return [hashlib.sha256(inp).digest() for inp in inputs]


class SparseInputGenerator:
    """Generate sparse, well-distributed input values"""
    
    def __init__(self, instance_id: str = None):
        # Use instance ID for uniqueness across instances
        self.instance_id = instance_id or self._generate_instance_id()
        self.counter = secrets.randbits(64)  # Start at random position
        self.jump_size = secrets.randbits(16) | 1  # Ensure odd for better distribution
        
    def _generate_instance_id(self) -> str:
        """Generate unique instance ID based on hostname and time"""
        hostname = socket.gethostname()
        timestamp = int(time.time() * 1000000)
        return f"{hostname}_{timestamp}_{secrets.token_hex(4)}"
    
    def generate_batch(self, batch_size: int) -> List[bytes]:
        """Generate a batch of sparse input values"""
        inputs = []
        for _ in range(batch_size):
            # Combine multiple entropy sources for maximum coverage
            entropy_sources = [
                self.counter.to_bytes(8, 'big'),
                secrets.token_bytes(8),  # Random component
                self.instance_id.encode()[:8].ljust(8, b'\x00'),  # Instance-specific
                int(time.time_ns()).to_bytes(8, 'big'),  # Time-based
                secrets.token_bytes(8)  # Additional randomness
            ]
            
            # Combine and hash to create 32-byte input
            combined = b''.join(entropy_sources)
            input_hash = hashlib.sha256(combined).digest()
            inputs.append(input_hash)
            
            # Jump by prime-like amount for sparse distribution
            self.counter = (self.counter * 6364136223846793005 + self.jump_size) & ((1 << 64) - 1)
        
        return inputs


class HashGenerator:
    """Main hash generator with BigTable integration"""
    
    def __init__(self, config: dict):
        self.config = config
        self.input_generator = SparseInputGenerator()
        self.hashers = []
        self.batch_buffer = []
        self.total_hashes = 0
        self.start_time = time.time()
        self.last_report_time = time.time()
        
        # Initialize BigTable
        self._init_bigtable()
        
        # Initialize GPU hashers
        self._init_gpu_hashers()
        
        # Thread pool for CPU fallback
        self.executor = ThreadPoolExecutor(max_workers=config.get('cpu_threads', 4))
    
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
        """Initialize GPU hashers for all available GPUs"""
        if GPU_AVAILABLE:
            try:
                gpu_count = cuda_driver.Device.count()
                logger.info(f"Detected {gpu_count} GPU(s)")
                for i in range(gpu_count):
                    self.hashers.append(GPUHasher(i))
            except Exception as e:
                logger.warning(f"GPU initialization failed: {e}")
                self.hashers = []
        
        if not self.hashers:
            logger.info("No GPUs available, using CPU")
            # Create CPU-based hashers
            for _ in range(self.config.get('cpu_threads', 4)):
                self.hashers.append(GPUHasher(-1))  # -1 indicates CPU
    
    async def bulk_upsert_bigtable(self, inputs: List[bytes], hashes: List[bytes]):
        """Bulk upsert to BigTable"""
        if not self.bt_table:
            return
        
        try:
            rows = []
            for input_bytes, hash_bytes in zip(inputs, hashes):
                # Use hash as row key for faster lookups
                row_key = hash_bytes
                
                row = DirectRow(row_key=row_key)
                row.set_cell(
                    column_family_id='hash_data',
                    column=b'input',
                    value=input_bytes
                )
                rows.append(row)
            
            # Batch mutation
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.bt_table.mutate_rows,
                rows
            )
            logger.info(f"Uploaded {len(rows)} hashes to BigTable")
        except Exception as e:
            logger.error(f"BigTable upload failed: {e}")
    
    async def report_hashrate(self):
        """Report hashrate to web server"""
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        if elapsed > 0:
            hashrate = self.total_hashes / elapsed
            
            # Calculate recent hashrate (last report interval)
            time_since_last = current_time - self.last_report_time
            hashes_since_last = len(self.batch_buffer)
            recent_hashrate = hashes_since_last / time_since_last if time_since_last > 0 else 0
            
            data = {
                'instance_id': self.input_generator.instance_id,
                'total_hashes': self.total_hashes,
                'overall_hashrate': hashrate,
                'recent_hashrate': recent_hashrate,
                'timestamp': datetime.utcnow().isoformat(),
                'gpu_count': len(self.hashers),
                'gpu_available': GPU_AVAILABLE
            }
            
            # Post to web server
            if self.config.get('monitoring', {}).get('endpoint'):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            self.config['monitoring']['endpoint'],
                            json=data,
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as response:
                            if response.status == 200:
                                logger.debug(f"Reported hashrate: {recent_hashrate:.2f} H/s")
                except Exception as e:
                    logger.warning(f"Failed to report hashrate: {e}")
            
            self.last_report_time = current_time
            logger.info(f"Hashrate: {recent_hashrate:.2f} H/s (Total: {self.total_hashes})")
    
    async def process_batch(self, hasher: GPUHasher, inputs: List[bytes]) -> List[bytes]:
        """Process a batch of inputs through a hasher"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            hasher.hash_batch_cpu,  # Using CPU for now
            np.array(inputs)
        )
    
    async def hash_worker(self, hasher_id: int):
        """Worker coroutine for continuous hashing"""
        hasher = self.hashers[hasher_id]
        batch_size = self.config.get('batch_size', 100)
        
        while True:
            try:
                # Generate sparse inputs
                inputs = self.input_generator.generate_batch(batch_size)
                
                # Compute hashes
                hashes = await self.process_batch(hasher, inputs)
                
                # Add to buffer
                for inp, hsh in zip(inputs, hashes):
                    self.batch_buffer.append((inp, hsh))
                    self.total_hashes += 1
                
                # Check if we need to upload
                if len(self.batch_buffer) >= self.config.get('upload_batch_size', 1000):
                    await self.upload_and_report()
                
            except Exception as e:
                logger.error(f"Worker {hasher_id} error: {e}")
                await asyncio.sleep(1)
    
    async def upload_and_report(self):
        """Upload batch to BigTable and report hashrate"""
        if not self.batch_buffer:
            return
        
        # Extract inputs and hashes
        inputs, hashes = zip(*self.batch_buffer)
        
        # Upload to BigTable
        await self.bulk_upsert_bigtable(list(inputs), list(hashes))
        
        # Report hashrate
        await self.report_hashrate()
        
        # Clear buffer
        self.batch_buffer = []
    
    async def periodic_upload(self):
        """Periodically upload any remaining hashes"""
        while True:
            await asyncio.sleep(self.config.get('upload_interval', 10))
            if self.batch_buffer:
                await self.upload_and_report()
    
    async def periodic_monitoring(self):
        """Report status to monitoring server every N seconds"""
        report_interval = self.config.get('monitoring', {}).get('report_interval', 10)
        logger.info(f"Starting monitoring reporter (every {report_interval} seconds)")
        
        while True:
            await asyncio.sleep(report_interval)
            await self.report_hashrate()
    
    async def run(self):
        """Main run loop"""
        logger.info(f"Starting hash generator with {len(self.hashers)} workers")
        logger.info(f"Instance ID: {self.input_generator.instance_id}")
        
        # Create worker tasks
        workers = [
            asyncio.create_task(self.hash_worker(i))
            for i in range(len(self.hashers))
        ]
        
        # Add periodic upload task
        workers.append(asyncio.create_task(self.periodic_upload()))
        
        # Add periodic monitoring task (reports every N seconds)
        workers.append(asyncio.create_task(self.periodic_monitoring()))
        
        try:
            await asyncio.gather(*workers)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            # Final upload
            await self.upload_and_report()


async def main():
    """Main entry point"""
    # Load configuration
    config_path = os.environ.get('CONFIG_PATH', 'config.json')
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.warning(f"Config file not found at {config_path}, using defaults")
        config = {
            'bigtable': {
                'project_id': os.environ.get('GCP_PROJECT_ID', 'your-project-id'),
                'instance_id': os.environ.get('BT_INSTANCE_ID', 'your-instance-id'),
                'table_name': os.environ.get('BT_TABLE_NAME', 'hashes')
            },
            'monitoring': {
                'endpoint': os.environ.get('MONITORING_ENDPOINT', '')
            },
            'batch_size': int(os.environ.get('BATCH_SIZE', '100')),
            'upload_batch_size': int(os.environ.get('UPLOAD_BATCH_SIZE', '1000')),
            'upload_interval': int(os.environ.get('UPLOAD_INTERVAL', '10')),
            'cpu_threads': int(os.environ.get('CPU_THREADS', '4'))
        }
    
    # Create and run generator
    generator = HashGenerator(config)
    await generator.run()


if __name__ == '__main__':
    asyncio.run(main())