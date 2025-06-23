#!/usr/bin/env python3
"""
Simple Paper2Poster API Test Example

A minimal example showing how to use the Paper2Poster API:
1. Upload a PDF
2. Wait for completion and get the PowerPoint file directly

Usage:
    python simple_api_test.py path/to/paper.pdf
"""

import sys
import requests
import os

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
    
    # 1. Check if API is healthy
    try:
        health_resp = requests.get(f"{api_url}/health", timeout=5)
        if health_resp.status_code != 200:
            print("❌ API is not healthy")
            return None
        print("✅ API is healthy")
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return None
    
    # 2. Upload PDF and generate poster (this now waits for completion)
    try:
        with open(pdf_path, 'rb') as f:
            files = {'pdf_file': f}
            data = {
                'model_name_t': '4o',
                'model_name_v': '4o',
                'poster_width_inches': 48,
                'poster_height_inches': 36,
                'return_type': 'pptx'  # Request PPTX file directly
            }
            
            print("📤 Uploading PDF and generating poster (this may take a few minutes)...")
            
            # Increase timeout since generation takes time
            response = requests.post(
                f"{api_url}/generate-poster", 
                files=files, 
                data=data,
                timeout=600  # 10 minute timeout
            )
            
            if response.status_code != 200:
                print(f"❌ Generation failed: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Error: {response.text}")
                return None
            
            # The response is the PPTX file
            filename = f"poster_{os.path.basename(pdf_path).replace('.pdf', '')}.pptx"
            
            # Save the file
            with open(filename, 'wb') as out_file:
                out_file.write(response.content)
            
            file_size = os.path.getsize(filename)
            print(f"✅ Downloaded: {filename} ({file_size:,} bytes)")
            return filename
    
    except requests.exceptions.Timeout:
        print(f"❌ Request timed out. Poster generation can take several minutes.")
        print("   Try increasing the timeout or check the server logs.")
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