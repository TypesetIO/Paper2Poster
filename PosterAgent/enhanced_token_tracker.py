"""Enhanced token tracking with cost calculation for OpenAI API calls."""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from PIL import Image
import base64
from io import BytesIO

# OpenAI pricing as of 2024 (per 1M tokens)
OPENAI_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-2024-11-20": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}

# Vision model constants
LOW_DETAIL_TOKENS = 85
HIGH_DETAIL_TOKENS_BASE = 85
HIGH_DETAIL_TOKENS_PER_TILE = 170
TILE_SIZE = 512

# Global tracking storage
_token_usage_log = []
_total_costs = {"total": 0.0, "by_component": {}}


def calculate_image_tokens(image: Image.Image, detail: str = "high") -> int:
    """Calculate tokens for a vision model image."""
    if detail == "low":
        return LOW_DETAIL_TOKENS
        
    width, height = image.size
    
    # Scale calculations for high detail
    if width > 2048 or height > 2048:
        scale = min(2048 / width, 2048 / height)
        width = int(width * scale)
        height = int(height * scale)
        
    scale = 768 / min(width, height)
    scaled_width = int(width * scale)
    scaled_height = int(height * scale)
    
    tiles_wide = (scaled_width + TILE_SIZE - 1) // TILE_SIZE
    tiles_high = (scaled_height + TILE_SIZE - 1) // TILE_SIZE
    total_tiles = tiles_wide * tiles_high
    
    return HIGH_DETAIL_TOKENS_BASE + (total_tiles * HIGH_DETAIL_TOKENS_PER_TILE)


def extract_images_from_messages(messages: List[Any]) -> int:
    """Extract and count vision tokens from messages."""
    vision_tokens = 0
    
    for msg in messages:
        if hasattr(msg, 'content') and hasattr(msg, 'image_list'):
            # Handle BaseMessage with image_list
            if msg.image_list:
                for image in msg.image_list:
                    if isinstance(image, Image.Image):
                        vision_tokens += calculate_image_tokens(image)
                        
    return vision_tokens


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost based on model and token counts."""
    base_model = None
    for model_key in OPENAI_PRICING:
        if model.startswith(model_key):
            base_model = model_key
            break
            
    if not base_model:
        base_model = "gpt-4o"  # Default
        
    pricing = OPENAI_PRICING[base_model]
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    
    return input_cost + output_cost


def account_token_enhanced(response, component: str = "Unknown", messages: Optional[List] = None) -> Tuple[int, int]:
    """Enhanced token accounting with cost tracking and vision support."""
    from .logger_config import get_logger
    logger = get_logger('token_tracker')
    
    # Extract basic token info
    input_tokens = response.info['usage']['prompt_tokens']
    output_tokens = response.info['usage']['completion_tokens']
    model = response.info.get('model', 'gpt-4o')
    
    # Calculate vision tokens if messages provided
    vision_tokens = 0
    if messages:
        vision_tokens = extract_images_from_messages(messages)
        
    # Calculate costs
    cost = calculate_cost(model, input_tokens, output_tokens)
    
    # Create log entry
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "component": component,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "vision_tokens": vision_tokens,
        "cost_usd": cost
    }
    
    # Update global tracking
    _token_usage_log.append(log_entry)
    _total_costs["total"] += cost
    if component not in _total_costs["by_component"]:
        _total_costs["by_component"][component] = 0.0
    _total_costs["by_component"][component] += cost
    
    # Log details
    if vision_tokens > 0:
        logger.info(
            f"{component} - Model: {model}, "
            f"Tokens: {input_tokens} (incl. {vision_tokens} vision) -> {output_tokens}, "
            f"Cost: ${cost:.4f}"
        )
    else:
        logger.info(
            f"{component} - Model: {model}, "
            f"Tokens: {input_tokens} -> {output_tokens}, "
            f"Cost: ${cost:.4f}"
        )
    
    return input_tokens, output_tokens


def get_token_usage_summary() -> Dict[str, Any]:
    """Get summary of all token usage and costs."""
    total_input = sum(entry["input_tokens"] for entry in _token_usage_log)
    total_output = sum(entry["output_tokens"] for entry in _token_usage_log)
    total_vision = sum(entry["vision_tokens"] for entry in _token_usage_log)
    
    return {
        "total_calls": len(_token_usage_log),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_vision_tokens": total_vision,
        "total_cost_usd": _total_costs["total"],
        "cost_by_component": _total_costs["by_component"],
        "detailed_log": _token_usage_log
    }


def save_token_usage_report(filepath: str):
    """Save detailed token usage report to file."""
    report = get_token_usage_summary()
    
    with open(filepath, 'w') as f:
        json.dump(report, f, indent=2)
        
    from .logger_config import get_logger
    logger = get_logger('token_tracker')
    logger.info(f"Token usage report saved to {filepath}")
    
    # Also log summary to console
    logger.info(f"Total API calls: {report['total_calls']}")
    logger.info(f"Total tokens: {report['total_input_tokens']} -> {report['total_output_tokens']}")
    logger.info(f"Total vision tokens: {report['total_vision_tokens']}")
    logger.info(f"Total cost: ${report['total_cost_usd']:.2f}")
    logger.info("Cost breakdown by component:")
    for component, cost in report['cost_by_component'].items():
        logger.info(f"  {component}: ${cost:.2f}") 