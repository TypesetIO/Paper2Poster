# Docling Components and Paper2Poster Usage

## Component Usage Table

| Docling Component | What it Extracts | How Paper2Poster Uses It | Storage Format |
|-------------------|------------------|--------------------------|----------------|
| **Document Text** | Full text content with structure | LLM processes to create poster content | Markdown file + JSON |
| **Page Images** | Full page renders at 360 DPI | Visual reference, debugging | PNG files |
| **Tables** | Table images + captions + structure | Selected for poster inclusion based on relevance | PNG + JSON metadata |
| **Figures** | Figure images + captions | Selected for poster visualization | PNG + JSON metadata |
| **Layout Info** | Bounding boxes, element positions | Not directly used (future potential) | Internal only |
| **Sections** | Hierarchical document structure | Maintains logical flow in poster | Part of markdown |
| **Captions** | Text associated with visuals | Displayed with figures/tables | JSON metadata |
| **Formulas** | Mathematical expressions as images | Preserved but not specially processed | Part of text/images |

## Detailed Component Breakdown

### 1. Text Extraction Pipeline
```
PDF → Docling → Markdown → LLM → Poster Sections
```
- **Input**: Academic paper PDF
- **Docling Process**: Layout analysis + text extraction
- **Output**: Clean markdown preserving structure
- **Usage**: Fed to LLM for content summarization

### 2. Visual Elements Pipeline
```
PDF → Docling → Images/Tables → Filter → Layout → Poster
```
- **Input**: Figures, charts, tables in PDF
- **Docling Process**: 
  - Detects visual elements via RT-DETR
  - Extracts at 5× resolution (360 DPI)
  - Preserves captions
- **Filter Process**: LLM selects relevant visuals
- **Output**: High-quality images in poster

### 3. Metadata Extraction
Each visual element includes:
```json
{
  "caption": "Figure caption text",
  "image_path": "path/to/image.png",
  "width": 2000,
  "height": 1500,
  "figure_size": 3000000,
  "figure_aspect": 1.33
}
```

### 4. Scale Ratios for Poster Display

| Element Type | Min Scale Ratio | Max Scale Ratio | Purpose |
|--------------|-----------------|-----------------|---------|
| Images | 1/50 | 1/40 | Ensures readable size on poster |
| Tables | 1/100 | 1/80 | Allows larger tables to fit |

### 5. Fallback Mechanisms

| Scenario | Primary Method | Fallback | Reason |
|----------|----------------|----------|--------|
| Text < 500 chars | Docling | Marker | Handles edge cases |
| Missing captions | Extract from nearest text | Empty string | Robustness |
| Corrupt images | Skip image | Log warning | Prevent crashes |

## Processing Statistics

Typical paper processing:
- **Pages**: 8-12 pages
- **Tables**: 2-5 extracted, 1-3 selected
- **Figures**: 4-8 extracted, 2-4 selected  
- **Processing Time**: 10-30 seconds for Docling
- **Image Quality**: 360 DPI (5× base resolution)

## Key Benefits of Docling Integration

1. **Preservation of Academic Structure**: Maintains logical flow from paper to poster
2. **High-Quality Visual Extraction**: 360 DPI ensures crisp images on large posters
3. **Intelligent Selection**: Captions enable context-aware figure/table selection
4. **Robustness**: Multiple output formats provide debugging capabilities
5. **Scalability**: Handles various paper formats and layouts 