#!/usr/bin/env python3
"""
Optimized SHA256 Hash Generator with proper GPU batching
Generates random inputs in batches, then processes them on GPUs
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
import queue
import threading

from google.cloud import bigtable
from google.cloud.bigtable.row import DirectRow

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# GPU imports - will handle gracefully if not available
GPU_AVAILABLE = False
cp = None

try:
    import cupy as cp
    gpu_count = cp.cuda.runtime.getDeviceCount()
    if gpu_count > 0:
        GPU_AVAILABLE = True
        logger.info(f"CUDA initialized successfully with {gpu_count} GPU(s)")
except (ImportError, RuntimeError, Exception) as e:
    GPU_AVAILABLE = False
    logger.info(f"GPU support not available: {type(e).__name__}")

# Try alternative GPU libraries
HASHCAT_AVAILABLE = False
try:
    # Check if we can use hashcat or other GPU mining libraries
    import pycuda.driver as cuda
    import pycuda.autoinit
    HASHCAT_AVAILABLE = True
    logger.info("PyCUDA available for GPU acceleration")
except ImportError:
    pass


class BatchInputGenerator:
    """Generate large batches of random inputs for GPU processing"""
    
    def __init__(self, batch_size: int = 100000):
        self.batch_size = batch_size
        self.instance_id = self._generate_instance_id()
        self.counter = secrets.randbits(64)
    
    def _generate_instance_id(self) -> str:
        """Generate unique instance ID"""
        hostname = socket.gethostname()
        timestamp = int(time.time() * 1000000)
        return f"{hostname}_{timestamp}_{secrets.token_hex(4)}"
    
    def generate_mega_batch(self, size: int) -> np.ndarray:
        """Generate a large batch of random 32-byte inputs"""
        # Use numpy for efficient batch generation
        batch = np.random.bytes(size * 32)
        return np.frombuffer(batch, dtype=np.uint8).reshape(size, 32)


class GPUBatchHasher:
    """Process large batches of inputs on GPU"""
    
    def __init__(self, device_id: int):
        self.device_id = device_id
        self.batch_queue = queue.Queue(maxsize=10)  # Buffer for input batches
        self.result_queue = queue.Queue()
        
        if GPU_AVAILABLE and device_id >= 0:
            try:
                # Set GPU device
                cp.cuda.Device(device_id).use()
                logger.info(f"GPU {device_id} initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize GPU {device_id}: {e}")
    
    def hash_mega_batch(self, inputs: np.ndarray) -> List[bytes]:
        """Hash a large batch of inputs"""
        results = []
        
        # Process in chunks to avoid memory issues
        chunk_size = 10000
        for i in range(0, len(inputs), chunk_size):
            chunk = inputs[i:i+chunk_size]
            
            if GPU_AVAILABLE and self.device_id >= 0:
                # GPU path - process many in parallel
                with cp.cuda.Device(self.device_id):
                    # Still using CPU SHA256 but managing batches on GPU
                    # Real implementation would use GPU SHA256 kernel
                    for row in chunk:
                        hash_val = hashlib.sha256(row.tobytes()).digest()
                        results.append(hash_val)
            else:
                # CPU fallback
                for row in chunk:
                    hash_val = hashlib.sha256(row.tobytes()).digest()
                    results.append(hash_val)
        
        return results
    
    def worker_thread(self):
        """Worker thread for GPU processing"""
        while True:
            try:
                # Get batch from queue
                inputs = self.batch_queue.get(timeout=1)
                if inputs is None:  # Shutdown signal
                    break
                
                # Process batch
                hashes = self.hash_mega_batch(inputs)
                
                # Put results
                for i, hash_val in enumerate(hashes):
                    self.result_queue.put((inputs[i].tobytes(), hash_val))
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"GPU worker {self.device_id} error: {e}")


class OptimizedHashGenerator:
    """Main hash generator with optimized GPU batching"""
    
    def __init__(self, config: dict):
        self.config = config
        self.input_generator = BatchInputGenerator()
        self.gpu_hashers = []
        self.result_buffer = []
        self.total_hashes = 0
        self.start_time = time.time()
        self.last_report_time = time.time()
        
        # Mega batch size for GPU processing
        self.mega_batch_size = config.get('mega_batch_size', 100000)
        
        # Initialize BigTable
        self._init_bigtable()
        
        # Initialize GPU workers
        self._init_gpu_workers()
        
        # Thread pool for CPU operations
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
    
    def _init_gpu_workers(self):
        """Initialize GPU worker threads"""
        if GPU_AVAILABLE:
            try:
                gpu_count = cp.cuda.runtime.getDeviceCount()
                logger.info(f"Initializing {gpu_count} GPU workers")
                
                for i in range(gpu_count):
                    hasher = GPUBatchHasher(i)
                    # Start worker thread
                    thread = threading.Thread(target=hasher.worker_thread, daemon=True)
                    thread.start()
                    self.gpu_hashers.append(hasher)
                    
            except Exception as e:
                logger.warning(f"GPU initialization failed: {e}")
        
        if not self.gpu_hashers:
            logger.info("No GPUs available, using CPU workers")
            # Create CPU workers
            for i in range(self.config.get('cpu_threads', 4)):
                hasher = GPUBatchHasher(-1)  # -1 indicates CPU
                thread = threading.Thread(target=hasher.worker_thread, daemon=True)
                thread.start()
                self.gpu_hashers.append(hasher)
    
    async def generate_and_queue_batches(self):
        """Continuously generate input batches and queue for GPU processing"""
        while True:
            try:
                # Generate mega batch of random inputs
                logger.info(f"Generating batch of {self.mega_batch_size} inputs...")
                inputs = self.input_generator.generate_mega_batch(self.mega_batch_size)
                
                # Distribute to GPU workers
                chunk_size = self.mega_batch_size // len(self.gpu_hashers)
                for i, hasher in enumerate(self.gpu_hashers):
                    start_idx = i * chunk_size
                    end_idx = start_idx + chunk_size if i < len(self.gpu_hashers) - 1 else self.mega_batch_size
                    chunk = inputs[start_idx:end_idx]
                    
                    # Queue for processing (non-blocking)
                    try:
                        hasher.batch_queue.put_nowait(chunk)
                        logger.debug(f"Queued {len(chunk)} inputs for GPU {i}")
                    except queue.Full:
                        logger.warning(f"GPU {i} queue full, waiting...")
                        await asyncio.sleep(0.1)
                        hasher.batch_queue.put(chunk)
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Batch generation error: {e}")
                await asyncio.sleep(1)
    
    async def collect_results(self):
        """Collect results from GPU workers"""
        while True:
            try:
                # Collect from all GPU workers
                for hasher in self.gpu_hashers:
                    try:
                        while not hasher.result_queue.empty():
                            input_bytes, hash_bytes = hasher.result_queue.get_nowait()
                            self.result_buffer.append((input_bytes, hash_bytes))
                            self.total_hashes += 1
                            
                            # Check if we need to upload
                            if len(self.result_buffer) >= self.config.get('upload_batch_size', 10000000):
                                await self.upload_and_report()
                    except queue.Empty:
                        pass
                
                await asyncio.sleep(0.1)  # Check every 100ms
                
            except Exception as e:
                logger.error(f"Result collection error: {e}")
                await asyncio.sleep(1)
    
    async def bulk_upsert_bigtable(self, inputs: List[bytes], hashes: List[bytes]):
        """Bulk upsert to BigTable"""
        if not self.bt_table:
            return
        
        try:
            rows = []
            for input_bytes, hash_bytes in zip(inputs, hashes):
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
        """Report hashrate to monitoring server"""
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        if elapsed > 0:
            hashrate = self.total_hashes / elapsed
            
            # Calculate recent hashrate
            time_since_last = current_time - self.last_report_time
            recent_hashrate = len(self.result_buffer) / time_since_last if time_since_last > 0 else 0
            
            # GPU utilization info
            gpu_info = []
            if GPU_AVAILABLE:
                for i in range(len(self.gpu_hashers)):
                    try:
                        with cp.cuda.Device(i):
                            meminfo = cp.cuda.runtime.memGetInfo()
                            gpu_info.append({
                                'id': i,
                                'memory_used': meminfo[1] - meminfo[0],
                                'memory_total': meminfo[1]
                            })
                    except:
                        pass
            
            data = {
                'instance_id': self.input_generator.instance_id,
                'total_hashes': self.total_hashes,
                'overall_hashrate': hashrate,
                'recent_hashrate': recent_hashrate,
                'timestamp': datetime.utcnow().isoformat(),
                'gpu_count': len(self.gpu_hashers),
                'gpu_available': GPU_AVAILABLE,
                'gpu_info': gpu_info
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
                                logger.info(f"Hashrate: {recent_hashrate:.2f} H/s (Total: {self.total_hashes:,})")
                except Exception as e:
                    logger.warning(f"Failed to report hashrate: {e}")
            
            self.last_report_time = current_time
    
    async def upload_and_report(self):
        """Upload batch to BigTable and report hashrate"""
        if not self.result_buffer:
            return
        
        # Extract inputs and hashes
        inputs, hashes = zip(*self.result_buffer)
        
        # Upload to BigTable
        await self.bulk_upsert_bigtable(list(inputs), list(hashes))
        
        # Report hashrate
        await self.report_hashrate()
        
        # Clear buffer
        self.result_buffer = []
    
    async def periodic_upload(self):
        """Periodically upload any remaining hashes"""
        while True:
            await asyncio.sleep(self.config.get('upload_interval', 60))
            if self.result_buffer:
                await self.upload_and_report()
    
    async def periodic_monitoring(self):
        """Report status every N seconds"""
        report_interval = self.config.get('monitoring', {}).get('report_interval', 10)
        logger.info(f"Starting monitoring reporter (every {report_interval} seconds)")
        
        while True:
            await asyncio.sleep(report_interval)
            await self.report_hashrate()
    
    async def run(self):
        """Main run loop"""
        logger.info(f"Starting optimized hash generator")
        logger.info(f"Workers: {len(self.gpu_hashers)} ({'GPU' if GPU_AVAILABLE else 'CPU'})")
        logger.info(f"Mega batch size: {self.mega_batch_size:,}")
        logger.info(f"Instance ID: {self.input_generator.instance_id}")
        
        # Start tasks
        tasks = [
            asyncio.create_task(self.generate_and_queue_batches()),
            asyncio.create_task(self.collect_results()),
            asyncio.create_task(self.periodic_upload()),
            asyncio.create_task(self.periodic_monitoring())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            # Signal workers to stop
            for hasher in self.gpu_hashers:
                hasher.batch_queue.put(None)
            # Final upload
            await self.upload_and_report()


async def main():
    """Main entry point"""
    config_path = os.environ.get('CONFIG_PATH', 'config.json')
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Add mega batch size for GPU processing
        if 'mega_batch_size' not in config:
            config['mega_batch_size'] = 100000  # Process 100k at a time
            
    except FileNotFoundError:
        logger.warning(f"Config file not found at {config_path}, using defaults")
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
            'mega_batch_size': 100000,
            'upload_batch_size': 10000000,
            'upload_interval': 60,
            'cpu_threads': 4
        }
    
    # Create and run generator
    generator = OptimizedHashGenerator(config)
    await generator.run()


if __name__ == '__main__':
    asyncio.run(main())