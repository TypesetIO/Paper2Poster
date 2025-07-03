#!/usr/bin/env python3
"""
Demo script showing how the enhanced token tracking system works.

This demonstrates:
1. Tracking regular text model calls
2. Tracking vision model calls with images
3. Generating comprehensive cost reports
"""

import os
import sys
from dotenv import load_dotenv

# Add the parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PosterAgent.enhanced_token_tracker import (
    TokenCostTracker, 
    set_global_tracker, 
    save_token_usage_report
)

def main():
    """Demo the enhanced token tracking system."""
    load_dotenv()
    
    # Create a tracker with logging to file
    tracker = TokenCostTracker(log_file="demo_token_log.jsonl")
    set_global_tracker(tracker)
    
    print("Enhanced Token Tracking Demo")
    print("=" * 50)
    
    # Simulate some API calls
    # In real usage, this would be done automatically by the enhanced account_token function
    
    # Example 1: Regular text model call
    mock_response = type('obj', (object,), {
        'info': {
            'usage': {
                'prompt_tokens': 150,
                'completion_tokens': 50
            },
            'model': 'gpt-4o'
        }
    })
    
    record = tracker.track_api_call(
        component="ParseRaw",
        response=mock_response
    )
    
    print(f"\n1. Regular text call:")
    print(f"   Component: {record['component']}")
    print(f"   Tokens: {record['input_tokens']} -> {record['output_tokens']}")
    print(f"   Cost: ${record['cost_usd']:.4f}")
    
    # Example 2: Vision model call
    from PIL import Image
    
    # Create a dummy image for demo
    dummy_image = Image.new('RGB', (1024, 768), color='red')
    
    mock_vision_response = type('obj', (object,), {
        'info': {
            'usage': {
                'prompt_tokens': 500,  # This includes vision tokens
                'completion_tokens': 100
            },
            'model': 'gpt-4o'
        }
    })
    
    # Mock messages with images
    mock_messages = [
        type('obj', (object,), {
            'content': 'Analyze this image',
            'image_list': [dummy_image]
        })
    ]
    
    record2 = tracker.track_api_call(
        component="Deoverflow-Critic",
        response=mock_vision_response,
        messages=mock_messages
    )
    
    print(f"\n2. Vision model call:")
    print(f"   Component: {record2['component']}")
    print(f"   Total input tokens: {record2['input_tokens']}")
    print(f"   Vision tokens: {record2['vision_tokens']}")
    print(f"   Text input tokens: {record2['text_input_tokens']}")
    print(f"   Output tokens: {record2['output_tokens']}")
    print(f"   Cost: ${record2['cost_usd']:.4f}")
    
    # Example 3: Different model
    mock_mini_response = type('obj', (object,), {
        'info': {
            'usage': {
                'prompt_tokens': 1000,
                'completion_tokens': 500
            },
            'model': 'gpt-4o-mini'
        }
    })
    
    record3 = tracker.track_api_call(
        component="GenContent",
        response=mock_mini_response
    )
    
    print(f"\n3. GPT-4o-mini call:")
    print(f"   Component: {record3['component']}")
    print(f"   Model: {record3['model']}")
    print(f"   Tokens: {record3['input_tokens']} -> {record3['output_tokens']}")
    print(f"   Cost: ${record3['cost_usd']:.4f} (note the lower price)")
    
    # Get session summary
    print("\n" + "=" * 50)
    print("Session Summary:")
    summary = tracker.get_session_summary()
    
    print(f"\nTotal API calls: {summary['total_calls']}")
    print(f"Total input tokens: {summary['total_input_tokens']:,}")
    print(f"Total output tokens: {summary['total_output_tokens']:,}")
    print(f"Total vision tokens: {summary['total_vision_tokens']:,}")
    print(f"Total cost: ${summary['total_cost_usd']:.2f}")
    
    print("\nCost breakdown by component:")
    for component, cost in summary['cost_breakdown'].items():
        print(f"  {component}: ${cost:.4f}")
    
    # Save detailed report
    tracker.save_session_report("demo_token_report.json")
    print("\nDetailed report saved to: demo_token_report.json")
    
    print("\n" + "=" * 50)
    print("In actual usage:")
    print("1. The enhanced token tracking is automatic when using account_token_enhanced()")
    print("2. Vision tokens are calculated automatically from images in messages")
    print("3. Costs are calculated based on the model used")
    print("4. All calls are logged with timestamps and details")
    print("5. A comprehensive report can be generated at any time")

if __name__ == "__main__":
    main() 