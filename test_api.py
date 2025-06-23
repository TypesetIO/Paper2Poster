#!/usr/bin/env python3
"""
Paper2Poster API Test Script

This script demonstrates how to:
1. Upload a PDF paper to the Paper2Poster API
2. Get the generated PowerPoint poster file directly

Usage:
    python test_api.py --pdf path/to/paper.pdf
    python test_api.py --pdf paper.pdf --model_t 4o --model_v 4o --width 48 --height 36
"""

import argparse
import requests
import time
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import json

class Paper2PosterClient:
    """Client for interacting with the Paper2Poster API"""
    
    def __init__(self, base_url: str = "http://localhost:6025"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
    def health_check(self) -> bool:
        """Check if the API service is healthy"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ API is healthy: {health_data}")
                return True
            else:
                print(f"❌ API health check failed: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot connect to API: {e}")
            return False
    
    def generate_poster(
        self,
        pdf_path: str,
        model_name_t: str = "4o",
        model_name_v: str = "4o",
        poster_width_inches: int = 48,
        poster_height_inches: int = 36,
        no_blank_detection: bool = False,
        ablation_no_tree_layout: bool = False,
        ablation_no_commenter: bool = False,
        ablation_no_example: bool = False,
        return_type: str = "pptx",
        output_dir: str = "."
    ) -> Optional[str]:
        """
        Upload PDF and generate poster
        
        Args:
            pdf_path: Path to PDF file
            model_name_t: Text model name
            model_name_v: Vision model name
            poster_width_inches: Poster width in inches
            poster_height_inches: Poster height in inches
            no_blank_detection: Disable blank detection
            ablation_no_tree_layout: Disable tree layout
            ablation_no_commenter: Disable commenter
            ablation_no_example: Disable examples
            return_type: Return type ('pptx', 'png', or 'json')
            output_dir: Directory to save output files
            
        Returns:
            Path to saved file if successful, None if failed
        """
        if not os.path.exists(pdf_path):
            print(f"❌ PDF file not found: {pdf_path}")
            return None
        
        pdf_file = None
        try:
            # Prepare the file and data
            pdf_file = open(pdf_path, 'rb')
            files = {'pdf_file': pdf_file}
            data = {
                'model_name_t': model_name_t,
                'model_name_v': model_name_v,
                'poster_width_inches': poster_width_inches,
                'poster_height_inches': poster_height_inches,
                'no_blank_detection': no_blank_detection,
                'ablation_no_tree_layout': ablation_no_tree_layout,
                'ablation_no_commenter': ablation_no_commenter,
                'ablation_no_example': ablation_no_example,
                'return_type': return_type
            }
            
            print(f"📤 Uploading {pdf_path} and generating poster...")
            print(f"   Models: Text={model_name_t}, Vision={model_name_v}")
            print(f"   Size: {poster_width_inches}x{poster_height_inches} inches")
            print(f"   Return type: {return_type}")
            print(f"   This may take several minutes...")
            
            start_time = time.time()
            
            response = self.session.post(
                f"{self.base_url}/generate-poster",
                files=files,
                data=data,
                timeout=1200  # 20 minute timeout
            )
            
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                # Ensure output directory exists
                os.makedirs(output_dir, exist_ok=True)
                
                if return_type == "json":
                    # Handle JSON response
                    result = response.json()
                    print(f"✅ Poster generated successfully!")
                    print(f"   Processing time: {result.get('processing_time', 'N/A')}")
                    print(f"   Poster size: {result.get('poster_size', 'N/A')}")
                    if 'token_usage' in result:
                        tokens = result['token_usage']
                        print(f"   Token usage:")
                        print(f"     Text: {tokens.get('input_tokens_t', 0)} → {tokens.get('output_tokens_t', 0)}")
                        print(f"     Vision: {tokens.get('input_tokens_v', 0)} → {tokens.get('output_tokens_v', 0)}")
                    
                    # Save JSON response
                    json_path = os.path.join(output_dir, f"{Path(pdf_path).stem}_result.json")
                    with open(json_path, 'w') as f:
                        json.dump(result, f, indent=2)
                    print(f"   Result saved to: {json_path}")
                    return json_path
                
                else:
                    # Handle file response (PPTX or PNG)
                    filename = f"{Path(pdf_path).stem}_poster.{return_type}"
                    output_path = os.path.join(output_dir, filename)
                    
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    
                    file_size = os.path.getsize(output_path)
                    print(f"✅ Poster generated successfully in {elapsed_time:.1f} seconds!")
                    print(f"   File saved: {output_path} ({file_size:,} bytes)")
                    return output_path
            
            else:
                print(f"❌ Failed to generate poster: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Error: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"❌ Request timed out after {elapsed_time:.1f} seconds")
            print("   Poster generation can take 10-15 minutes for complex papers.")
            print("   Try increasing the timeout or check the server logs.")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None
        finally:
            if pdf_file:
                pdf_file.close()
    
    def generate_poster_all_formats(
        self,
        pdf_path: str,
        output_dir: str = "./downloads",
        **kwargs
    ) -> Dict[str, Optional[str]]:
        """
        Generate poster in all available formats
        
        Returns:
            Dictionary with paths to generated files
        """
        results = {}
        
        # Generate PPTX
        print("\n📊 Generating PowerPoint presentation...")
        results['pptx'] = self.generate_poster(
            pdf_path,
            return_type="pptx",
            output_dir=output_dir,
            **kwargs
        )
        
        # Generate PNG
        print("\n🖼️  Generating PNG image...")
        results['png'] = self.generate_poster(
            pdf_path,
            return_type="png",
            output_dir=output_dir,
            **kwargs
        )
        
        # Get JSON metadata
        print("\n📄 Getting generation metadata...")
        results['json'] = self.generate_poster(
            pdf_path,
            return_type="json",
            output_dir=output_dir,
            **kwargs
        )
        
        return results


def main():
    parser = argparse.ArgumentParser(description='Test the Paper2Poster API')
    parser.add_argument('--pdf', required=True, help='Path to PDF paper file')
    parser.add_argument('--api-url', default='http://localhost:6025', help='API base URL')
    parser.add_argument('--model-t', default='4o', help='Text model name')
    parser.add_argument('--model-v', default='4o', help='Vision model name')
    parser.add_argument('--width', type=int, default=48, help='Poster width in inches')
    parser.add_argument('--height', type=int, default=36, help='Poster height in inches')
    parser.add_argument('--output-dir', default='./downloads', help='Output directory for downloaded files')
    parser.add_argument('--no-blank-detection', action='store_true', help='Disable blank detection')
    parser.add_argument('--ablation-no-tree-layout', action='store_true', help='Disable tree layout')
    parser.add_argument('--ablation-no-commenter', action='store_true', help='Disable commenter')
    parser.add_argument('--ablation-no-example', action='store_true', help='Disable examples')
    parser.add_argument('--return-type', default='pptx', choices=['pptx', 'png', 'json'], help='Return type')
    parser.add_argument('--all-formats', action='store_true', help='Generate all formats (PPTX, PNG, JSON)')
    
    args = parser.parse_args()
    
    # Initialize client
    client = Paper2PosterClient(args.api_url)
    
    print("🎓 Paper2Poster API Test Script")
    print("=" * 50)
    
    # Health check
    print("🏥 Checking API health...")
    if not client.health_check():
        print("Please make sure the Paper2Poster API is running!")
        sys.exit(1)
    
    # Generate poster
    if args.all_formats:
        # Generate all formats
        print(f"\n📋 Generating poster in all formats for: {args.pdf}")
        results = client.generate_poster_all_formats(
            pdf_path=args.pdf,
            output_dir=args.output_dir,
            model_name_t=args.model_t,
            model_name_v=args.model_v,
            poster_width_inches=args.width,
            poster_height_inches=args.height,
            no_blank_detection=args.no_blank_detection,
            ablation_no_tree_layout=args.ablation_no_tree_layout,
            ablation_no_commenter=args.ablation_no_commenter,
            ablation_no_example=args.ablation_no_example
        )
        
        print("\n📊 Summary:")
        success_count = sum(1 for v in results.values() if v is not None)
        print(f"✅ Successfully generated {success_count}/3 formats")
        
        if results['pptx']:
            print(f"   PowerPoint: {results['pptx']}")
        if results['png']:
            print(f"   PNG Image: {results['png']}")
        if results['json']:
            print(f"   Metadata: {results['json']}")
    
    else:
        # Generate single format
        result = client.generate_poster(
            pdf_path=args.pdf,
            model_name_t=args.model_t,
            model_name_v=args.model_v,
            poster_width_inches=args.width,
            poster_height_inches=args.height,
            no_blank_detection=args.no_blank_detection,
            ablation_no_tree_layout=args.ablation_no_tree_layout,
            ablation_no_commenter=args.ablation_no_commenter,
            ablation_no_example=args.ablation_no_example,
            return_type=args.return_type,
            output_dir=args.output_dir
        )
        
        if result:
            print(f"\n🎉 Success! Output saved to: {result}")
            print(f"📁 Full path: {os.path.abspath(result)}")
        else:
            print("\n❌ Poster generation failed!")
            sys.exit(1)


if __name__ == "__main__":
    main() 