#!/usr/bin/env python3
"""
Test script to verify backend-frontend communication
"""
import requests
import base64
import json
import os

def test_backend_response():
    """Test the backend analyze-image endpoint with a sample image"""
    
    # Use one of the test images from the frontend/public directory
    image_path = "frontend/public/fire.jpg"
    
    if not os.path.exists(image_path):
        print(f"Test image not found: {image_path}")
        return
    
    # Read and encode the image
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    # Create form data
    files = {'image': ('test.jpg', image_data, 'image/jpeg')}
    
    try:
        # Send request to backend
        response = requests.post('http://localhost:8080/api/analyze-image', files=files)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Backend response successful!")
            print(f"Status: {result.get('status', 'N/A')}")
            print(f"Total items: {result.get('total_items', 0)}")
            print(f"Items array length: {len(result.get('items', []))}")
            print(f"Images object keys: {list(result.get('images', {}).keys())}")
            
            # Check items structure
            items = result.get('items', [])
            if items:
                print("\n📋 First item structure:")
                first_item = items[0]
                for key, value in first_item.items():
                    print(f"  {key}: {value} (type: {type(value).__name__})")
                
                # Check nullify field specifically
                nullify_values = [item.get('nullify') for item in items]
                print(f"\n🔍 Nullify field values: {nullify_values}")
                print(f"🔍 Nullify field types: {[type(v).__name__ for v in nullify_values]}")
                
                # Count items with nullify=False
                non_nullified = [item for item in items if item.get('nullify') == False]
                print(f"📊 Items with nullify=False: {len(non_nullified)}")
                print(f"📊 Total items: {len(items)}")
                
            else:
                print("❌ No items returned from backend")
                
        else:
            print(f"❌ Backend request failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing backend: {e}")

if __name__ == "__main__":
    print("🧪 Testing backend-frontend communication...")
    test_backend_response() 