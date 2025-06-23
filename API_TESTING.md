# Paper2Poster API Testing

This document explains how to test the Paper2Poster API using the provided Python scripts.

## Test Scripts

### 1. `simple_api_test.py` - Basic Usage

A minimal script for quick testing:

```bash
# Basic usage
python simple_api_test.py paper.pdf

# Example output:
🎓 Generating poster for: paper.pdf
✅ API is healthy
📤 Uploading PDF and starting generation...
✅ Job started: abc123-def456-789
👀 Monitoring job progress...
📊 Status: processing - Parsing PDF paper...
📊 Status: processing - Generating poster layout...
📊 Status: processing - Generating PowerPoint presentation...
🎉 Generation completed!
💾 Downloading PowerPoint file...
✅ Downloaded: poster_abc123-def456-789.pptx (2,458,123 bytes)

🎉 Success! Poster saved as: poster_abc123-def456-789.pptx
```

### 2. `test_api.py` - Advanced Testing

A comprehensive script with full control over parameters:

#### Basic Usage
```bash
python test_api.py --pdf paper.pdf
```

#### Advanced Usage with Custom Parameters
```bash
python test_api.py \
    --pdf paper.pdf \
    --model-t 4o \
    --model-v 4o \
    --width 48 \
    --height 36 \
    --output-dir ./my_posters \
    --poll-interval 5
```

#### Using Local Models (vLLM)
```bash
# First start vLLM services
docker-compose --profile vllm up -d

# Then generate with local models
python test_api.py \
    --pdf paper.pdf \
    --model-t vllm_qwen \
    --model-v vllm_qwen_vl
```

#### Utility Commands
```bash
# List all jobs
python test_api.py --list-jobs

# Monitor existing job
python test_api.py --job-id abc123-def456-789

# Download files for existing job
python test_api.py --download-only abc123-def456-789
```

## Prerequisites

1. **Start the API service:**
   ```bash
   docker-compose up -d
   ```

2. **Install Python dependencies:**
   ```bash
   pip install requests
   ```

3. **Verify API is running:**
   ```bash
   curl http://localhost:6025/health
   ```

## Usage Examples

### Example 1: Quick Test
```bash
# Download a sample paper (example)
wget https://arxiv.org/pdf/2301.07041.pdf -O sample_paper.pdf

# Generate poster
python simple_api_test.py sample_paper.pdf
```

### Example 2: Custom Configuration
```bash
python test_api.py \
    --pdf research_paper.pdf \
    --model-t 4o \
    --model-v 4o \
    --width 36 \
    --height 24 \
    --output-dir ./conference_posters
```

### Example 3: Using Different Models
```bash
# GPT-4o models
python test_api.py --pdf paper.pdf --model-t 4o --model-v 4o

# Mix of models
python test_api.py --pdf paper.pdf --model-t 4o-mini --model-v 4o

# Local vLLM models (requires vLLM services running)
python test_api.py --pdf paper.pdf --model-t vllm_qwen --model-v vllm_qwen_vl
```

### Example 4: Ablation Studies
```bash
# Disable tree layout
python test_api.py --pdf paper.pdf --ablation-no-tree-layout

# Disable commenter
python test_api.py --pdf paper.pdf --ablation-no-commenter

# Disable examples
python test_api.py --pdf paper.pdf --ablation-no-example
```

## Script Parameters

### `test_api.py` Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--pdf` | Path to PDF paper file | Required |
| `--api-url` | API base URL | `http://localhost:6025` |
| `--model-t` | Text model name | `4o` |
| `--model-v` | Vision model name | `4o` |
| `--width` | Poster width in inches | `48` |
| `--height` | Poster height in inches | `36` |
| `--output-dir` | Output directory | `./downloads` |
| `--poll-interval` | Status check interval (seconds) | `10` |
| `--no-blank-detection` | Disable blank detection | `False` |
| `--ablation-*` | Various ablation study options | `False` |

### Available Models

#### Text Models (`--model-t`)
- `4o` - GPT-4o
- `4o-mini` - GPT-4o Mini  
- `vllm_qwen` - Qwen2.5-7B-Instruct (local)
- `claude-3-5-sonnet` - Claude 3.5 Sonnet

#### Vision Models (`--model-v`)
- `4o` - GPT-4o Vision
- `vllm_qwen_vl` - Qwen2.5-VL-7B-Instruct (local)
- `claude-3-5-sonnet` - Claude 3.5 Sonnet

## Expected Output Files

After successful generation, you'll get:
- **PowerPoint file** (`.pptx`) - Editable poster presentation
- **PNG image** (`.png`) - Static poster image

## Troubleshooting

### Common Issues

1. **API Connection Error**
   ```
   ❌ Cannot connect to API: Connection refused
   ```
   **Solution:** Make sure the API service is running:
   ```bash
   docker-compose up -d
   curl http://localhost:6025/health
   ```

2. **PDF Upload Error**
   ```
   ❌ PDF file not found: paper.pdf
   ```
   **Solution:** Check the file path and ensure the PDF exists:
   ```bash
   ls -la paper.pdf
   file paper.pdf  # Should show "PDF document"
   ```

3. **Job Timeout or Failure**
   ```
   ❌ Job failed: OpenAI API key not found
   ```
   **Solution:** Check your environment variables:
   ```bash
   # Make sure .env file exists with your API keys
   cat .env | grep API_KEY
   ```

4. **Model Not Available**
   ```
   ❌ Model 'vllm_qwen' not available
   ```
   **Solution:** Start the vLLM services:
   ```bash
   docker-compose --profile vllm up -d
   ```

### Debug Mode

For more detailed output, you can modify the scripts to add debug information:

```python
import requests
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
requests.packages.urllib3.disable_warnings()
```

### Manual API Testing

You can also test the API manually using curl:

```bash
# Health check
curl http://localhost:6025/health

# Generate poster
curl -X POST "http://localhost:6025/generate-poster" \
  -F "pdf_file=@paper.pdf" \
  -F "model_name_t=4o" \
  -F "model_name_v=4o"

# Check job status (replace JOB_ID)
curl http://localhost:6025/jobs/JOB_ID

# Download result (replace JOB_ID)
curl -O -J "http://localhost:6025/download/JOB_ID?file_type=pptx"
```

## Performance Notes

- **Generation time:** Typically 2-10 minutes depending on paper complexity
- **File sizes:** PowerPoint files are usually 1-5 MB
- **Concurrent jobs:** The API supports multiple simultaneous jobs
- **Rate limits:** Depends on your AI model provider's limits

## Support

If you encounter issues:
1. Check the API logs: `docker-compose logs paper2poster`
2. Verify your environment configuration
3. Ensure all required services are running
4. Review the API documentation at http://localhost:6025/docs 