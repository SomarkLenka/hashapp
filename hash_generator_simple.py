#!/usr/bin/env python3
"""
Simple, working hash generator that actually generates random SHA256 hashes
No fancy GPU stuff until we fix the basic issue
"""

import asyncio
import hashlib
import secrets
import time
import os
import json
import socket
from typing import List, Tuple
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
import logging

from google.cloud import bigtable
from google.cloud.bigtable.row import DirectRow

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def hash_batch_cpu(batch_size: int) -> List[Tuple[bytes, bytes]]:
    """Generate random inputs and hash them"""
    results = []
    for _ in range(batch_size):
        # Generate truly random input
        random_bytes = secrets.token_bytes(32)
        
        # Hash the raw bytes (not hex string)
        hash_result = hashlib.sha256(random_bytes).digest()
        
        # Store as (input_hex, hash)
        results.append((random_bytes.hex().encode('utf-8'), hash_result))
    
    return results


class HashGenerator:
    """Simple hash generator that actually works"""
    
    def __init__(self, config: dict):
        self.config = config
        self.instance_id = f"{socket.gethostname()}_{int(time.time()*1000000)}_{secrets.token_hex(4)}"
        self.batch_buffer = []
        self.total_hashes = 0
        self.start_time = time.time()
        self.last_report_time = time.time()
        
        # Initialize BigTable
        self._init_bigtable()
        
        # Use process pool for parallel CPU hashing
        self.executor = ProcessPoolExecutor(max_workers=config.get('cpu_threads', 16))
    
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
            
            # Check if table exists
            if self.bt_table.exists():
                logger.info("BigTable connection initialized")
            else:
                logger.error(f"BigTable table '{self.config['bigtable']['table_name']}' does not exist!")
                self.bt_table = None
                
        except Exception as e:
            logger.error(f"Failed to initialize BigTable: {e}")
            self.bt_table = None
    
    async def bulk_upsert_bigtable(self, batch: List[Tuple[bytes, bytes]]):
        """Bulk upsert to BigTable"""
        if not self.bt_table:
            logger.warning("BigTable not available, skipping upload")
            return
        
        try:
            rows = []
            for input_hex, hash_bytes in batch:
                # Use hash as row key
                row = DirectRow(row_key=hash_bytes)
                row.set_cell(
                    column_family_id='hash_data',
                    column=b'input',
                    value=input_hex
                )
                rows.append(row)
            
            # Upload in chunks of 10000
            chunk_size = 10000
            for i in range(0, len(rows), chunk_size):
                chunk = rows[i:i+chunk_size]
                self.bt_table.mutate_rows(chunk)
                logger.info(f"Uploaded {len(chunk)} hashes to BigTable")
            
            # Log sample to verify randomness
            if batch:
                sample_hash = batch[0][1].hex()
                logger.info(f"Sample hash: {sample_hash} (should be random)")
            
        except Exception as e:
            logger.error(f"BigTable upload failed: {e}", exc_info=True)
    
    async def hash_worker(self, worker_id: int):
        """Worker that generates and hashes"""
        batch_size = 10000  # Process 10k at a time
        
        while True:
            try:
                # Generate and hash in parallel process
                loop = asyncio.get_event_loop()
                batch = await loop.run_in_executor(
                    self.executor,
                    hash_batch_cpu,
                    batch_size
                )
                
                # Add to buffer
                self.batch_buffer.extend(batch)
                self.total_hashes += len(batch)
                
                # Upload if buffer is large enough
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
        
        # Upload to BigTable
        batch_to_upload = self.batch_buffer[:1000000]  # Upload max 1M at a time
        await self.bulk_upsert_bigtable(batch_to_upload)
        
        # Remove uploaded items
        self.batch_buffer = self.batch_buffer[len(batch_to_upload):]
        
        # Report hashrate
        current_time = time.time()
        elapsed = current_time - self.start_time
        hashrate = self.total_hashes / elapsed if elapsed > 0 else 0
        
        logger.info(f"Hashrate: {hashrate/1000:.2f} KH/s | Total: {self.total_hashes:,}")
        
        if hashrate > 1000000:
            logger.info(f"Hashrate: {hashrate/1000000:.2f} MH/s")
        
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
        num_workers = self.config.get('cpu_threads', 16)
        logger.info(f"Starting CPU hash generator with {num_workers} workers")
        logger.info(f"Instance: {self.instance_id}")
        
        # Start workers
        workers = [
            asyncio.create_task(self.hash_worker(i))
            for i in range(num_workers)
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
            'upload_batch_size': 1000000,  # Upload 1M at a time
            'upload_interval': 60,  # Every minute
            'cpu_threads': 16  # Use 16 CPU threads
        }
    
    # Override with larger batch size
    config['upload_batch_size'] = 1000000
    config['upload_interval'] = 60
    config['cpu_threads'] = 16
    
    generator = HashGenerator(config)
    await generator.run()


if __name__ == '__main__':
    asyncio.run(main())