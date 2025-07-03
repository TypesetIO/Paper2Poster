# Docling Usage in Paper2Poster

## Overview

Docling is a powerful document parsing library that serves as the foundation for extracting structured information from PDF papers in the Paper2Poster system. It provides sophisticated document understanding capabilities, extracting not just text but also tables, figures, layout information, and document structure.

## Docling Components and Their Usage

### 1. DocumentConverter - The Main Entry Point

The `DocumentConverter` is initialized in `parse_raw.py` with specific pipeline options:

```python
pipeline_options = PdfPipelineOptions()
pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE  # 5.0
pipeline_options.generate_page_images = True
pipeline_options.generate_picture_images = True

doc_converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)
```

**Key Configuration:**
- `images_scale = 5.0`: Upscales images to 360 DPI (72 DPI × 5) for better quality
- `generate_page_images = True`: Creates full page images for visual reference
- `generate_picture_images = True`: Extracts individual figures/charts from the document

### 2. Document Structure Extraction

When `doc_converter.convert(raw_source)` is called, Docling performs multiple analyses:

#### A. Layout Analysis
- Uses RT-DETR model to detect layout components
- Identifies: Title, Section Headers, Text, Tables, Figures, Captions, Formulas, List Items, Page Headers/Footers
- Creates bounding boxes for each detected element

#### B. Text Extraction
- Extracts text while preserving reading order
- Maintains hierarchical structure (sections, subsections)
- Handles multi-column layouts intelligently

#### C. Table Detection and Structure Recognition
- Detects tables using layout model
- Uses TableFormer model for structure analysis
- Extracts table cells, rows, columns, and their relationships
- Preserves table captions

#### D. Figure/Image Extraction
- Identifies figures, charts, and diagrams
- Extracts images with their captions
- Maintains figure-caption associations

### 3. Docling Output Components Used in Paper2Poster

#### A. Markdown Export
```python
raw_markdown = raw_result.document.export_to_markdown()
```
- Clean, structured text representation
- Preserves document hierarchy
- Used as input for LLM to understand paper content
- Comments are stripped: `markdown_clean_pattern.sub("", raw_markdown)`

#### B. Page Images
```python
for page_no, page in conv_res.document.pages.items():
    page_image_filename = output_dir / f"{doc_filename}-{page_no}.png"
    page.image.pil_image.save(fp, format="PNG")
```
- Full page renderings at high resolution
- Used for visual reference and debugging
- Stored for potential manual review

#### C. Table Extraction
```python
for element, _level in conv_res.document.iterate_items():
    if isinstance(element, TableItem):
        table_counter += 1
        element.get_image(conv_res.document).save(fp, "PNG")
```

Each table is processed to extract:
- **Caption**: `table.caption_text(conv_res.document)`
- **Visual representation**: High-resolution PNG image
- **Dimensions**: Width, height for layout planning
- **Aspect ratio**: For optimal poster placement
- **Table structure**: Cells, rows, columns (though not directly used in current implementation)

#### D. Figure Extraction
```python
if isinstance(element, PictureItem):
    picture_counter += 1
    element.get_image(conv_res.document).save(fp, "PNG")
```

Each figure/image is processed to extract:
- **Caption**: Associated descriptive text
- **High-res image**: Extracted at 5× scale
- **Metadata**: Dimensions, aspect ratio, file size
- **Position**: Original location in document

### 4. Data Flow Through the Pipeline

1. **Initial Parsing** (`parse_raw.py`):
   - Docling converts PDF → structured document
   - Markdown exported for text content
   - Falls back to Marker if Docling fails (text < 500 chars)

2. **Content Generation**:
   - LLM uses markdown text to create poster sections
   - Maintains paper structure and key information

3. **Figure/Table Filtering** (`filter_image_table`):
   - Analyzes extracted figures and tables
   - Calculates min/max display sizes based on scale ratios
   - LLM selects relevant visuals for poster

4. **Layout Planning**:
   - Uses figure/table dimensions for space allocation
   - Considers aspect ratios for optimal placement
   - Integrates captions with visual elements

5. **Final Poster Assembly**:
   - Places selected figures/tables in designated areas
   - Maintains visual quality through high-resolution extraction
   - Preserves caption-visual associations

### 5. Advanced Docling Features Utilized

#### Multi-format Output
```python
# Embedded images in markdown
conv_res.document.save_as_markdown(md_filename, image_mode=ImageRefMode.EMBEDDED)

# External image references
conv_res.document.save_as_markdown(md_filename, image_mode=ImageRefMode.REFERENCED)

# HTML output
conv_res.document.save_as_html(html_filename, image_mode=ImageRefMode.REFERENCED)
```

These outputs are saved for:
- Debugging and verification
- Alternative processing pipelines
- Manual review and editing

#### Hierarchical Document Understanding
- Docling preserves section hierarchy
- Enables context-aware content extraction
- Maintains logical flow for poster narrative

#### Quality Assurance
- High-resolution image extraction (5× scale)
- Caption preservation ensures context
- Fallback to Marker for robust parsing

### 6. Benefits of Docling Integration

1. **Accuracy**: State-of-the-art models for layout and table understanding
2. **Completeness**: Extracts all document components (text, tables, figures)
3. **Structure Preservation**: Maintains document hierarchy and relationships
4. **Visual Quality**: High-resolution extraction for poster-quality images
5. **Robustness**: Handles complex layouts and multi-column formats

### 7. Limitations and Workarounds

1. **Complex Formulas**: Currently extracted as images, not LaTeX
2. **Handwritten Content**: May not be accurately extracted
3. **Scanned PDFs**: Relies on OCR quality (can be configured)
4. **Very Large Tables**: May need manual adjustment for poster format

The Docling integration provides Paper2Poster with sophisticated document understanding capabilities, enabling it to transform complex academic papers into well-structured, visually appealing posters while preserving all critical information and visual elements. 