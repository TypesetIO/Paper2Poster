# Paper2Poster API Quick Start Guide

This guide helps you quickly get the Paper2Poster API service up and running.

## Prerequisites

- Python 3.8 or higher
- CUDA-capable GPU (recommended) or CPU
- At least 8GB RAM (16GB recommended)
- ~5GB disk space for models

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Starting the API Service

### Method 1: Using the Startup Script (Recommended)

The startup script handles model pre-loading and proper multi-worker configuration:

```bash
# Start with default settings (3 workers, port 6025)
python start_api.py

# Custom configuration
python start_api.py --host 0.0.0.0 --port 8080 --workers 4

# Development mode with auto-reload
python start_api.py --reload --workers 1

# Skip model pre-download (models will download on first use)
python start_api.py --skip-model-download
```

### Method 2: Direct API Start

```bash
# Simple start (single worker)
python api_service.py

# Or with uvicorn directly (3 workers)
uvicorn api_service:app --host 0.0.0.0 --port 6025 --workers 3
```

## Pre-downloading Models

To avoid delays during first request, you can pre-download all models:

```bash
python download_models.py
```

This will download:
- Docling models for PDF parsing
- Marker models (fallback PDF parser)
- All required dependencies

**Note**: This process takes 10-30 minutes on first run depending on your internet speed.

## Testing the Service

Once the service is running, you can test it:

```bash
# Check if service is healthy
curl http://localhost:6025/health

# Run the test client
python test_api.py --pdf path/to/paper.pdf --output-dir ./output
```

## API Endpoints

- `GET /` - Welcome message and available endpoints
- `GET /health` - Health check
- `POST /generate-poster` - Generate poster from PDF
- `GET /jobs/{job_id}` - Check job status
- `GET /download/{job_id}` - Download generated poster
- `GET /docs` - Interactive API documentation

## Performance Tips

1. **Use GPU**: The service runs much faster with a CUDA-capable GPU
2. **Pre-download models**: Run `python download_models.py` before starting the service
3. **Multiple workers**: Use 3-4 workers for better throughput
4. **Adequate RAM**: Ensure at least 8GB RAM available

## Troubleshooting

### "I/O operation on closed file" error
This has been fixed in the latest version. Make sure you're using the updated `api_service.py`.

### Models downloading on every request
Run `python download_models.py` once to cache all models locally.

### Out of memory errors
- Reduce number of workers
- Ensure adequate RAM/GPU memory
- Try CPU mode if GPU memory is limited

### Service won't start
- Check Python version (3.8+ required)
- Verify all dependencies are installed
- Check if port 6025 is available

## Docker Usage

For Docker deployment, see [DOCKER_README.md](DOCKER_README.md). 