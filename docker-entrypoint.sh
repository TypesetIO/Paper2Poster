#!/bin/bash
set -e

echo "============================================="
echo "Paper2Poster Docker Container Starting..."
echo "============================================="

# Check if we should skip model download
if [ "${SKIP_MODEL_DOWNLOAD}" = "true" ]; then
    echo "Skipping model download (SKIP_MODEL_DOWNLOAD=true)"
else
    # Check if models are already downloaded
    MODEL_MARKER_FILE="/app/model_cache/.models_downloaded"
    
    if [ -f "$MODEL_MARKER_FILE" ]; then
        echo "Models already downloaded (found marker file)"
    else
        echo "Downloading models for the first time..."
        echo "This may take 10-30 minutes depending on your internet speed..."
        
        # Run the model download script
        python /app/download_models.py
        
        # Create marker file to indicate models have been downloaded
        if [ $? -eq 0 ]; then
            touch "$MODEL_MARKER_FILE"
            echo "Model download completed successfully!"
        else
            echo "Model download failed! The service may not work properly."
            # Continue anyway - models might download on first request
        fi
    fi
fi

echo "============================================="
echo "Starting Paper2Poster API Service..."
echo "============================================="

# Execute the command passed to the container
# Default is to start the API service with the startup script
exec "$@" 