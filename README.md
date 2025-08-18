# Asynchronous SHA256 Hash Generator with GPU Support

A high-performance SHA256 hash generator with GPU acceleration, Google BigTable integration, and distributed processing capabilities.

## Features

- **Asynchronous Processing**: Efficient async/await pattern for maximum throughput
- **GPU Acceleration**: Auto-detects and utilizes all available NVIDIA GPUs
- **Sparse Input Generation**: Unique algorithm ensuring 90%+ different hashes between instances
- **BigTable Integration**: Batch uploads every 1000 hashes to Google BigTable
- **Real-time Monitoring**: Posts hashrate to designated web server
- **Docker Support**: Fully containerized with GPU passthrough
- **Auto-parallelization**: Distributes work across all detected GPUs/CPUs

## Architecture

### Input Generation Strategy
The system uses multiple entropy sources to generate sparse, well-distributed inputs:
- Instance-specific ID (hostname + timestamp + random)
- Non-linear counter progression (multiplicative congruential generator)
- Time-based entropy (nanosecond precision)
- Cryptographically secure random bytes
- Combined via SHA256 for 32-byte inputs

This ensures maximum coverage of the hash space with minimal overlap between instances.

## Prerequisites

- Docker and Docker Compose
- NVIDIA GPU with CUDA 12.x support (optional, falls back to CPU)
- Google Cloud account with BigTable API enabled
- Service account key with BigTable permissions

## Setup

### 1. Clone and Configure

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 2. Google Cloud Setup

```bash
# Set up authentication
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Create BigTable resources
python setup_bigtable.py
```

### 3. Build and Run

```bash
# Build the Docker image
docker-compose build

# Run the container
docker-compose up -d

# View logs
docker-compose logs -f hash-generator
```

## Configuration

Edit `config.json` or use environment variables:

```json
{
  "bigtable": {
    "project_id": "your-project-id",
    "instance_id": "your-instance-id",
    "table_name": "hashes"
  },
  "monitoring": {
    "endpoint": "http://your-server/api/hashrate"
  },
  "batch_size": 100,
  "upload_batch_size": 1000,
  "upload_interval": 10
}
```

## Performance Tuning

- **batch_size**: Number of hashes per GPU batch (default: 100)
- **upload_batch_size**: Hashes to accumulate before BigTable upload (default: 1000)
- **cpu_threads**: Thread pool size for CPU operations (default: 4)
- **CUDA_VISIBLE_DEVICES**: Control GPU visibility (default: all)

## Monitoring

The system posts hashrate data to your monitoring endpoint:

```json
{
  "instance_id": "unique-instance-id",
  "total_hashes": 1000000,
  "overall_hashrate": 50000.5,
  "recent_hashrate": 52000.3,
  "timestamp": "2024-01-20T10:30:00Z",
  "gpu_count": 4,
  "gpu_available": true
}
```

## BigTable Schema

Table: `hashes`
- **Row Key**: 2-byte SHA1 prefix + 30-byte input (for distribution)
- **Column Family**: `hash_data`
  - `sha256`: 32-byte hash value
  - `input`: Original 32-byte input
  - `timestamp`: Unix timestamp

## Security Notes

- Container runs as non-root user
- Service account key should be mounted read-only
- Use secrets management for production deployments

## Scaling

To run multiple instances:
```bash
# Instance 1
docker-compose up -d

# Instance 2 (different host)
docker-compose up -d
```

Each instance generates unique sparse inputs with 90%+ different coverage.

## Development

```bash
# Install dependencies locally
pip install -r requirements.txt

# Run without Docker
python hash_generator.py
```

## License

MIT"# hash" 
