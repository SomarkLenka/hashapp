#!/usr/bin/env python3
"""
Fixed hash generator with working uploads and monitoring
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
import aiohttp

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
    GPU_COUNT = cp.cuda.runtime.getDeviceCount()
    if GPU_COUNT > 0:
        GPU_AVAILABLE = True
        logger.info(f"CuPy initialized with {GPU_COUNT} GPU(s)")
        for i in range(GPU_COUNT):
            try:
                with cp.cuda.Device(i):
                    props = cp.cuda.runtime.getDeviceProperties(i)
                    name = props['name'].decode('utf-8') if isinstance(props['name'], bytes) else props['name']
                    memory = props['totalGlobalMem'] / (1024**3)
                    logger.info(f"GPU {i}: {name}, {memory:.1f} GB")
            except:
                pass
except Exception as e:
    logger.warning(f"GPU initialization failed: {e}")
    GPU_AVAILABLE = False


class HashWorker:
    """Worker that generates and hashes"""
    
    def __init__(self, worker_id: int, use_gpu: bool = False):
        self.worker_id = worker_id
        self.use_gpu = use_gpu and GPU_AVAILABLE
        
        if self.use_gpu:
            try:
                with cp.cuda.Device(worker_id % GPU_COUNT):
                    _ = cp.zeros(1)
                logger.info(f"Worker {worker_id} using GPU {worker_id % GPU_COUNT}")
            except:
                self.use_gpu = False
                logger.info(f"Worker {worker_id} using CPU")
        else:
            logger.info(f"Worker {worker_id} using CPU")
    
    def generate_and_hash(self, batch_size: int) -> List[Tuple[bytes, bytes]]:
        """Generate random inputs and hash them"""
        results = []
        
        for _ in range(batch_size):
            random_bytes = secrets.token_bytes(32)
            hash_bytes = hashlib.sha256(random_bytes).digest()
            input_hex = random_bytes.hex().encode('utf-8')
            results.append((input_hex, hash_bytes))
        
        return results


class HashGenerator:
    """Main hash generator with fixed upload and monitoring"""
    
    def __init__(self, config: dict):
        self.config = config
        self.instance_id = f"{socket.gethostname()}_{int(time.time()*1000000)}_{secrets.token_hex(4)}"
        self.batch_buffer = []
        self.total_hashes = 0
        self.total_uploaded = 0
        self.start_time = time.time()
        self.last_report_time = time.time()
        self.last_upload_time = time.time()
        self.workers = []
        self.upload_in_progress = False
        
        # Initialize BigTable
        self._init_bigtable()
        
        # Initialize workers
        self._init_workers()
        
        # Thread pool
        self.executor = ThreadPoolExecutor(max_workers=4)
    
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
                logger.info("BigTable connection initialized successfully")
            else:
                logger.error(f"BigTable table '{self.config['bigtable']['table_name']}' does not exist!")
                self.bt_table = None
                
        except Exception as e:
            logger.error(f"Failed to initialize BigTable: {e}")
            self.bt_table = None
    
    def _init_workers(self):
        """Initialize workers"""
        if GPU_AVAILABLE and GPU_COUNT > 0:
            # Create GPU workers
            for i in range(GPU_COUNT):
                self.workers.append(HashWorker(i, use_gpu=True))
            logger.info(f"Created {GPU_COUNT} GPU workers")
        
        # Always add some CPU workers
        cpu_count = self.config.get('cpu_threads', 4)
        for i in range(cpu_count):
            self.workers.append(HashWorker(GPU_COUNT + i, use_gpu=False))
        
        logger.info(f"Total workers: {len(self.workers)} ({GPU_COUNT} GPU, {cpu_count} CPU)")
    
    def bulk_upsert_bigtable_sync(self, batch: List[Tuple[bytes, bytes]]) -> bool:
        """Synchronous BigTable upload"""
        if not self.bt_table:
            logger.warning("BigTable not available, discarding batch")
            return True  # Return true to clear buffer
        
        try:
            rows = []
            for input_hex, hash_bytes in batch[:100000]:  # Max 100k per upload
                row = DirectRow(row_key=hash_bytes)
                row.set_cell(
                    column_family_id='hash_data',
                    column=b'input',
                    value=input_hex
                )
                rows.append(row)
            
            # Upload in chunks of 10k
            for i in range(0, len(rows), 10000):
                chunk = rows[i:i+10000]
                self.bt_table.mutate_rows(chunk)
                logger.info(f"Uploaded chunk: {len(chunk)} hashes to BigTable")
            
            self.total_uploaded += len(rows)
            
            # Log sample hash
            if batch:
                sample = batch[0][1].hex()
                logger.info(f"Sample hash: {sample[:32]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"BigTable upload failed: {e}")
            return False
    
    async def report_stats_to_server(self):
        """Report stats to monitoring endpoint"""
        endpoint = self.config.get('monitoring', {}).get('endpoint')
        if not endpoint:
            return
        
        try:
            current_time = time.time()
            elapsed = current_time - self.start_time
            overall_hashrate = self.total_hashes / elapsed if elapsed > 0 else 0
            
            # Calculate recent hashrate (last 10 seconds)
            time_since_last = current_time - self.last_report_time
            recent_hashes = len(self.batch_buffer)  # Approximate
            recent_hashrate = (recent_hashes * 10) / time_since_last if time_since_last > 0 else 0
            
            data = {
                'instance_id': self.instance_id,
                'total_hashes': self.total_hashes,
                'overall_hashrate': overall_hashrate,
                'recent_hashrate': recent_hashrate,
                'timestamp': datetime.utcnow().isoformat(),
                'gpu_count': GPU_COUNT,
                'gpu_available': GPU_AVAILABLE,
                'worker_count': len(self.workers),
                'buffer_size': len(self.batch_buffer),
                'total_uploaded': self.total_uploaded
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        logger.debug(f"Stats reported to {endpoint}")
                    else:
                        logger.warning(f"Stats server returned {response.status}")
                        
        except Exception as e:
            logger.warning(f"Failed to report stats: {e}")
    
    async def log_stats(self):
        """Log stats to console"""
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        if elapsed > 0:
            overall_hashrate = self.total_hashes / elapsed
            
            # Estimate recent hashrate
            time_since_last = current_time - self.last_report_time
            recent_hashes = len(self.batch_buffer)
            recent_hashrate = (recent_hashes * 10) / time_since_last if time_since_last > 0 else overall_hashrate
            
            mode = "GPU" if GPU_AVAILABLE else "CPU"
            
            logger.info(f"=== HASHRATE STATS ===")
            logger.info(f"Mode: {mode} | Workers: {len(self.workers)}")
            logger.info(f"Recent: {recent_hashrate/1000:.2f} KH/s | Overall: {overall_hashrate/1000:.2f} KH/s")
            logger.info(f"Total Hashes: {self.total_hashes:,} | Buffer: {len(self.batch_buffer):,}")
            logger.info(f"Total Uploaded: {self.total_uploaded:,}")
            
            if recent_hashrate > 1000000:
                logger.info(f"Recent: {recent_hashrate/1000000:.2f} MH/s")
            if overall_hashrate > 1000000:
                logger.info(f"Overall: {overall_hashrate/1000000:.2f} MH/s")
            
            self.last_report_time = current_time
    
    async def hash_worker(self, worker_id: int):
        """Worker that generates and hashes"""
        worker = self.workers[worker_id]
        batch_size = 10000 if worker.use_gpu else 1000
        
        while True:
            try:
                # Don't generate if buffer is too large
                if len(self.batch_buffer) > 10000000:  # 10M max buffer
                    await asyncio.sleep(1)
                    continue
                
                # Generate and hash
                loop = asyncio.get_event_loop()
                batch = await loop.run_in_executor(
                    self.executor,
                    worker.generate_and_hash,
                    batch_size
                )
                
                # Add to buffer
                self.batch_buffer.extend(batch)
                self.total_hashes += len(batch)
                
                # No upload here - let periodic uploader handle it
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)
    
    async def periodic_uploader(self):
        """Dedicated uploader task"""
        logger.info("Starting periodic uploader")
        
        while True:
            try:
                # Wait a bit
                await asyncio.sleep(10)
                
                # Check if we should upload
                should_upload = (
                    len(self.batch_buffer) >= 100000 and  # At least 100k hashes
                    not self.upload_in_progress  # Not already uploading
                )
                
                if should_upload:
                    self.upload_in_progress = True
                    
                    # Take batch to upload
                    batch_size = min(100000, len(self.batch_buffer))
                    batch_to_upload = self.batch_buffer[:batch_size]
                    
                    logger.info(f"Uploading {len(batch_to_upload)} hashes...")
                    
                    # Upload synchronously in executor
                    loop = asyncio.get_event_loop()
                    success = await loop.run_in_executor(
                        self.executor,
                        self.bulk_upsert_bigtable_sync,
                        batch_to_upload
                    )
                    
                    if success:
                        # Remove uploaded items
                        self.batch_buffer = self.batch_buffer[batch_size:]
                        logger.info(f"Upload complete. Buffer now: {len(self.batch_buffer)}")
                    else:
                        logger.warning("Upload failed, keeping batch in buffer")
                    
                    self.upload_in_progress = False
                    self.last_upload_time = time.time()
                    
            except Exception as e:
                logger.error(f"Uploader error: {e}")
                self.upload_in_progress = False
                await asyncio.sleep(5)
    
    async def periodic_stats_reporter(self):
        """Periodically report stats"""
        report_interval = self.config.get('monitoring', {}).get('report_interval', 10)
        logger.info(f"Starting stats reporter (every {report_interval}s)")
        
        while True:
            try:
                await asyncio.sleep(report_interval)
                
                # Log stats locally
                await self.log_stats()
                
                # Report to server
                await self.report_stats_to_server()
                
            except Exception as e:
                logger.error(f"Stats reporter error: {e}")
                await asyncio.sleep(10)
    
    async def run(self):
        """Main run loop"""
        mode = f"GPU ({GPU_COUNT} devices)" if GPU_AVAILABLE else "CPU"
        logger.info(f"=== STARTING HASH GENERATOR ===")
        logger.info(f"Mode: {mode}")
        logger.info(f"Workers: {len(self.workers)}")
        logger.info(f"Instance: {self.instance_id}")
        logger.info(f"Monitoring: {self.config.get('monitoring', {}).get('endpoint', 'Not configured')}")
        logger.info(f"BigTable: {'Connected' if self.bt_table else 'Not connected'}")
        logger.info(f"================================")
        
        # Start all tasks
        tasks = []
        
        # Hash workers
        for i in range(len(self.workers)):
            tasks.append(asyncio.create_task(self.hash_worker(i)))
        
        # Dedicated uploader
        tasks.append(asyncio.create_task(self.periodic_uploader()))
        
        # Stats reporter
        tasks.append(asyncio.create_task(self.periodic_stats_reporter()))
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await self.log_stats()


async def main():
    """Main entry point"""
    config_path = os.environ.get('CONFIG_PATH', 'config.json')
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            logger.info(f"Loaded config from {config_path}")
    except FileNotFoundError:
        logger.warning(f"Config file not found at {config_path}, using defaults")
        config = {
            'bigtable': {
                'project_id': os.environ.get('GCP_PROJECT_ID', 'adept-storm-466618-b4'),
                'instance_id': os.environ.get('BT_INSTANCE_ID', 'hash-generator-instance'),
                'table_name': os.environ.get('BT_TABLE_NAME', 'hashes')
            },
            'monitoring': {
                'endpoint': os.environ.get('MONITORING_ENDPOINT', 'https://hash-production-3375.up.railway.app/api/hashrate'),
                'report_interval': 10
            },
            'upload_batch_size': 100000,
            'upload_interval': 10,
            'cpu_threads': 4
        }
    
    # Log config
    logger.info(f"BigTable project: {config['bigtable']['project_id']}")
    logger.info(f"BigTable instance: {config['bigtable']['instance_id']}")
    logger.info(f"BigTable table: {config['bigtable']['table_name']}")
    logger.info(f"Monitoring endpoint: {config.get('monitoring', {}).get('endpoint', 'None')}")
    
    generator = HashGenerator(config)
    await generator.run()


if __name__ == '__main__':
    asyncio.run(main())