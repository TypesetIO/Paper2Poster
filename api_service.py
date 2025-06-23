import os
import json
import time
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
import tempfile
import shutil
import logging
import torch
import io

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import the pipeline components
from PosterAgent.parse_raw import parse_raw, gen_image_and_table
from PosterAgent.gen_outline_layout import filter_image_table, gen_outline_layout_v2
from utils.wei_utils import get_agent_config, utils_functions, run_code, style_bullet_content, scale_to_target_area, char_capacity
from PosterAgent.tree_split_layout import main_train, main_inference, get_arrangments_in_inches, split_textbox, to_inches
from PosterAgent.gen_pptx_code import generate_poster_code
from utils.src.utils import ppt_to_images
from PosterAgent.gen_poster_content import gen_bullet_point_content
from utils.ablation_utils import no_tree_get_layout

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set cache directories
os.environ['TRANSFORMERS_CACHE'] = str(Path('model_cache').absolute())
os.environ['HF_HOME'] = str(Path('model_cache').absolute())
os.environ['DOCLING_CACHE_DIR'] = str(Path('model_cache/docling').absolute())

# Pre-initialize models during startup
logger.info("Pre-initializing Docling models...")
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

# Initialize Docling converter
pipeline_options = PdfPipelineOptions()
pipeline_options.images_scale = 5.0  # IMAGE_RESOLUTION_SCALE from parse_raw.py
pipeline_options.generate_page_images = True
pipeline_options.generate_picture_images = True

doc_converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)
logger.info("Docling models initialized successfully")

# Pre-initialize marker models for fallback
# logger.info("Pre-initializing Marker models...")
# from marker.models import create_model_dict
# marker_model = create_model_dict(device='cuda' if torch.cuda.is_available() else 'cpu', dtype=torch.float16)
# logger.info("Marker models initialized successfully")

# Initialize FastAPI app
app = FastAPI(
    title="Paper2Poster API",
    description="Multimodal Poster Automation from Scientific Papers",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize models and resources on startup"""
    logger.info("=" * 50)
    logger.info("Starting Paper2Poster API Service")
    logger.info("=" * 50)
    
    # Check GPU availability
    if torch.cuda.is_available():
        logger.info(f"GPU Available: {torch.cuda.get_device_name(0)}")
        logger.info(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    else:
        logger.warning("No GPU available, using CPU (this may be slower)")
    
    # Docling and Marker models are already initialized at module level
    logger.info("All models pre-loaded successfully")
    logger.info("Service is ready to accept requests!")
    logger.info("=" * 50)

# Global constants
UNITS_PER_INCH = 25
THEME_TITLE_TEXT_COLOR = (255, 255, 255)
THEME_TITLE_FILL_COLOR = (47, 85, 151)

THEME = {
    'panel_visible': True,
    'textbox_visible': False,
    'figure_visible': False,
    'panel_theme': {
        'color': THEME_TITLE_FILL_COLOR,
        'thickness': 5,
        'line_style': 'solid',
    },
    'textbox_theme': None,
    'figure_theme': None,
}

class PosterRequest(BaseModel):
    model_name_t: str = Field(default="4o", description="Text model name")
    model_name_v: str = Field(default="4o", description="Vision model name")
    poster_width_inches: Optional[int] = Field(default=48, description="Poster width in inches")
    poster_height_inches: Optional[int] = Field(default=36, description="Poster height in inches")
    no_blank_detection: bool = Field(default=False, description="Disable blank detection")
    ablation_no_tree_layout: bool = Field(default=False, description="Disable tree layout")
    ablation_no_commenter: bool = Field(default=False, description="Disable commenter")
    ablation_no_example: bool = Field(default=False, description="Disable examples")

class PosterResponse(BaseModel):
    success: bool
    message: str
    poster_size: Optional[str] = None
    processing_time: Optional[str] = None
    token_usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None

class MockArgs:
    """Mock argparse.Namespace object for compatibility with existing pipeline"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

@app.get("/")
async def root():
    return {
        "message": "Welcome to Paper2Poster API",
        "version": "2.0.0",
        "endpoints": {
            "generate_poster": "/generate-poster",
            "generate_poster_stream": "/generate-poster-stream",
            "health": "/health",
            "docs": "/docs",
            "redoc": "/redoc"
        },
        "description": "Direct async poster generation API. Each request waits for completion."
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/generate-poster")
async def generate_poster(
    pdf_file: UploadFile = File(..., description="PDF file of the scientific paper"),
    model_name_t: str = Query(default="4o", description="Text model name"),
    model_name_v: str = Query(default="4o", description="Vision model name"),
    poster_width_inches: int = Query(default=48, description="Poster width in inches"),
    poster_height_inches: int = Query(default=36, description="Poster height in inches"),
    no_blank_detection: bool = Query(default=False, description="Disable blank detection"),
    ablation_no_tree_layout: bool = Query(default=False, description="Disable tree layout"),
    ablation_no_commenter: bool = Query(default=False, description="Disable commenter"),
    ablation_no_example: bool = Query(default=False, description="Disable examples"),
    return_type: str = Query(default="pptx", description="Return type: 'pptx', 'png', or 'json'")
):
    """
    Generate a poster from a PDF paper.
    Returns the poster file directly (PPTX or PNG) or JSON with metadata.
    This is an async endpoint that waits for completion before returning.
    """
    
    # Validate file type
    if not pdf_file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Validate return type
    if return_type not in ["pptx", "png", "json"]:
        raise HTTPException(status_code=400, detail="return_type must be 'pptx', 'png', or 'json'")
    
    temp_dir = None
    try:
        # Read file content
        file_content = await pdf_file.read()
        
        # Create request object
        request_data = PosterRequest(
            model_name_t=model_name_t,
            model_name_v=model_name_v,
            poster_width_inches=poster_width_inches,
            poster_height_inches=poster_height_inches,
            no_blank_detection=no_blank_detection,
            ablation_no_tree_layout=ablation_no_tree_layout,
            ablation_no_commenter=ablation_no_commenter,
            ablation_no_example=ablation_no_example
        )
        
        logger.info(f"Starting poster generation for file {pdf_file.filename}")
        
        # Run poster generation in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            process_poster_generation_sync,
            pdf_file.filename,
            file_content,
            request_data
        )
        
        # Store temp_dir for cleanup
        temp_dir = result.get("temp_dir")
        
        # Return based on requested type
        if return_type == "json":
            # Return metadata as JSON
            return JSONResponse(content={
                "success": True,
                "message": "Poster generated successfully",
                "poster_size": result["poster_size"],
                "processing_time": result["processing_time"],
                "token_usage": result["token_usage"],
                "filename": pdf_file.filename.replace('.pdf', '')
            })
        
        elif return_type == "pptx":
            # Return PPTX file
            if not os.path.exists(result["pptx_path"]):
                raise HTTPException(status_code=500, detail="PPTX file not found")
            
            return FileResponse(
                result["pptx_path"],
                media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                filename=f"{pdf_file.filename.replace('.pdf', '')}_poster.pptx"
            )
        
        else:  # return_type == "png"
            # Return PNG file
            output_dir = result["output_dir"]
            image_files = []
            for ext in ['.png', '.jpg', '.jpeg']:
                image_files.extend(Path(output_dir).glob(f"*{ext}"))
            
            if not image_files:
                raise HTTPException(status_code=500, detail="No image files found")
            
            # Return the first image file
            image_file = str(image_files[0])
            return FileResponse(
                image_file,
                media_type="image/png",
                filename=f"{pdf_file.filename.replace('.pdf', '')}_poster.png"
            )
    
    except Exception as e:
        logger.error(f"Poster generation failed: {str(e)}", exc_info=True)
        
        if return_type == "json":
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Poster generation failed",
                    "error": str(e)
                }
            )
        else:
            raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up temporary files after a delay (to allow file download)
        if temp_dir and os.path.exists(temp_dir):
            try:
                # Schedule cleanup after 60 seconds
                asyncio.create_task(cleanup_temp_dir(temp_dir, delay=60))
            except:
                pass

async def cleanup_temp_dir(temp_dir: str, delay: int = 60):
    """Clean up temporary directory after a delay"""
    await asyncio.sleep(delay)
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        logger.error(f"Failed to clean up {temp_dir}: {e}")

def process_poster_generation_sync(filename: str, file_content: bytes, request: PosterRequest) -> Dict[str, Any]:
    """Synchronous function to process poster generation"""
    
    temp_dir = None
    try:
        start_time = time.time()
        
        logger.info(f'Starting poster generation for {filename}...')
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix=f"poster_")
        paper_dir = os.path.join(temp_dir, "paper")
        os.makedirs(paper_dir, exist_ok=True)
        
        # Save uploaded PDF
        pdf_path = os.path.join(paper_dir, "paper.pdf")
        logger.info(f"Saving PDF to {pdf_path}")
        with open(pdf_path, "wb") as f:
            f.write(file_content)
        
        # Create mock args object
        args = MockArgs(
            poster_path=pdf_path,
            model_name_t=request.model_name_t,
            model_name_v=request.model_name_v,
            index=0,
            poster_name=filename.replace('.pdf', '').replace(' ', '_'),
            tmp_dir=os.path.join(temp_dir, "tmp"),
            poster_width_inches=request.poster_width_inches,
            poster_height_inches=request.poster_height_inches,
            no_blank_detection=request.no_blank_detection,
            ablation_no_tree_layout=request.ablation_no_tree_layout,
            ablation_no_commenter=request.ablation_no_commenter,
            ablation_no_example=request.ablation_no_example
        )
        
        os.makedirs(args.tmp_dir, exist_ok=True)
        
        # Create necessary directories for the pipeline
        os.makedirs('contents', exist_ok=True)
        os.makedirs('outlines', exist_ok=True)
        os.makedirs('tree_splits', exist_ok=True)
        os.makedirs(f'<{request.model_name_t}_{request.model_name_v}>_images_and_tables', exist_ok=True)
        os.makedirs(f'images_and_tables', exist_ok=True)  # For filtered images/tables
        
        # Run the poster generation pipeline
        result = run_poster_pipeline_sync(args)
        
        end_time = time.time()
        result["processing_time"] = f"{end_time - start_time:.2f} seconds"
        result["temp_dir"] = temp_dir
        
        logger.info(f'Poster generation completed in {result["processing_time"]}')
        
        return result
        
    except Exception as e:
        logger.error(f'Poster generation failed: {str(e)}', exc_info=True)
        raise

def run_poster_pipeline_sync(args) -> Dict[str, Any]:
    """Run the complete poster generation pipeline synchronously"""
    
    start_time = time.time()
    detail_log = {}
    
    # Calculate poster dimensions
    poster_width = args.poster_width_inches * UNITS_PER_INCH
    poster_height = args.poster_height_inches * UNITS_PER_INCH
    poster_width, poster_height = scale_to_target_area(poster_width, poster_height)
    poster_width_inches = to_inches(poster_width, UNITS_PER_INCH)
    poster_height_inches = to_inches(poster_height, UNITS_PER_INCH)
    
    if poster_width_inches > 56 or poster_height_inches > 56:
        if poster_width_inches >= poster_height_inches:
            scale_factor = 56 / poster_width_inches
        else:
            scale_factor = 56 / poster_height_inches
        
        poster_width_inches *= scale_factor
        poster_height_inches *= scale_factor
        poster_width = poster_width_inches * UNITS_PER_INCH
        poster_height = poster_height_inches * UNITS_PER_INCH
    
    # Get agent configurations
    agent_config_t = get_agent_config(args.model_name_t)
    agent_config_v = get_agent_config(args.model_name_v)
    
    total_input_tokens_t, total_output_tokens_t = 0, 0
    total_input_tokens_v, total_output_tokens_v = 0, 0
    
    # Step 1: Parse the raw poster
    logger.info(f"Parsing PDF paper...")
    input_token, output_token, raw_result = parse_raw(args, agent_config_t, version=2)
    total_input_tokens_t += input_token
    total_output_tokens_t += output_token
    
    _, _, images, tables = gen_image_and_table(args, raw_result)
    detail_log['parser_in_t'] = input_token
    detail_log['parser_out_t'] = output_token
    
    # Step 2: Filter unnecessary images and tables
    logger.info(f"Filtering images and tables...")
    input_token, output_token = filter_image_table(args, agent_config_t)
    total_input_tokens_t += input_token
    total_output_tokens_t += output_token
    detail_log['filter_in_t'] = input_token
    detail_log['filter_out_t'] = output_token
    
    # Step 3: Generate outline
    logger.info(f"Generating poster outline...")
    input_token, output_token, panels, figures = gen_outline_layout_v2(args, agent_config_t)
    total_input_tokens_t += input_token
    total_output_tokens_t += output_token
    detail_log['outline_in_t'] = input_token
    detail_log['outline_out_t'] = output_token
    
    # Step 4: Generate layout
    logger.info(f"Generating poster layout...")
    if args.ablation_no_tree_layout:
        panel_arrangement, figure_arrangement, text_arrangement, input_token, output_token = no_tree_get_layout(
            poster_width, poster_height, panels, figures, agent_config_t
        )
        total_input_tokens_t += input_token
        total_output_tokens_t += output_token
        detail_log['no_tree_layout_in_t'] = input_token
        detail_log['no_tree_layout_out_t'] = output_token
    else:
        panel_model_params, figure_model_params = main_train()
        panel_arrangement, figure_arrangement, text_arrangement = main_inference(
            panels, panel_model_params, figure_model_params, poster_width, poster_height, shrink_margin=3
        )
        
        text_arrangement_title = text_arrangement[0]
        text_arrangement = text_arrangement[1:]
        text_arrangement_title_top, text_arrangement_title_bottom = split_textbox(text_arrangement_title, 0.8)
        text_arrangement = [text_arrangement_title_top, text_arrangement_title_bottom] + text_arrangement
    
    # Process figure paths
    for i in range(len(figure_arrangement)):
        panel_id = figure_arrangement[i]['panel_id']
        panel_section_name = panels[panel_id]['section_name']
        figure_info = figures[panel_section_name]
        if 'image' in figure_info:
            figure_id = figure_info['image']
            figure_path = images.get(str(figure_id), images.get(figure_id, {})).get('image_path')
        elif 'table' in figure_info:
            figure_id = figure_info['table']
            figure_path = tables.get(str(figure_id), tables.get(figure_id, {})).get('table_path')
        
        if figure_path:
            figure_arrangement[i]['figure_path'] = figure_path
    
    # Calculate character capacity
    for text_arrangement_item in text_arrangement:
        num_chars = char_capacity(
            bbox=(text_arrangement_item['x'], text_arrangement_item['y'], 
                 text_arrangement_item['height'], text_arrangement_item['width'])
        )
        text_arrangement_item['num_chars'] = num_chars
    
    # Get arrangements in inches
    width_inch, height_inch, panel_arrangement_inches, figure_arrangement_inches, text_arrangement_inches = get_arrangments_in_inches(
        poster_width, poster_height, panel_arrangement, figure_arrangement, text_arrangement, UNITS_PER_INCH
    )
    
    # Save tree split results to file (required by gen_bullet_point_content)
    tree_split_results = {
        'poster_width': poster_width,
        'poster_height': poster_height,
        'poster_width_inches': width_inch,
        'poster_height_inches': height_inch,
        'panels': panels,
        'panel_arrangement': panel_arrangement,
        'figure_arrangement': figure_arrangement,
        'text_arrangement': text_arrangement,
        'panel_arrangement_inches': panel_arrangement_inches,
        'figure_arrangement_inches': figure_arrangement_inches,
        'text_arrangement_inches': text_arrangement_inches,
    }
    os.makedirs('tree_splits', exist_ok=True)
    with open(f'tree_splits/<{args.model_name_t}_{args.model_name_v}>_{args.poster_name}_tree_split_{args.index}.json', 'w') as f:
        json.dump(tree_split_results, f, indent=4)
    
    # Step 5: Generate content
    logger.info(f"Generating poster content...")
    input_token_t, output_token_t, input_token_v, output_token_v = gen_bullet_point_content(
        args, agent_config_t, agent_config_v, tmp_dir=args.tmp_dir
    )
    total_input_tokens_t += input_token_t
    total_output_tokens_t += output_token_t
    total_input_tokens_v += input_token_v
    total_output_tokens_v += output_token_v
    
    bullet_content = json.load(open(f'contents/<{args.model_name_t}_{args.model_name_v}>_{args.poster_name}_bullet_point_content_{args.index}.json', 'r'))
    
    # Step 6: Apply basic styles
    logger.info(f"Applying styles...")
    for k, v in bullet_content[0].items():
        style_bullet_content(v, THEME_TITLE_TEXT_COLOR, THEME_TITLE_FILL_COLOR)
    
    for i in range(1, len(bullet_content)):
        curr_content = bullet_content[i]
        style_bullet_content(curr_content['title'], THEME_TITLE_TEXT_COLOR, THEME_TITLE_FILL_COLOR)
    
    # Step 7: Generate the PowerPoint
    logger.info(f"Generating PowerPoint presentation...")
    poster_code = generate_poster_code(
        panel_arrangement_inches, text_arrangement_inches, figure_arrangement_inches,
        presentation_object_name='poster_presentation', slide_object_name='poster_slide',
        utils_functions=utils_functions, slide_width=width_inch, slide_height=height_inch,
        img_path=None, save_path=f'{args.tmp_dir}/poster.pptx', visible=False,
        content=bullet_content, theme=THEME, tmp_dir=args.tmp_dir,
    )
    
    output, err = run_code(poster_code)
    if err is not None:
        raise RuntimeError(f'Error in generating PowerPoint: {err}')
    
    # Step 8: Create output directory and move files
    logger.info(f"Finalizing poster files...")
    output_dir = f'<{args.model_name_t}_{args.model_name_v}>_generated_posters/{args.poster_name}'
    os.makedirs(output_dir, exist_ok=True)
    
    pptx_path = os.path.join(output_dir, f'{args.poster_name}.pptx')
    shutil.move(f'{args.tmp_dir}/poster.pptx', pptx_path)
    
    # Step 9: Convert to images
    logger.info(f"Converting PowerPoint to images...")
    ppt_to_images(pptx_path, output_dir)
    
    end_time = time.time()
    time_taken = end_time - start_time
    
    # Save logs
    log_data = {
        'input_tokens_t': total_input_tokens_t,
        'output_tokens_t': total_output_tokens_t,
        'input_tokens_v': total_input_tokens_v,
        'output_tokens_v': total_output_tokens_v,
        'time_taken': time_taken,
    }
    
    with open(os.path.join(output_dir, 'log.json'), 'w') as f:
        json.dump(log_data, f, indent=4)
    
    with open(os.path.join(output_dir, 'detail_log.json'), 'w') as f:
        json.dump(detail_log, f, indent=4)
    
    return {
        'pptx_path': pptx_path,
        'output_dir': output_dir,
        'poster_size': f'{poster_width_inches:.1f} x {poster_height_inches:.1f} inches',
        'processing_time': f'{time_taken:.2f} seconds',
        'token_usage': log_data
    }

@app.post("/generate-poster-stream")
async def generate_poster_stream(
    pdf_file: UploadFile = File(..., description="PDF file of the scientific paper"),
    model_name_t: str = Query(default="4o", description="Text model name"),
    model_name_v: str = Query(default="4o", description="Vision model name"),
    poster_width_inches: int = Query(default=48, description="Poster width in inches"),
    poster_height_inches: int = Query(default=36, description="Poster height in inches"),
    no_blank_detection: bool = Query(default=False, description="Disable blank detection"),
    ablation_no_tree_layout: bool = Query(default=False, description="Disable tree layout"),
    ablation_no_commenter: bool = Query(default=False, description="Disable commenter"),
    ablation_no_example: bool = Query(default=False, description="Disable examples")
):
    """
    Generate a poster with streaming progress updates.
    Returns Server-Sent Events (SSE) stream with progress updates.
    """
    # This is a placeholder for future streaming implementation
    # For now, redirect to the main endpoint
    return await generate_poster(
        pdf_file=pdf_file,
        model_name_t=model_name_t,
        model_name_v=model_name_v,
        poster_width_inches=poster_width_inches,
        poster_height_inches=poster_height_inches,
        no_blank_detection=no_blank_detection,
        ablation_no_tree_layout=ablation_no_tree_layout,
        ablation_no_commenter=ablation_no_commenter,
        ablation_no_example=ablation_no_example,
        return_type="json"
    )

if __name__ == "__main__":
    import uvicorn
    # Run with multiple workers to handle concurrent requests
    uvicorn.run("api_service:app", host="0.0.0.0", port=6025, workers=3, reload=False) 