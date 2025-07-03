# Docling Processing Example

## Sample Paper Processing Workflow

Let's walk through how Docling processes a typical computer science paper.

### Input: "Deep Learning for Poster Generation.pdf" (8 pages)

### Step 1: Docling Initialization
```python
# In parse_raw.py
pipeline_options = PdfPipelineOptions()
pipeline_options.images_scale = 5.0  # 360 DPI output
pipeline_options.generate_page_images = True
pipeline_options.generate_picture_images = True

doc_converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)

# Convert the PDF
raw_result = doc_converter.convert("Deep_Learning_for_Poster_Generation.pdf")
```

### Step 2: Text Extraction Output

**Markdown Output** (`raw_result.document.export_to_markdown()`):
```markdown
# Deep Learning for Poster Generation

## Abstract
We present a novel approach to automatically generate academic posters from research papers using deep learning techniques...

## 1. Introduction
Academic poster creation is a time-consuming task that requires...

## 2. Related Work
Previous approaches to document summarization include...

### 2.1 Neural Abstractive Summarization
Recent advances in transformer models...

## 3. Methodology
Our approach consists of three main components...

[... continues with full paper text ...]
```

### Step 3: Visual Elements Extraction

**Extracted Figures** (stored in `<model>_images_and_tables/paper_name/`):

1. **Figure 1**: Architecture Diagram
   - File: `Deep_Learning_for_Poster_Generation-picture-1.png`
   - Caption: "Figure 1: Overall architecture of our poster generation system"
   - Dimensions: 3000×2000 pixels (at 360 DPI)
   - Metadata:
   ```json
   {
     "1": {
       "caption": "Figure 1: Overall architecture of our poster generation system",
       "image_path": "images_and_tables/Deep_Learning_for_Poster_Generation/Deep_Learning_for_Poster_Generation-picture-1.png",
       "width": 3000,
       "height": 2000,
       "figure_size": 6000000,
       "figure_aspect": 1.5
     }
   }
   ```

2. **Table 1**: Performance Comparison
   - File: `Deep_Learning_for_Poster_Generation-table-1.png`
   - Caption: "Table 1: Comparison of poster generation methods"
   - Dimensions: 2500×1500 pixels

### Step 4: LLM Processing of Extracted Content

**Input to LLM** (via prompt template):
```
Given the following research paper content in markdown format:

[Extracted markdown text]

Please extract and organize the content into the following sections suitable for a poster:
1. Title and Authors
2. Key Contributions (3-4 bullet points)
3. Methodology Overview
4. Main Results
5. Conclusions and Future Work
```

**LLM Output** (structured JSON):
```json
{
  "meta": {
    "title": "Deep Learning for Poster Generation",
    "authors": "Smith, J., Doe, A., Johnson, B.",
    "affiliation": "University of AI Research"
  },
  "sections": [
    {
      "title": "Key Contributions",
      "content": "• First end-to-end deep learning system for academic poster generation\n• Novel layout algorithm that preserves visual hierarchy\n• Achieves 85% user satisfaction in studies"
    },
    {
      "title": "Methodology",
      "content": "Our system uses a three-stage pipeline:\n1. Document parsing with Docling\n2. Content selection via transformer models\n3. Layout generation using constraint optimization"
    }
  ]
}
```

### Step 5: Figure/Table Selection

**Filter Agent Input**:
```json
{
  "paper_content": "[summarized sections]",
  "available_figures": {
    "1": {"caption": "Figure 1: Overall architecture..."},
    "2": {"caption": "Figure 2: Training loss curves..."},
    "3": {"caption": "Figure 3: User study results..."}
  },
  "available_tables": {
    "1": {"caption": "Table 1: Comparison of methods..."},
    "2": {"caption": "Table 2: Ablation study results..."}
  }
}
```

**Filter Agent Output**:
```json
{
  "selected_figures": ["1", "3"],  // Architecture and results
  "selected_tables": ["1"]         // Main comparison
}
```

### Step 6: Final File Structure

```
project_root/
├── contents/
│   └── <gpt-4o_gpt-4o>_Deep_Learning_for_Poster_Generation_raw_content.json
├── <gpt-4o_gpt-4o>_images_and_tables/
│   └── Deep_Learning_for_Poster_Generation/
│       ├── Deep_Learning_for_Poster_Generation-1.png  # Page 1
│       ├── Deep_Learning_for_Poster_Generation-2.png  # Page 2
│       ├── Deep_Learning_for_Poster_Generation-picture-1.png
│       ├── Deep_Learning_for_Poster_Generation-picture-2.png
│       ├── Deep_Learning_for_Poster_Generation-picture-3.png
│       ├── Deep_Learning_for_Poster_Generation-table-1.png
│       ├── Deep_Learning_for_Poster_Generation-table-2.png
│       ├── Deep_Learning_for_Poster_Generation-with-images.md
│       └── Deep_Learning_for_Poster_Generation-with-image-refs.html
├── Deep_Learning_for_Poster_Generation_images.json
└── Deep_Learning_for_Poster_Generation_tables.json
```

### Step 7: Benefits Realized

1. **Accurate Extraction**: Docling correctly identified all 3 figures and 2 tables
2. **Caption Preservation**: All captions maintained for context
3. **High Quality**: 360 DPI images suitable for large-format printing
4. **Structure Preservation**: Section hierarchy maintained in markdown
5. **Robust Processing**: Successfully handled two-column layout

### Common Edge Cases Handled

1. **Multi-column Layout**: Docling correctly merges columns in reading order
2. **Embedded Formulas**: Extracted as images with proper positioning
3. **Complex Tables**: Spanning cells correctly identified
4. **Figure Subfigures**: Treated as single unit with combined caption
5. **References Section**: Properly identified and can be excluded from poster

This example demonstrates how Docling's comprehensive document understanding enables Paper2Poster to create accurate, visually appealing posters while preserving the essential elements of the original academic paper. 