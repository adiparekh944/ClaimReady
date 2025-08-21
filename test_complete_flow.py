#!/usr/bin/env python3
"""
Test script to verify the complete frontend-backend flow
"""
import requests
import json
import os

def test_complete_flow():
    """Test the complete flow from frontend to backend and back"""
    
    # Use one of the test images from the frontend/public directory
    image_path = "frontend/public/fire.jpg"
    
    if not os.path.exists(image_path):
        print(f"Test image not found: {image_path}")
        return
    
    # Read and encode the image
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    # Create form data (simulating frontend FormData)
    files = {'image': ('test.jpg', image_data, 'image/jpeg')}
    
    try:
        # Send request to backend (simulating frontend fetch)
        print("🔄 Sending request to backend...")
        response = requests.post('http://localhost:8080/api/analyze-image', files=files)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Backend response received!")
            
            # Simulate frontend processing
            print("\n📊 Frontend Processing Simulation:")
            
            # Check if items exist
            items = result.get('items', [])
            if not items:
                print("❌ No items returned from backend")
                return
            
            print(f"📋 Total items received: {len(items)}")
            
            # Check nullify field
            nullified_items = [item for item in items if item.get('nullify') == True]
            non_nullified_items = [item for item in items if item.get('nullify') == False]
            
            print(f"🔍 Items with nullify=True: {len(nullified_items)}")
            print(f"🔍 Items with nullify=False: {len(non_nullified_items)}")
            
            # Simulate frontend segments creation
            images = result.get('images', {})
            print(f"🖼️ Images object keys: {list(images.keys())}")
            
            # Create segments (simulating frontend logic)
            segments = []
            for code, image in images.items():
                # Extract numeric part from codes like 'scene_0', '0', '1', etc.
                import re
                numeric_match = re.search(r'(\d+)$', code)
                index = int(numeric_match.group(1)) if numeric_match else int(code)
                
                segments.append({
                    'index': index,
                    'image': image,
                    'original_box': [0, 0, 0, 0],
                    'original_size': [0, 0],
                    'normalized_size': [0, 0]
                })
            
            print(f"📐 Segments created: {len(segments)}")
            print(f"📐 Segment indices: {[s['index'] for s in segments]}")
            
            # Simulate ItemTable filtering
            filtered_items = [item for item in items if item.get('nullify') == False]
            print(f"✅ Items after nullify filtering: {len(filtered_items)}")
            
            # Check if items have required fields
            required_fields = ['code', 'name', 'category', 'brand', 'condition', 'price_usd', 'description', 'nullify']
            for i, item in enumerate(filtered_items[:3]):  # Check first 3 items
                missing_fields = [field for field in required_fields if field not in item]
                if missing_fields:
                    print(f"⚠️ Item {i} missing fields: {missing_fields}")
                else:
                    print(f"✅ Item {i} has all required fields")
            
            # Simulate segment matching
            print("\n🔗 Segment-Item Matching:")
            for item in filtered_items[:3]:  # Check first 3 items
                code_str = str(item['code']).replace('CODE:', '')
                numeric_match = re.search(r'(\d+)$', code_str)
                code_num = numeric_match.group(1) if numeric_match else code_str
                
                matching_segment = next((s for s in segments if str(s['index']) == code_num), None)
                
                print(f"  Item '{item['name']}' (code: {item['code']}) -> Segment: {'Found' if matching_segment else 'Not found'}")
            
            # Summary
            print(f"\n📈 Summary:")
            print(f"  - Backend items: {len(items)}")
            print(f"  - Non-nullified items: {len(filtered_items)}")
            print(f"  - Segments created: {len(segments)}")
            print(f"  - Items that should display: {len(filtered_items)}")
            
            if len(filtered_items) > 0:
                print("✅ Items should be visible in the frontend table!")
            else:
                print("❌ No items will be displayed in the frontend table!")
                
        else:
            print(f"❌ Backend request failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing complete flow: {e}")

if __name__ == "__main__":
    print("🧪 Testing complete frontend-backend flow...")
    test_complete_flow() 