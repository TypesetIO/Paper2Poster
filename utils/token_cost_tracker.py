"""
Token and cost tracking utilities for OpenAI API calls, including vision models.

This module provides comprehensive tracking for:
- Input/output token counts
- Vision model image tokens
- Cost calculation based on model and token types
- Detailed logging of each API call
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from PIL import Image
import base64
from io import BytesIO

# OpenAI pricing as of 2024 (per 1M tokens)
OPENAI_PRICING = {
    # GPT-4o models
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-2024-11-20": {"input": 2.50, "output": 10.00},
    "gpt-4o-2024-08-06": {"input": 2.50, "output": 10.00},
    "gpt-4o-2024-05-13": {"input": 5.00, "output": 15.00},
    
    # GPT-4o-mini models
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60},
    
    # GPT-4 models
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-4-32k": {"input": 60.00, "output": 120.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4-turbo-2024-04-09": {"input": 10.00, "output": 30.00},
    "gpt-4-turbo-preview": {"input": 10.00, "output": 30.00},
    "gpt-4-1106-preview": {"input": 10.00, "output": 30.00},
    "gpt-4-0125-preview": {"input": 10.00, "output": 30.00},
    
    # GPT-3.5 models
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "gpt-3.5-turbo-0125": {"input": 0.50, "output": 1.50},
    "gpt-3.5-turbo-1106": {"input": 1.00, "output": 2.00},
    "gpt-3.5-turbo-16k": {"input": 3.00, "output": 4.00},
}

# Vision model image token calculation constants
LOW_DETAIL_TOKENS = 85
HIGH_DETAIL_TOKENS_BASE = 85
HIGH_DETAIL_TOKENS_PER_TILE = 170
TILE_SIZE = 512
MAX_SHORT_SIDE = 768
MAX_DIMENSION = 2048


class TokenCostTracker:
    """Tracks token usage and costs for OpenAI API calls."""
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize the token cost tracker.
        
        Args:
            log_file: Optional path to a JSON file for detailed logging
        """
        self.log_file = log_file
        self.session_totals = {
            "input_tokens": 0,
            "output_tokens": 0,
            "vision_tokens": 0,
            "total_cost": 0.0,
            "calls": []
        }
        self.logger = logging.getLogger(__name__)
        
    def calculate_image_tokens(self, image: Image.Image, detail: str = "high") -> int:
        """
        Calculate tokens for a single image based on OpenAI's vision pricing.
        
        Args:
            image: PIL Image object
            detail: "low" or "high" detail level
            
        Returns:
            Number of tokens for the image
        """
        if detail == "low":
            return LOW_DETAIL_TOKENS
            
        # High detail calculation
        width, height = image.size
        
        # Scale down if exceeds max dimension
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            scale = min(MAX_DIMENSION / width, MAX_DIMENSION / height)
            width = int(width * scale)
            height = int(height * scale)
            
        # Scale so shortest side is 768px
        scale = MAX_SHORT_SIDE / min(width, height)
        scaled_width = int(width * scale)
        scaled_height = int(height * scale)
        
        # Calculate number of 512x512 tiles
        tiles_wide = (scaled_width + TILE_SIZE - 1) // TILE_SIZE
        tiles_high = (scaled_height + TILE_SIZE - 1) // TILE_SIZE
        total_tiles = tiles_wide * tiles_high
        
        return HIGH_DETAIL_TOKENS_BASE + (total_tiles * HIGH_DETAIL_TOKENS_PER_TILE)
    
    def extract_images_from_messages(self, messages: List[Dict]) -> List[Tuple[Image.Image, str]]:
        """
        Extract images and their detail levels from OpenAI messages.
        
        Args:
            messages: List of OpenAI message dictionaries
            
        Returns:
            List of (image, detail) tuples
        """
        images = []
        
        for msg in messages:
            content = msg.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if item.get("type") == "image_url":
                        image_url = item.get("image_url", {})
                        url = image_url.get("url", "")
                        detail = image_url.get("detail", "high")
                        
                        # Handle base64 encoded images
                        if url.startswith("data:image"):
                            # Extract base64 data
                            base64_str = url.split(",")[1] if "," in url else ""
                            if base64_str:
                                try:
                                    image_data = base64.b64decode(base64_str)
                                    image = Image.open(BytesIO(image_data))
                                    images.append((image, detail))
                                except Exception as e:
                                    self.logger.error(f"Failed to decode image: {e}")
                                    
        return images
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost based on model and token counts.
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Total cost in USD
        """
        # Find the base model name for pricing
        base_model = None
        for model_key in OPENAI_PRICING:
            if model.startswith(model_key):
                base_model = model_key
                break
                
        if not base_model:
            self.logger.warning(f"Unknown model for pricing: {model}, using gpt-4o rates")
            base_model = "gpt-4o"
            
        pricing = OPENAI_PRICING[base_model]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost
    
    def track_api_call(
        self,
        component: str,
        response: Any,
        messages: Optional[List[Dict]] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track a single API call with detailed information.
        
        Args:
            component: Name of the component making the call
            response: Response object from the API call
            messages: Optional list of messages sent to the API
            model: Optional model name override
            
        Returns:
            Dictionary with tracking details
        """
        # Extract token counts from response
        input_tokens = 0
        output_tokens = 0
        vision_tokens = 0
        
        if hasattr(response, 'info') and 'usage' in response.info:
            usage = response.info['usage']
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            
        # Extract model from response if not provided
        if not model and hasattr(response, 'info'):
            model = response.info.get('model', 'unknown')
            
        # Calculate vision tokens if messages contain images
        if messages:
            images = self.extract_images_from_messages(messages)
            for image, detail in images:
                vision_tokens += self.calculate_image_tokens(image, detail)
                
        # Adjust input tokens to account for vision tokens
        text_input_tokens = max(0, input_tokens - vision_tokens)
        
        # Calculate cost
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        
        # Create tracking record
        record = {
            "timestamp": datetime.now().isoformat(),
            "component": component,
            "model": model,
            "input_tokens": input_tokens,
            "text_input_tokens": text_input_tokens,
            "vision_tokens": vision_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
            "has_images": vision_tokens > 0
        }
        
        # Update session totals
        self.session_totals["input_tokens"] += input_tokens
        self.session_totals["output_tokens"] += output_tokens
        self.session_totals["vision_tokens"] += vision_tokens
        self.session_totals["total_cost"] += cost
        self.session_totals["calls"].append(record)
        
        # Log the call
        self._log_call(record)
        
        return record
    
    def _log_call(self, record: Dict[str, Any]) -> None:
        """Log a single API call."""
        # Console logging
        if record["has_images"]:
            self.logger.info(
                f"{record['component']} API call: "
                f"text_in={record['text_input_tokens']}, "
                f"vision={record['vision_tokens']}, "
                f"out={record['output_tokens']}, "
                f"cost=${record['cost_usd']:.4f}"
            )
        else:
            self.logger.info(
                f"{record['component']} API call: "
                f"in={record['input_tokens']}, "
                f"out={record['output_tokens']}, "
                f"cost=${record['cost_usd']:.4f}"
            )
            
        # File logging
        if self.log_file:
            try:
                with open(self.log_file, 'a') as f:
                    f.write(json.dumps(record) + '\n')
            except Exception as e:
                self.logger.error(f"Failed to write to log file: {e}")
                
    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session."""
        return {
            "total_input_tokens": self.session_totals["input_tokens"],
            "total_output_tokens": self.session_totals["output_tokens"],
            "total_vision_tokens": self.session_totals["vision_tokens"],
            "total_cost_usd": self.session_totals["total_cost"],
            "total_calls": len(self.session_totals["calls"]),
            "cost_breakdown": self._get_cost_breakdown()
        }
        
    def _get_cost_breakdown(self) -> Dict[str, float]:
        """Get cost breakdown by component."""
        breakdown = {}
        for call in self.session_totals["calls"]:
            component = call["component"]
            if component not in breakdown:
                breakdown[component] = 0.0
            breakdown[component] += call["cost_usd"]
        return breakdown
        
    def save_session_report(self, filepath: str) -> None:
        """Save a detailed session report to a JSON file."""
        report = {
            "session_summary": self.get_session_summary(),
            "detailed_calls": self.session_totals["calls"]
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
            
        self.logger.info(f"Session report saved to {filepath}")


# Global tracker instance
_global_tracker = None


def get_global_tracker() -> TokenCostTracker:
    """Get or create the global token cost tracker."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = TokenCostTracker()
    return _global_tracker


def set_global_tracker(tracker: TokenCostTracker) -> None:
    """Set the global token cost tracker."""
    global _global_tracker
    _global_tracker = tracker


def track_tokens_and_cost(
    component: str,
    response: Any,
    messages: Optional[List[Dict]] = None,
    model: Optional[str] = None
) -> Tuple[int, int]:
    """
    Track tokens and cost for an API call and return token counts.
    
    This is a convenience function that uses the global tracker.
    
    Returns:
        Tuple of (input_tokens, output_tokens)
    """
    tracker = get_global_tracker()
    record = tracker.track_api_call(component, response, messages, model)
    return record["input_tokens"], record["output_tokens"] 