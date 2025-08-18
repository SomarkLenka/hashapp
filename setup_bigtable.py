#!/usr/bin/env python3
"""
Setup script to create BigTable instance and table for hash storage
"""

import os
import sys
from google.cloud import bigtable
from google.cloud.bigtable import column_family
from google.cloud.bigtable import row_filters

def create_bigtable_resources(project_id, instance_id, table_name, recreate_table=False):
    """Create BigTable instance and table with appropriate schema"""
    
    # Create client
    client = bigtable.Client(project=project_id, admin=True)
    
    # Check if instance exists
    instance = client.instance(instance_id)
    
    if not instance.exists():
        print(f"Creating instance {instance_id}...")
        # Create instance with production configuration
        from google.cloud.bigtable import enums
        
        # Create cluster configuration
        cluster = instance.cluster(
            cluster_id='cluster-main',
            location_id='us-central1-a',
            serve_nodes=3,  # Minimum for production
            default_storage_type=enums.StorageType.SSD
        )
        
        # Create production instance with cluster
        operation = instance.create(
            clusters=[cluster]
        )
        operation.result(timeout=300)
        print(f"Instance {instance_id} created")
    else:
        print(f"Instance {instance_id} already exists")
    
    # Create table
    table = instance.table(table_name)
    
    # Handle table recreation if requested
    if recreate_table and table.exists():
        print(f"Deleting existing table {table_name}...")
        table.delete()
        print(f"Table {table_name} deleted")
    
    if not table.exists():
        print(f"Creating table {table_name}...")
        
        # Define column families with GC rule
        max_versions_rule = column_family.MaxVersionsGCRule(1)
        
        # Create table with column family
        table.create(column_families={'hash_data': max_versions_rule})
        print(f"Table {table_name} created with column family 'hash_data'")
    else:
        print(f"Table {table_name} already exists")
    
    return True

def main():
    """Main setup function"""
    # Get configuration from environment or use defaults
    project_id = os.environ.get('GCP_PROJECT_ID', 'adept-storm-466618-b4')
    instance_id = os.environ.get('BT_INSTANCE_ID', 'hash-generator-instance')
    table_name = os.environ.get('BT_TABLE_NAME', 'hashes')
    
    # Check for --recreate-table flag
    recreate_table = '--recreate-table' in sys.argv
    
    if project_id == 'your-project-id':
        print("Error: Please set GCP_PROJECT_ID environment variable")
        sys.exit(1)
    
    print(f"Setting up BigTable resources...")
    print(f"Project: {project_id}")
    print(f"Instance: {instance_id}")
    print(f"Table: {table_name}")
    if recreate_table:
        print("WARNING: Will recreate table if it exists!")
    
    try:
        create_bigtable_resources(project_id, instance_id, table_name, recreate_table)
        print("\nSetup completed successfully!")
        print("\nTable schema:")
        print("  Row Key: SHA256 hash (for fast lookups)")
        print("  Column Family: hash_data")
        print("    - input: The original input value")
    except Exception as e:
        print(f"Error during setup: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()