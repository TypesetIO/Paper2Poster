#!/usr/bin/env python3
"""
Simple Paper2Poster API Test Example

A minimal example showing how to use the Paper2Poster API:
1. Upload a PDF
2. Get S3 path where poster will be uploaded
3. Poll for completion (3-5 minutes)

Note: S3 configuration is required. Only PPTX format is supported.

Usage:
    python simple_api_test.py path/to/paper.pdf
"""

import sys
import requests
import os
import time
import json

def generate_poster(pdf_path: str, api_url: str = "http://localhost:6025"):
    """
    Simple function to generate a poster and download the result
    
    Args:
        pdf_path: Path to the PDF paper
        api_url: API base URL
    
    Returns:
        Path to downloaded PPTX file if successful, None if failed
    """
    
    print(f"🎓 Generating poster for: {pdf_path}")
    
    # 1. Check if API is healthy and get configuration
    try:
        health_resp = requests.get(f"{api_url}/health", timeout=5)
        if health_resp.status_code != 200:
            print("❌ API is not healthy")
            return None
        print("✅ API is healthy")
        
        # Check API configuration
        root_resp = requests.get(f"{api_url}/", timeout=5)
        api_info = root_resp.json()
        s3_configured = api_info.get('s3_configured', False)
        
        if not s3_configured:
            print("❌ S3 storage is not configured. Please configure S3 environment variables.")
            return None
        
        print(f"📦 S3 storage configured: {api_info.get('s3_bucket')}")
            
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return None
    
    # 2. Upload PDF and generate poster
    try:
        with open(pdf_path, 'rb') as f:
            files = {'pdf_file': f}
            data = {
                'model_name_t': '4o',
                'model_name_v': '4o',
                'poster_width_inches': 48,
                'poster_height_inches': 36,
            }
            
            print("📤 Uploading PDF and starting poster generation...")
            
            response = requests.post(
                f"{api_url}/generate-poster", 
                files=files, 
                data=data,
                timeout=60  # 1 minute timeout for initial request
            )
            
            if response.status_code != 200:
                print(f"❌ Generation failed: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Error: {response.text}")
                return None
            
            result = response.json()
            
            # Check if request was successful
            if not result.get('success', False):
                print(f"❌ Failed to start generation: {result.get('error', 'Unknown error')}")
                return None
            
            # Handle S3 response
            if 's3_path' in result:
                print(f"✅ Job started successfully!")
                print(f"   S3 Path: {result['s3_path']}")
                print(f"   Estimated time: 3-5 minutes")
                
                # Extract S3 URL from path
                # Format: s3://bucket/key
                s3_path = result['s3_path']
                if s3_path.startswith('s3://'):
                    # Convert to HTTPS URL
                    parts = s3_path[5:].split('/', 1)
                    bucket = parts[0]
                    key = parts[1] if len(parts) > 1 else ''
                    s3_url = f"https://{bucket}.s3.amazonaws.com/{key}"
                else:
                    print("❌ Invalid S3 path format")
                    return None
                
                # Poll S3 for file existence
                start_time = time.time()
                poll_interval = 10  # seconds
                max_wait_time = 600  # 10 minutes
                
                print(f"\n⏳ Polling S3 for completion (checking every {poll_interval} seconds)...")
                
                while time.time() - start_time < max_wait_time:
                    time.sleep(poll_interval)
                    elapsed = int(time.time() - start_time)
                    
                    # Check if file exists on S3
                    try:
                        head_resp = requests.head(s3_url, timeout=10)
                        if head_resp.status_code == 200:
                            print(f"\n✅ Poster ready in {elapsed} seconds!")
                            
                            # Download from S3
                            print(f"📥 Downloading from: {s3_url}")
                            download_resp = requests.get(s3_url, timeout=60)
                            
                            if download_resp.status_code == 200:
                                filename = f"poster_{os.path.basename(pdf_path).replace('.pdf', '')}.pptx"
                                with open(filename, 'wb') as out_file:
                                    out_file.write(download_resp.content)
                                
                                file_size = os.path.getsize(filename)
                                print(f"✅ Downloaded: {filename} ({file_size:,} bytes)")
                                return filename
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
    
    except requests.exceptions.Timeout:
        print(f"❌ Request timed out.")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    if len(sys.argv) != 2:
        print("Usage: python simple_api_test.py <pdf_file>")
        print("Example: python simple_api_test.py my_paper.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        sys.exit(1)
    
    if not pdf_path.lower().endswith('.pdf'):
        print("❌ File must be a PDF")
        sys.exit(1)
    
    # Generate poster
    result_file = generate_poster(pdf_path)
    
    if result_file:
        print(f"\n🎉 Success! Poster saved as: {result_file}")
        print(f"📁 Full path: {os.path.abspath(result_file)}")
    else:
        print("\n❌ Poster generation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 