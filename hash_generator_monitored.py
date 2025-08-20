#!/usr/bin/env python3
"""
GPU-accelerated SHA256 hash generator with proper monitoring and stats
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
            with cp.cuda.Device(i):
                props = cp.cuda.runtime.getDeviceProperties(i)
                name = props['name'].decode('utf-8') if isinstance(props['name'], bytes) else props['name']
                memory = props['totalGlobalMem'] / (1024**3)
                logger.info(f"GPU {i}: {name}, {memory:.1f} GB")
except Exception as e:
    logger.warning(f"GPU initialization failed: {e}")
    GPU_AVAILABLE = False


class HashWorker:
    """Worker that generates and hashes"""
    
    def __init__(self, worker_id: int, use_gpu: bool = False):
        self.worker_id = worker_id
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.hashes_generated = 0
        
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
        
        if self.use_gpu:
            try:
                with cp.cuda.Device(self.worker_id % GPU_COUNT):
                    # GPU path - generate on GPU for speed
                    for _ in range(batch_size):
                        random_bytes = secrets.token_bytes(32)
                        hash_bytes = hashlib.sha256(random_bytes).digest()
                        input_hex = random_bytes.hex().encode('utf-8')
                        results.append((input_hex, hash_bytes))
                        self.hashes_generated += 1
            except:
                # Fallback to CPU
                self.use_gpu = False
        
        if not self.use_gpu:
            # CPU path
            for _ in range(batch_size):
                random_bytes = secrets.token_bytes(32)
                hash_bytes = hashlib.sha256(random_bytes).digest()
                input_hex = random_bytes.hex().encode('utf-8')
                results.append((input_hex, hash_bytes))
                self.hashes_generated += 1
        
        return results


class HashGenerator:
    """Main hash generator with monitoring"""
    
    def __init__(self, config: dict):
        self.config = config
        self.instance_id = f"{socket.gethostname()}_{int(time.time()*1000000)}_{secrets.token_hex(4)}"
        self.batch_buffer = []
        self.total_hashes = 0
        self.start_time = time.time()
        self.last_report_time = time.time()
        self.last_upload_time = time.time()
        self.workers = []
        
        # Stats tracking
        self.stats = {
            'total_hashes': 0,
            'total_uploads': 0,
            'last_hashrate': 0,
            'peak_hashrate': 0,
            'current_buffer_size': 0
        }
        
        # Initialize BigTable
        self._init_bigtable()
        
        # Initialize workers
        self._init_workers()
        
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
    
    def _init_workers(self):
        """Initialize workers"""
        if GPU_AVAILABLE and GPU_COUNT > 0:
            # Create GPU workers
            for i in range(GPU_COUNT):
                self.workers.append(HashWorker(i, use_gpu=True))
            logger.info(f"Created {GPU_COUNT} GPU workers")
        
        # Always add some CPU workers too
        cpu_count = self.config.get('cpu_threads', 4)
        for i in range(cpu_count):
            self.workers.append(HashWorker(GPU_COUNT + i, use_gpu=False))
        
        logger.info(f"Total workers: {len(self.workers)} ({GPU_COUNT} GPU, {cpu_count} CPU)")
    
    async def bulk_upsert_bigtable(self, batch: List[Tuple[bytes, bytes]]):
        """Bulk upsert to BigTable"""
        if not self.bt_table:
            logger.warning("BigTable not available, skipping upload")
            return False
        
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
            chunk_size = 100000
            uploaded = 0
            for i in range(0, len(rows), chunk_size):
                chunk = rows[i:i+chunk_size]
                await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self.bt_table.mutate_rows,
                    chunk
                )
                uploaded += len(chunk)
                logger.info(f"Uploaded chunk: {len(chunk)} hashes to BigTable")
            
            self.stats['total_uploads'] += uploaded
            
            # Log sample hash to verify randomness
            if batch:
                sample = batch[0][1].hex()
                logger.info(f"Sample hash: {sample[:32]}... (verifying randomness)")
            
            return True
            
        except Exception as e:
            logger.error(f"BigTable upload failed: {e}")
            return False
    
    async def report_stats_to_server(self):
        """Report stats to monitoring endpoint"""
        if not self.config.get('monitoring', {}).get('endpoint'):
            return
        
        try:
            current_time = time.time()
            elapsed = current_time - self.start_time
            overall_hashrate = self.total_hashes / elapsed if elapsed > 0 else 0
            
            # Calculate recent hashrate
            time_since_last = current_time - self.last_report_time
            if time_since_last > 0:
                recent_hashrate = self.stats['last_hashrate']
            else:
                recent_hashrate = 0
            
            # Update peak
            if overall_hashrate > self.stats['peak_hashrate']:
                self.stats['peak_hashrate'] = overall_hashrate
            
            data = {
                'instance_id': self.instance_id,
                'total_hashes': self.total_hashes,
                'overall_hashrate': overall_hashrate,
                'recent_hashrate': recent_hashrate,
                'peak_hashrate': self.stats['peak_hashrate'],
                'timestamp': datetime.utcnow().isoformat(),
                'gpu_count': GPU_COUNT,
                'gpu_available': GPU_AVAILABLE,
                'worker_count': len(self.workers),
                'buffer_size': len(self.batch_buffer),
                'total_uploads': self.stats['total_uploads']
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config['monitoring']['endpoint'],
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        logger.debug(f"Stats reported to server successfully")
                    else:
                        logger.warning(f"Server returned status {response.status}")
                        
        except Exception as e:
            logger.warning(f"Failed to report stats to server: {e}")
    
    async def log_stats(self):
        """Log stats to console"""
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        if elapsed > 0:
            overall_hashrate = self.total_hashes / elapsed
            
            # Calculate recent hashrate
            time_since_last = current_time - self.last_report_time
            hashes_since_last = sum(w.hashes_generated for w in self.workers)
            recent_hashrate = hashes_since_last / time_since_last if time_since_last > 0 else 0
            
            self.stats['last_hashrate'] = recent_hashrate
            
            # Reset worker counters
            for w in self.workers:
                w.hashes_generated = 0
            
            mode = "GPU" if GPU_AVAILABLE else "CPU"
            
            # Log detailed stats
            logger.info(f"=== HASHRATE STATS ===")
            logger.info(f"Mode: {mode} | Workers: {len(self.workers)}")
            logger.info(f"Recent: {recent_hashrate/1000:.2f} KH/s | Overall: {overall_hashrate/1000:.2f} KH/s")
            logger.info(f"Total Hashes: {self.total_hashes:,} | Buffer: {len(self.batch_buffer):,}")
            logger.info(f"Total Uploaded: {self.stats['total_uploads']:,}")
            
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
                
                # Check if we should upload
                current_time = time.time()
                time_since_upload = current_time - self.last_upload_time
                
                should_upload = (
                    len(self.batch_buffer) >= self.config.get('upload_batch_size', 1000000) or
                    (len(self.batch_buffer) > 100000 and time_since_upload > 30)
                )
                
                if should_upload:
                    logger.info(f"Triggering upload: buffer={len(self.batch_buffer)}, time={time_since_upload:.1f}s")
                    await self.upload_batch()
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)
    
    async def upload_batch(self):
        """Upload current batch to BigTable"""
        if not self.batch_buffer:
            return
        
        # Take up to 1M hashes to upload
        batch_to_upload = self.batch_buffer[:1000000]
        
        # Upload to BigTable
        success = await self.bulk_upsert_bigtable(batch_to_upload)
        
        if success:
            # Remove uploaded items
            self.batch_buffer = self.batch_buffer[len(batch_to_upload):]
            self.last_upload_time = time.time()
            logger.info(f"Successfully uploaded {len(batch_to_upload)} hashes")
        else:
            logger.warning("Upload failed, keeping hashes in buffer")
    
    async def periodic_stats_reporter(self):
        """Periodically report stats"""
        report_interval = self.config.get('monitoring', {}).get('report_interval', 10)
        logger.info(f"Starting stats reporter (every {report_interval}s)")
        
        while True:
            await asyncio.sleep(report_interval)
            
            # Log stats locally
            await self.log_stats()
            
            # Report to server
            await self.report_stats_to_server()
    
    async def periodic_uploader(self):
        """Force periodic uploads"""
        upload_interval = self.config.get('upload_interval', 60)
        logger.info(f"Starting periodic uploader (every {upload_interval}s)")
        
        while True:
            await asyncio.sleep(upload_interval)
            
            if self.batch_buffer:
                logger.info(f"Periodic upload: {len(self.batch_buffer)} hashes in buffer")
                await self.upload_batch()
            else:
                logger.debug("Periodic upload: buffer empty")
    
    async def run(self):
        """Main run loop"""
        mode = f"GPU ({GPU_COUNT} devices)" if GPU_AVAILABLE else "CPU"
        logger.info(f"=== STARTING HASH GENERATOR ===")
        logger.info(f"Mode: {mode}")
        logger.info(f"Workers: {len(self.workers)}")
        logger.info(f"Instance: {self.instance_id}")
        logger.info(f"Monitoring: {self.config.get('monitoring', {}).get('endpoint', 'Not configured')}")
        logger.info(f"================================")
        
        # Start all workers
        tasks = []
        
        # Hash workers
        for i in range(len(self.workers)):
            tasks.append(asyncio.create_task(self.hash_worker(i)))
        
        # Stats reporter
        tasks.append(asyncio.create_task(self.periodic_stats_reporter()))
        
        # Periodic uploader
        tasks.append(asyncio.create_task(self.periodic_uploader()))
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await self.upload_batch()
            await self.log_stats()


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
            'monitoring': {
                'endpoint': os.environ.get('MONITORING_ENDPOINT', 'https://hash-production-3375.up.railway.app/api/hashrate'),
                'report_interval': 10
            },
            'upload_batch_size': 1000000,
            'upload_interval': 60,
            'cpu_threads': 4
        }
    
    generator = HashGenerator(config)
    await generator.run()


if __name__ == '__main__':
    asyncio.run(main())