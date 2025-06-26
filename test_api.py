#!/usr/bin/env python3
"""
Paper2Poster API Test Script

This script demonstrates how to:
1. Upload a PDF paper to the Paper2Poster API
2. Get S3 path where poster will be uploaded
3. Poll for completion (3-5 minutes)

Note: S3 configuration is required. Only PPTX format is supported.

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
        output_dir: str = "."
    ) -> Optional[str]:
        """
        Upload PDF and generate poster (PPTX format only)
        
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
            output_dir: Directory to save output files
            
        Returns:
            Path to saved PPTX file if successful, None if failed
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
                'ablation_no_example': ablation_no_example
            }
            
            print(f"📤 Uploading {pdf_path} and generating poster...")
            print(f"   Models: Text={model_name_t}, Vision={model_name_v}")
            print(f"   Size: {poster_width_inches}x{poster_height_inches} inches")
            
            start_time = time.time()
            
            response = self.session.post(
                f"{self.base_url}/generate-poster",
                files=files,
                data=data,
                timeout=60  # Reduced timeout for initial request
            )
            
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                # Ensure output directory exists
                os.makedirs(output_dir, exist_ok=True)
                
                # Check if response is JSON (could be S3 mode or legacy JSON mode)
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    result = response.json()
                    
                    # Check if request was successful
                    if not result.get('success', False):
                        print(f"❌ Failed to start generation: {result.get('error', 'Unknown error')}")
                        return None
                    
                    # Check if this is S3 response
                    if 's3_path' in result:
                        print(f"✅ Job started successfully!")
                        print(f"   S3 Path: {result['s3_path']}")
                        print(f"   Estimated time: 3-5 minutes")
                        
                        # Convert S3 path to HTTPS URL
                        s3_path = result['s3_path']
                        if s3_path.startswith('s3://'):
                            parts = s3_path[5:].split('/', 1)
                            bucket = parts[0]
                            key = parts[1] if len(parts) > 1 else ''
                            s3_url = f"https://{bucket}.s3.amazonaws.com/{key}"
                        else:
                            print("❌ Invalid S3 path format")
                            return None
                        
                        # Poll S3 for file existence
                        poll_interval = 10  # seconds
                        max_wait_time = 600  # 10 minutes
                        
                        print(f"\n⏳ Polling S3 for completion (checking every {poll_interval} seconds)...")
                        
                        while time.time() - start_time < max_wait_time:
                            time.sleep(poll_interval)
                            elapsed = int(time.time() - start_time)
                            
                            try:
                                # Check if file exists on S3
                                head_resp = self.session.head(s3_url, timeout=10)
                                if head_resp.status_code == 200:
                                    print(f"\n✅ Poster ready in {elapsed} seconds!")
                                    
                                    # Download from S3
                                    print(f"📥 Downloading from: {s3_url}")
                                    download_resp = self.session.get(s3_url, timeout=60)
                                    
                                    if download_resp.status_code == 200:
                                        filename = f"{Path(pdf_path).stem}_poster.pptx"
                                        output_path = os.path.join(output_dir, filename)
                                        
                                        with open(output_path, 'wb') as f:
                                            f.write(download_resp.content)
                                        
                                        file_size = os.path.getsize(output_path)
                                        print(f"✅ Downloaded: {output_path} ({file_size:,} bytes)")
                                        return output_path
                                    else:
                                        print(f"❌ Failed to download from S3: {download_resp.status_code}")
                                        return None
                                else:
                                    print(f"   [{elapsed}s] Still processing...", end='\r')
                            except:
                                print(f"   [{elapsed}s] Still processing...", end='\r')
                        
                        print(f"\n❌ Timeout: Poster generation took longer than {max_wait_time} seconds")
                        return None
                    
                    else:
                        print("❌ Unexpected response: S3 path not found")
                        return None
                
                else:
                    print("❌ Unexpected response: Not JSON format")
                    return None
            
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