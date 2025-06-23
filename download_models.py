#!/usr/bin/env python3
"""
Download and cache all required models for Paper2Poster

This script can be run independently to ensure all models are downloaded
before starting the API service. This is useful for Docker builds or
deployment scenarios where you want to pre-cache models.
"""

import os
import sys
import logging
import torch
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def download_docling_models():
    """Download and initialize Docling models"""
    logger.info("Downloading Docling models...")
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
        
        # Configure pipeline options
        pipeline_options = PdfPipelineOptions()
        pipeline_options.images_scale = 5.0
        pipeline_options.generate_page_images = True
        pipeline_options.generate_picture_images = True
        
        # Initialize converter - this will download models if needed
        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        
        logger.info("✅ Docling models downloaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to download Docling models: {e}")
        return False

def download_marker_models():
    """Download and initialize Marker models"""
    logger.info("Downloading Marker models...")
    try:
        from marker.models import create_model_dict
        
        # Determine device
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        if device == 'cuda':
            logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
        else:
            logger.info("Using CPU (GPU not available)")
        
        # Create model dict - this will download models if needed
        marker_model = create_model_dict(device=device, dtype=torch.float16)
        
        logger.info("✅ Marker models downloaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to download Marker models: {e}")
        return False

def main():
    """Main function to download all models"""
    logger.info("=" * 60)
    logger.info("Paper2Poster Model Downloader")
    logger.info("=" * 60)
    
    # Check Python version
    if sys.version_info < (3, 8):
        logger.error("Python 3.8 or higher is required!")
        sys.exit(1)
    
    # Create necessary directories
    directories = ['model_cache', 'contents', 'tmp']
    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
        logger.info(f"Ensured directory exists: {dir_name}")
    
    # Set cache directories
    os.environ['TRANSFORMERS_CACHE'] = str(Path('model_cache').absolute())
    os.environ['HF_HOME'] = str(Path('model_cache').absolute())
    os.environ['DOCLING_CACHE_DIR'] = str(Path('model_cache/docling').absolute())
    
    logger.info("\nStarting model downloads...")
    logger.info("This may take 10-30 minutes on first run depending on your internet speed.\n")
    
    success = True
    
    # Download Docling models
    if not download_docling_models():
        success = False
    
    # Download Marker models
    # if not download_marker_models():
    #     success = False
    
    # Summary
    logger.info("=" * 60)
    if success:
        logger.info("✅ All models downloaded successfully!")
        logger.info("You can now start the API service without model download delays.")
    else:
        logger.info("❌ Some models failed to download. Check the errors above.")
        sys.exit(1)
    logger.info("=" * 60)

if __name__ == "__main__":
    main() 