#!/usr/bin/env python3
"""
Paper2Poster API Startup Script

This script starts the Paper2Poster API service with proper configuration
and ensures models are pre-loaded before accepting requests.
"""

import os
import sys
import time
import logging
import argparse
import torch
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if the environment is properly set up"""
    logger.info("Checking environment...")
    
    # Check Python version
    python_version = sys.version_info
    logger.info(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        logger.error("Python 3.8 or higher is required!")
        return False
    
    # Check GPU availability
    if torch.cuda.is_available():
        logger.info(f"✅ GPU Available: {torch.cuda.get_device_name(0)}")
        logger.info(f"   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    else:
        logger.warning("⚠️  No GPU available, using CPU (this may be slower)")
    
    # Check if required directories exist
    required_dirs = ['contents', 'tmp']
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
            logger.info(f"Created directory: {dir_name}")
    
    return True

def pre_download_models():
    """Pre-download and initialize models"""
    logger.info("=" * 60)
    logger.info("Pre-downloading and initializing models...")
    logger.info("This may take a few minutes on first run...")
    logger.info("=" * 60)
    
    # Set cache directories
    os.environ['TRANSFORMERS_CACHE'] = str(Path('model_cache').absolute())
    os.environ['HF_HOME'] = str(Path('model_cache').absolute())
    os.environ['DOCLING_CACHE_DIR'] = str(Path('model_cache/docling').absolute())
    
    try:
        # Import and initialize Docling
        logger.info("Loading Docling models...")
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
        
        pipeline_options = PdfPipelineOptions()
        pipeline_options.images_scale = 5.0
        pipeline_options.generate_page_images = True
        pipeline_options.generate_picture_images = True
        
        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        logger.info("✅ Docling models loaded successfully")
        
        # Import and initialize Marker models
        # logger.info("Loading Marker models...")
        # from marker.models import create_model_dict
        # device = 'cuda' if torch.cuda.is_available() else 'cpu'
        # marker_model = create_model_dict(device=device, dtype=torch.float16)
        # logger.info("✅ Marker models loaded successfully")
        
        logger.info("=" * 60)
        logger.info("All models loaded successfully!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Start Paper2Poster API Service')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=6025, help='Port to bind to')
    parser.add_argument('--workers', type=int, default=3, help='Number of worker processes')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload for development')
    parser.add_argument('--skip-model-download', action='store_true', help='Skip pre-downloading models')
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting Paper2Poster API Service")
    
    # Check environment
    if not check_environment():
        logger.error("Environment check failed!")
        sys.exit(1)
    
    # Pre-download models unless skipped
    if not args.skip_model_download:
        if not pre_download_models():
            logger.error("Model download failed!")
            sys.exit(1)
    else:
        logger.warning("Skipping model pre-download. Models will be downloaded on first use.")
    
    # Start the service
    logger.info(f"Starting API service on {args.host}:{args.port} with {args.workers} workers...")
    
    import uvicorn
    
    # When using multiple workers, we need to use the string import format
    uvicorn.run(
        "api_service:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        reload=args.reload,
        log_level="info"
    )

if __name__ == "__main__":
    main() 