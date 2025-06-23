# Paper2Poster API v2.0

## Overview

The Paper2Poster API has been updated to use a direct async approach instead of the previous job-based system. API calls now wait for completion and return results directly, making integration simpler and more straightforward.

## Key Changes

- **No more job management**: No need to track job IDs or poll for status
- **Direct responses**: Each API call waits for poster generation to complete
- **Multiple return formats**: Choose between PPTX file, PNG image, or JSON metadata
- **Simplified integration**: Fewer API calls needed, cleaner client code

## API Endpoints

### Generate Poster
`POST /generate-poster`

Generates a poster from a PDF paper and returns the result directly.

**Parameters:**
- `pdf_file` (file, required): The PDF file to convert
- `model_name_t` (string, default: "4o"): Text model name
- `model_name_v` (string, default: "4o"): Vision model name  
- `poster_width_inches` (int, default: 48): Poster width in inches
- `poster_height_inches` (int, default: 36): Poster height in inches
- `return_type` (string, default: "pptx"): Return format - "pptx", "png", or "json"
- Additional ablation flags (see API docs)

**Response:**
- If `return_type` is "pptx" or "png": Returns the file directly
- If `return_type` is "json": Returns generation metadata

### Health Check
`GET /health`

Check if the API service is healthy.

## Usage Examples

### Python Example (Simple)
```python
import requests

# Generate poster and get PPTX file
with open('paper.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:6025/generate-poster',
        files={'pdf_file': f},
        data={'return_type': 'pptx'},
        timeout=600  # 10 minute timeout
    )
    
if response.status_code == 200:
    with open('poster.pptx', 'wb') as out:
        out.write(response.content)
    print("Poster saved!")
```

### Python Example (With Metadata)
```python
import requests

# Generate poster and get metadata
with open('paper.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:6025/generate-poster',
        files={'pdf_file': f},
        data={'return_type': 'json'},
        timeout=600
    )
    
if response.status_code == 200:
    result = response.json()
    print(f"Poster size: {result['poster_size']}")
    print(f"Processing time: {result['processing_time']}")
    print(f"Tokens used: {result['token_usage']}")
```

### cURL Example
```bash
# Generate poster and save as PPTX
curl -X POST http://localhost:6025/generate-poster \
  -F "pdf_file=@paper.pdf" \
  -F "return_type=pptx" \
  -o poster.pptx

# Get JSON metadata
curl -X POST http://localhost:6025/generate-poster \
  -F "pdf_file=@paper.pdf" \
  -F "return_type=json"
```

## Running the API

Start the API service with multiple workers to handle concurrent requests:

```bash
python api_service.py
```

The API will run on `http://localhost:6025` with 3 worker processes by default.

## Testing

Three test scripts are provided:

1. **simple_api_test.py** - Basic command-line test
   ```bash
   python simple_api_test.py paper.pdf
   ```

2. **test_api.py** - Comprehensive test with all options
   ```bash
   python test_api.py --pdf paper.pdf --all-formats
   ```

3. **api_test.html** - Interactive web interface
   Open in browser and test via GUI

## Important Notes

- **Timeouts**: Poster generation can take 5-15 minutes depending on paper complexity. Set appropriate timeouts in your client code.
- **Concurrent Requests**: The API can handle 1-3 concurrent requests with 3 workers.
- **Memory Usage**: Each request may use significant memory. Monitor your system resources.
- **File Cleanup**: Temporary files are automatically cleaned up after 60 seconds.

## Migration from v1.0

If you were using the job-based API v1.0:

1. Remove all job status checking code
2. Remove job ID tracking
3. Increase request timeout to 10-20 minutes  
4. Handle the response directly instead of downloading separately
5. Update error handling for direct responses

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad request (invalid parameters)
- `500`: Server error (generation failed)

For JSON return type, errors include detailed information:
```json
{
  "success": false,
  "message": "Poster generation failed",
  "error": "Detailed error message"
}
``` 