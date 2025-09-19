#!/usr/bin/env python3
"""
Test script for hardcoded room API endpoints.
"""

import requests
import base64
import json
import os

def create_test_image_base64():
    """Create a simple test image as base64."""
    # Create a simple 100x100 red image
    from PIL import Image
    import io
    
    img = Image.new('RGB', (100, 100), color='red')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    img_bytes = buffer.getvalue()
    return base64.b64encode(img_bytes).decode('utf-8')

def test_hardcoded_api():
    """Test the API with hardcoded room filenames."""
    base_url = "http://localhost:8080"  # Adjust if your server runs on different port
    
    print("Testing Hardcoded Room API")
    print("=" * 50)
    
    # Test single image endpoint
    print("\n1. Testing single image endpoint with hardcoded rooms:")
    
    test_cases = [
        {"filename": "room1.jpg", "expected_items": 5},
        {"filename": "room2.jpg", "expected_items": 5}, 
        {"filename": "room3.jpg", "expected_items": 5},
        {"filename": "normal_image.jpg", "expected_items": "unknown"}
    ]
    
    for test_case in test_cases:
        filename = test_case["filename"]
        print(f"\n   Testing {filename}:")
        
        try:
            # Create test image
            test_image_data = create_test_image_base64()
            
            # Prepare request
            files = {
                'image': (filename, base64.b64decode(test_image_data), 'image/jpeg')
            }
            
            # Make request
            response = requests.post(f"{base_url}/api/analyze-image", files=files)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                is_hardcoded = data.get('hardcoded', False)
                total_value = data.get('total_value', 0)
                
                print(f"      Status: ✓ Success")
                print(f"      Hardcoded: {'Yes' if is_hardcoded else 'No'}")
                print(f"      Items: {len(items)}")
                print(f"      Total Value: ${total_value:.2f}")
                
                if items and len(items) > 0:
                    print(f"      First item: {items[0].get('name')} - ${items[0].get('price_usd')}")
            else:
                print(f"      Status: ✗ Error {response.status_code}")
                print(f"      Response: {response.text}")
                
        except Exception as e:
            print(f"      Error: {e}")
    
    print("\n" + "=" * 50)
    print("API test completed!")

if __name__ == "__main__":
    test_hardcoded_api()
