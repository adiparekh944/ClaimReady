#!/usr/bin/env python3
"""
Test script to verify multi-image processing
"""
import requests
import base64
import json
import os

def test_multi_image():
    """Test the multi-image endpoint with two test images"""
    
    # Use two test images from the frontend/public directory
    image_paths = ["frontend/public/fire.jpg", "frontend/public/flood.jpeg"]
    
    # Check if images exist
    for path in image_paths:
        if not os.path.exists(path):
            print(f"Test image not found: {path}")
            return
    
    # Read and encode images
    image_data_array = []
    for path in image_paths:
        with open(path, "rb") as f:
            image_data = f.read()
            # Convert to base64 without data URL prefix
            base64_data = base64.b64encode(image_data).decode('utf-8')
            image_data_array.append(base64_data)
    
    try:
        # Send request to multi-image endpoint
        print("🔄 Sending multi-image request to backend...")
        response = requests.post('http://localhost:8080/api/analyze-multiple-images', 
                               json={'images': image_data_array})
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Multi-image response received!")
            print(f"Status: {result.get('status', 'N/A')}")
            print(f"Total items: {result.get('total_items', 0)}")
            print(f"Items array length: {len(result.get('items', []))}")
            print(f"Images object keys: {list(result.get('images', {}).keys())}")
            
            # Check items structure
            items = result.get('items', [])
            if items:
                print("\n📋 First 5 items detail:")
                for i, item in enumerate(items[:5]):
                    print(f"  Item {i}:", {
                        'code': item.get('code'),
                        'name': item.get('name'),
                        'category': item.get('category'),
                        'price_usd': item.get('price_usd'),
                        'nullify': item.get('nullify'),
                        'nullifyType': type(item.get('nullify')).__name__
                    })
                
                # Check for code conflicts
                codes = [item.get('code') for item in items]
                unique_codes = set(codes)
                print(f"\n🔍 Code analysis:")
                print(f"  Total items: {len(items)}")
                print(f"  Unique codes: {len(unique_codes)}")
                print(f"  All codes: {codes}")
                
                if len(codes) != len(unique_codes):
                    print("⚠️ CODE CONFLICT DETECTED!")
                    from collections import Counter
                    code_counts = Counter(codes)
                    duplicates = {code: count for code, count in code_counts.items() if count > 1}
                    print(f"  Duplicate codes: {duplicates}")
                else:
                    print("✅ No code conflicts detected")
                
                # Check nullify field
                nullify_values = [item.get('nullify') for item in items]
                non_nullified = [item for item in items if item.get('nullify') == False]
                print(f"\n🔍 Nullify analysis:")
                print(f"  Items with nullify=False: {len(non_nullified)}")
                print(f"  Total items: {len(items)}")
                
            else:
                print("❌ No items returned from multi-image endpoint")
                
        else:
            print(f"❌ Multi-image request failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing multi-image: {e}")

if __name__ == "__main__":
    print("🧪 Testing multi-image processing...")
    test_multi_image() 