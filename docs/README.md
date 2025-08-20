# Hash Generator Library - Complete Documentation

## Quick Navigation

### Core Documentation
- [**Index & Overview**](index.md) - Project overview and architecture
- [**Main Hash Generator**](hash_generator.md) - Primary implementation with all features
- [**Hash Generator Variants**](hash_generator_variants.md) - Different implementations for various use cases

### Infrastructure & Setup
- [**Bigtable Setup**](setup_bigtable.md) - Google Cloud Bigtable configuration
- [**GPU SHA256**](gpu_sha256.md) - GPU acceleration implementation

### Testing & Diagnostics
- [**Testing Utilities**](testing_utilities.md) - Complete testing suite documentation
- [**Bigtable Tests**](test_bigtable.md) - Storage backend testing
- [**GPU Detection**](test_gpu_detection.md) - GPU capability testing
- [**Query Utilities**](query_bigtable.md) - Data retrieval and export tools

## Documentation Structure

```
/docs/
├── README.md                    # This file - navigation guide
├── index.md                     # Project overview and architecture
├── hash_generator.md            # Main implementation documentation
├── hash_generator_variants.md   # All variant implementations
├── setup_bigtable.md           # Cloud storage setup
├── gpu_sha256.md               # GPU acceleration details
├── test_bigtable.md            # Storage testing documentation
├── test_gpu_detection.md       # GPU detection and testing
├── query_bigtable.md           # Query and export utilities
└── testing_utilities.md        # All testing tools documentation
```

## Quick Start Guide

### 1. Initial Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Setup Google Cloud credentials
export GOOGLE_APPLICATION_CREDENTIALS="path/to/credentials.json"

# Create Bigtable resources
python setup_bigtable.py
```

### 2. Test Environment
```bash
# Check GPU availability
python test_gpu_detection.py

# Test Bigtable connection
python test_bigtable.py

# Verify SHA256 implementation
python test_sha256.py
```

### 3. Run Hash Generator
```bash
# Basic execution
python hash_generator.py

# With monitoring
python hash_generator_monitored.py

# Rate-limited
python hash_generator_throttled.py
```

### 4. Query Data
```bash
# Query specific hash
python query_bigtable.py --hash "abc123..."

# Export data
python query_bigtable.py --export data.csv

# Get statistics
python query_bigtable.py --stats
```

## Module Categories

### Production Components
- `hash_generator.py` - Main production implementation
- `hash_generator_fixed.py` - Stable production version
- `hash_generator_fixed_upload.py` - Reliable upload mechanism
- `setup_bigtable.py` - Infrastructure setup

### Performance Components
- `gpu_sha256.py` - GPU acceleration
- `hash_generator_gpu.py` - GPU-optimized generator
- `hash_generator_gpu_nvidia.py` - NVIDIA-specific optimization
- `hash_generator_real_gpu.py` - Production GPU implementation

### Monitoring & Control
- `hash_generator_monitored.py` - Built-in monitoring
- `hash_generator_throttled.py` - Rate limiting
- `diagnose_monitoring.py` - Monitoring diagnostics

### Testing & Validation
- `test_sha256.py` - Algorithm validation
- `test_gpu_detection.py` - Hardware detection
- `test_gpu_access.py` - GPU functionality
- `test_bigtable.py` - Storage testing
- `test_hex_format.py` - Format validation
- `test_push_hash.py` - Upload testing
- `verify_binary_storage.py` - Storage integrity
- `verify_inside_container.py` - Container environment

### Utilities
- `query_bigtable.py` - Data retrieval
- `hash_generator_simple.py` - Basic implementation

## Performance Metrics

| Component | Performance | Hardware Required |
|-----------|------------|------------------|
| CPU Implementation | 10-50K hashes/sec | CPU only |
| GPU Implementation | 500K-1.5M hashes/sec | NVIDIA GPU |
| Bigtable Storage | 10K writes/sec | Cloud connection |
| Monitoring System | Real-time updates | Network access |

## System Requirements

### Minimum Requirements
- Python 3.7+
- 4GB RAM
- Internet connection (for cloud storage)
- Linux/Windows/macOS

### Recommended Requirements
- Python 3.9+
- 16GB RAM
- NVIDIA GPU (compute 6.0+)
- SSD storage
- Gigabit network

### GPU Requirements (Optional)
- NVIDIA GPU with CUDA support
- CUDA Toolkit 11.0+
- CuPy library
- 4GB+ GPU memory

## Environment Variables

```bash
# Google Cloud Configuration
export GCP_PROJECT_ID="your-project-id"
export BT_INSTANCE_ID="hash-generator-instance"
export BT_TABLE_NAME="hashes"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/credentials.json"

# GPU Configuration
export CUDA_VISIBLE_DEVICES="0,1"  # Select GPUs
export CUDA_DEVICE_ORDER="PCI_BUS_ID"

# Monitoring Configuration
export MONITORING_URL="http://monitoring.example.com"
export INSTANCE_ID="node-1"

# Performance Tuning
export BATCH_SIZE="10000"
export WORKER_THREADS="4"
export QUEUE_SIZE="100000"
```

## Troubleshooting

### Common Issues

#### GPU Not Detected
```bash
# Check CUDA installation
nvidia-smi

# Test GPU access
python test_gpu_detection.py --verbose

# Verify CuPy installation
python -c "import cupy; print(cupy.cuda.runtime.getDeviceCount())"
```

#### Bigtable Connection Failed
```bash
# Verify credentials
gcloud auth application-default login

# Test connection
python test_bigtable.py

# Check project configuration
gcloud config get-value project
```

#### Low Performance
```bash
# Run diagnostics
python diagnose_monitoring.py

# Check resource usage
htop  # or Task Manager on Windows

# Verify GPU utilization
nvidia-smi -l 1
```

## Support & Contributing

### Getting Help
- Check documentation in `/docs/` folder
- Review test outputs for diagnostics
- Enable verbose logging with `--verbose` flag

### Reporting Issues
1. Run diagnostic tests
2. Collect error logs
3. Include environment details
4. Provide reproduction steps

## License & Credits

This documentation was generated to provide comprehensive guidance for the Hash Generator Library. Each module is documented with its specific purpose, usage, and configuration options.