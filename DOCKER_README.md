# Paper2Poster API Docker Setup

This guide will help you set up and run the Paper2Poster FastAPI service using Docker and Docker Compose.

## Prerequisites

- Docker and Docker Compose installed on your system
- NVIDIA Docker runtime (if using local GPU models with vLLM)
- API keys for AI services (OpenAI, Anthropic, etc.)
- 5GB+ free disk space for OCR/parsing models (downloaded on first run)

## Quick Start

### 1. Environment Setup

Copy the example environment file and configure your API keys:

```bash
cp env.example .env
```

Edit `.env` and add your API keys:
```bash
OPENAI_API_KEY=your_actual_openai_api_key
# Add other API keys as needed
```

### 2. Create Required Directories

```bash
mkdir -p input_papers output_posters model_cache
```

### 3. Build and Run the API Service

```bash
# Build and start the API service
docker-compose up -d

# Check if the service is running
docker-compose ps

# Monitor the startup logs (first run will download models)
docker-compose logs -f paper2poster

# Check service health
curl http://localhost:6025/health

# View API documentation
open http://localhost:6025/docs
```

**Note on First Run**: On the first container startup, the service will automatically download required OCR and parsing models (Docling and Marker). This process takes 10-30 minutes depending on your internet speed. The models are cached in the `model_cache` volume and won't need to be downloaded again.

To skip model download (not recommended for production):
```bash
# Set environment variable to skip model download
SKIP_MODEL_DOWNLOAD=true docker-compose up -d
```

The FastAPI service will be available at:
- **API Endpoint**: http://localhost:6025
- **Interactive Docs**: http://localhost:6025/docs
- **ReDoc**: http://localhost:6025/redoc

## API Usage Examples

### Generate a Poster from PDF using REST API

#### Method 1: Using curl (Command Line)

```bash
# Generate a poster using the REST API
curl -X POST "http://localhost:6025/generate-poster" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "pdf_file=@/path/to/your/paper.pdf" \
  -F "model_name_t=4o" \
  -F "model_name_v=4o" \
  -F "poster_width_inches=48" \
  -F "poster_height_inches=36"

# Response will include a job_id like:
# {"job_id":"abc123...","message":"Poster generation started","status":"queued"}
```

#### Method 2: Using the Interactive API Documentation

1. Navigate to http://localhost:6025/docs
2. Click on "POST /generate-poster"
3. Click "Try it out"
4. Upload your PDF file and set parameters
5. Click "Execute"

#### Method 3: Using Python requests

```python
import requests
import time

# Upload and start poster generation
with open('/path/to/your/paper.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:6025/generate-poster',
        files={'pdf_file': f},
        data={
            'model_name_t': '4o',
            'model_name_v': '4o',
            'poster_width_inches': 48,
            'poster_height_inches': 36
        }
    )

job_id = response.json()['job_id']
print(f"Job started: {job_id}")

# Check job status
while True:
    status_response = requests.get(f'http://localhost:6025/jobs/{job_id}')
    status = status_response.json()
    print(f"Status: {status['status']} - {status['progress']}")
    
    if status['status'] in ['completed', 'failed']:
        break
    time.sleep(10)

# Download the generated poster
if status['status'] == 'completed':
    poster_response = requests.get(f'http://localhost:6025/download/{job_id}?file_type=pptx')
    with open('generated_poster.pptx', 'wb') as f:
        f.write(poster_response.content)
    print("Poster downloaded successfully!")
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information and available endpoints |
| `/health` | GET | Health check endpoint |
| `/generate-poster` | POST | Upload PDF and start poster generation |
| `/jobs/{job_id}` | GET | Get job status and progress |
| `/jobs` | GET | List all jobs (admin) |
| `/download/{job_id}` | GET | Download generated poster files |
| `/jobs/{job_id}` | DELETE | Delete a job |

### Job Status Monitoring

```bash
# Check job status
curl http://localhost:6025/jobs/{job_id}

# List all jobs
curl http://localhost:6025/jobs

# Download poster (PPTX format)
curl -O -J http://localhost:6025/download/{job_id}?file_type=pptx

# Download poster (PNG format)
curl -O -J http://localhost:6025/download/{job_id}?file_type=png
```

### Using Local Models (vLLM)

1. Start the vLLM services:
```bash
docker-compose --profile vllm up -d
```

2. Generate poster with local models via API:
```bash
curl -X POST "http://localhost:6025/generate-poster" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "pdf_file=@/path/to/your/paper.pdf" \
  -F "model_name_t=vllm_qwen" \
  -F "model_name_v=vllm_qwen_vl" \
  -F "poster_width_inches=48" \
  -F "poster_height_inches=36"
```

### Legacy Command Line Interface (Optional)

You can still access the original command-line interface if needed:

```bash
# Access container shell
docker-compose exec paper2poster bash

# Run original pipeline
python -m PosterAgent.new_pipeline \
    --poster_path=/app/input_papers/my_paper/paper.pdf \
    --model_name_t="4o" \
    --model_name_v="4o"

# Create evaluation dataset
python -m PosterAgent.create_dataset

# Evaluate posters
python -m Paper2Poster-eval.eval_poster_pipeline \
    --paper_name="my_paper" \
    --poster_method="4o_4o_generated_posters" \
    --metric=qa
```

## Service Profiles

### Default Profile
- `paper2poster`: Main application container

### vLLM Profile (for local models)
- `vllm-server`: Text generation model server (Qwen2.5-7B-Instruct)
- `vllm-vl-server`: Vision-language model server (Qwen2.5-VL-7B-Instruct)

Start vLLM services:
```bash
docker-compose --profile vllm up -d
```

## Directory Structure

```
Paper2Poster/
├── input_papers/          # Place your PDF papers here
│   └── paper_name/
│       └── paper.pdf
├── output_posters/        # Generated posters will appear here
├── model_cache/           # Cached models (OCR/parsing models + vLLM)
│   └── .models_downloaded # Marker file indicating models are downloaded
├── tmp/                   # Temporary files
├── contents/              # Parsed paper contents
├── tree_splits/           # Layout information
├── <4o_4o>_images_and_tables/     # Extracted images and tables
├── <4o_4o>_generated_posters/     # Final generated posters
└── .env                   # Your API keys and configuration
```

## Model Options

### Text Models (`--model_name_t`)
- `4o`: GPT-4o (requires OpenAI API key)
- `4o-mini`: GPT-4o Mini (requires OpenAI API key)
- `vllm_qwen`: Qwen2.5-7B-Instruct via vLLM (local)
- `claude-3-5-sonnet`: Claude 3.5 Sonnet (requires Anthropic API key)

### Vision Models (`--model_name_v`)
- `4o`: GPT-4o Vision (requires OpenAI API key)
- `vllm_qwen_vl`: Qwen2.5-VL-7B-Instruct via vLLM (local)
- `claude-3-5-sonnet`: Claude 3.5 Sonnet Vision (requires Anthropic API key)

## Configuration Options

### Poster Size
- `--poster_width_inches`: Width in inches (default: 48)
- `--poster_height_inches`: Height in inches (default: 36)

### Additional Options
- `--no_blank_detection`: Disable blank detection for severe overflow
- `--ablation_no_tree_layout`: Disable tree layout (ablation study)
- `--ablation_no_commenter`: Disable commenter (ablation study)
- `--ablation_no_example`: Disable examples (ablation study)

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose logs paper2poster

# Rebuild the image
docker-compose build --no-cache paper2poster
```

### GPU Issues with vLLM
Make sure you have NVIDIA Docker runtime installed:
```bash
# Test GPU access
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
```

### Permission Issues
```bash
# Fix permissions
sudo chown -R $USER:$USER input_papers output_posters model_cache
```

### API Key Issues
- Make sure your `.env` file is properly configured
- Check that API keys are valid and have sufficient credits
- Verify the container can access the `.env` file

### Model Download Issues
If the service fails to start due to model download problems:
```bash
# Remove the marker file and restart
rm model_cache/.models_downloaded
docker-compose restart paper2poster

# Or manually download models
docker-compose exec paper2poster python /app/download_models.py

# Check model cache size
du -sh model_cache/
```

## Development

### Interactive Shell
```bash
docker-compose exec paper2poster bash
```

### View Logs
```bash
docker-compose logs -f paper2poster
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop vLLM services only
docker-compose --profile vllm down
```

## Resource Requirements

### Minimum Requirements
- 8GB RAM
- 2 CPU cores
- 15GB storage (10GB for Docker image + 5GB for OCR/parsing models)

### Recommended for Production
- 16GB RAM
- 4 CPU cores
- 20GB storage
- NVIDIA GPU (optional, for faster processing)

### Additional for vLLM
- 16GB+ RAM
- NVIDIA GPU with 8GB+ VRAM
- 50GB+ storage for vLLM model cache

## Support

For issues and questions, please refer to the main README.md or create an issue in the repository. 