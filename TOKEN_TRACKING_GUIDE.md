# Enhanced Token Tracking Guide

## Overview

The enhanced token tracking system provides comprehensive tracking of OpenAI API usage, including:
- Input and output token counts
- Vision model image token calculation
- Cost calculation based on current OpenAI pricing
- Detailed logging by component
- Session summaries and reports

## Key Features

### 1. Automatic Token and Cost Tracking

Every OpenAI API call is automatically tracked with:
- **Component identification**: Know which part of the system made the call
- **Token counts**: Input tokens, output tokens, and vision tokens
- **Cost calculation**: Automatic cost calculation based on the model used
- **Timestamp logging**: When each call was made

### 2. Vision Model Support

The system automatically detects and calculates tokens for images:
- Supports both "low" and "high" detail image processing
- Calculates tiles and tokens based on OpenAI's vision pricing model
- Separates vision tokens from text tokens for clarity

### 3. Multi-Model Pricing

Supports pricing for all major OpenAI models:
- GPT-4o series (including latest versions)
- GPT-4o-mini
- GPT-4 and GPT-4-turbo
- GPT-3.5-turbo variants

## Implementation

### Basic Usage

The system has been integrated into the PosterAgent codebase. Key files have been updated to use `account_token_enhanced()` instead of the basic `account_token()`:

```python
from PosterAgent.enhanced_token_tracker import account_token_enhanced

# For regular text calls
input_tokens, output_tokens = account_token_enhanced(
    response, 
    component='ComponentName'
)

# For vision model calls with images
input_tokens, output_tokens = account_token_enhanced(
    response,
    component='VisionComponent',
    messages=[msg_with_images]  # Messages containing image_list
)
```

### Components Tracked

The following components are now tracked:
- **ParseRaw**: Document parsing
- **FilterImageTable**: Image and table filtering
- **GenOutline-Planner**: Outline generation
- **GenContent-{section}**: Content generation for each section
- **GenPosterTitle**: Title generation
- **GenBulletContent**: Bullet point generation
- **GenContent-Critic**: Vision model critique of content
- **Deoverflow-Critic-{section}**: Overflow detection with vision
- **Fill and Style**: Content filling and styling operations

### Output Reports

At the end of each pipeline run, a detailed JSON report is saved to:
```
log/{model_name}_{poster_name}_{index}_token_report.json
```

This report includes:
- Total token usage across all components
- Cost breakdown by component
- Detailed log of each API call
- Vision token usage statistics

## Example Output

### Console Logging
```
[INFO] ParseRaw - Model: gpt-4o, Tokens: 1500 -> 800, Cost: $0.0118
[INFO] GenContent-Critic - Model: gpt-4o, Tokens: 2000 (incl. 850 vision) -> 500, Cost: $0.0100
[INFO] Deoverflow-Critic-Introduction - Model: gpt-4o, Tokens: 1800 (incl. 680 vision) -> 300, Cost: $0.0075
```

### JSON Report Structure
```json
{
  "session_summary": {
    "total_calls": 45,
    "total_input_tokens": 125000,
    "total_output_tokens": 35000,
    "total_vision_tokens": 15000,
    "total_cost_usd": 1.2345,
    "cost_breakdown": {
      "ParseRaw": 0.0118,
      "GenContent-Introduction": 0.0856,
      "GenContent-Critic": 0.2340,
      "Deoverflow-Critic-Introduction": 0.1250
    }
  },
  "detailed_calls": [
    {
      "timestamp": "2024-01-15T10:30:45",
      "component": "ParseRaw",
      "model": "gpt-4o",
      "input_tokens": 1500,
      "text_input_tokens": 1500,
      "vision_tokens": 0,
      "output_tokens": 800,
      "cost_usd": 0.0118,
      "has_images": false
    }
  ]
}
```

## Cost Optimization Tips

1. **Use GPT-4o-mini** for non-critical components when possible (6x cheaper than GPT-4o)
2. **Monitor vision token usage** - high-resolution images can be expensive
3. **Review the cost breakdown** to identify expensive components
4. **Consider using "low" detail** for images when high detail isn't necessary

## Running the Demo

To see the enhanced token tracking in action:

```bash
python demo_token_tracking.py
```

This will demonstrate:
- Regular text model tracking
- Vision model tracking with image tokens
- Cost calculation for different models
- Report generation

## Future Enhancements

Potential improvements:
- Real-time cost alerts when exceeding thresholds
- Historical cost tracking and trends
- Batch API support for reduced costs
- Integration with OpenAI usage dashboard
- Support for streaming responses 