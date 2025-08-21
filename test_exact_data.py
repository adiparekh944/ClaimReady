#!/usr/bin/env python3
"""
Test script to verify the exact data structure the user provided
"""
import requests
import json
import os

def test_exact_data_structure():
    """Test with the exact data structure provided by the user"""
    
    # Simulate the exact backend response structure
    mock_response = {
        "items": [
            {
                "code": "2",
                "imageAttachment": "crop2",
                "bbox": [1064, 1640, 2460, 2030],
                "name": "Area Rug",
                "category": "Textiles",
                "price_usd": 750,
                "description": "Modern patterned area rug, primarily grey and beige tones, situated under the coffee table and seating area. Provides warmth and defines the space.",
                "brand": "Unknown",
                "condition": "Good",
                "nullify": False
            },
            {
                "code": "0",
                "imageAttachment": "crop0",
                "bbox": [120, 1270, 1062, 1911],
                "name": "Armchair",
                "category": "Furniture",
                "price_usd": 900,
                "description": "Contemporary light grey fabric armchair with wooden legs, part of the living room seating arrangement. Offers comfortable single seating.",
                "brand": "Unknown",
                "condition": "Good",
                "nullify": False
            },
            {
                "code": "scene_6",
                "imageAttachment": "scene",
                "bbox": [0, 1690, 2400, 2244],
                "name": "Sectional Sofa",
                "category": "Furniture",
                "price_usd": 3500,
                "description": "Spacious light grey fabric sectional sofa forming the primary seating area in the living room. Designed for comfort and accommodating multiple people.",
                "brand": "Unknown",
                "condition": "Good",
                "nullify": False
            }
        ],
        "images": {
            "0": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",  # Mock base64
            "2": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...",  # Mock base64
            "scene_6": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."  # Mock base64
        },
        "total_items": 3,
        "total_value": 5150
    }
    
    print("🧪 Testing exact data structure from user...")
    print(f"📋 Items count: {len(mock_response['items'])}")
    print(f"🖼️ Images count: {len(mock_response['images'])}")
    
    # Test frontend processing logic
    items = mock_response['items']
    images = mock_response['images']
    
    # Simulate frontend segments creation
    segments = []
    for code, image in images.items():
        # Handle different code formats: '0', '1', 'scene_6', 'crop0', etc.
        import re
        let_index = None
        
        # Extract numeric part from various code formats
        numeric_match = re.search(r'(\d+)$', code)
        if numeric_match:
            let_index = int(numeric_match.group(1))
        elif code.startswith('scene_'):
            # For scene codes like 'scene_6', extract the number after underscore
            scene_match = re.search(r'scene_(\d+)', code)
            let_index = int(scene_match.group(1)) if scene_match else 0
        elif code.startswith('crop'):
            # For crop codes like 'crop0', extract the number
            crop_match = re.search(r'crop(\d+)', code)
            let_index = int(crop_match.group(1)) if crop_match else 0
        else:
            # Try to parse as number directly
            let_index = int(code) if code.isdigit() else 0
        
        segments.append({
            'index': let_index,
            'image': image,
            'original_box': [0, 0, 0, 0],
            'original_size': [0, 0],
            'normalized_size': [0, 0]
        })
    
    print(f"📐 Segments created: {len(segments)}")
    print(f"📐 Segment indices: {[s['index'] for s in segments]}")
    
    # Test item-segment matching
    print("\n🔗 Item-Segment Matching:")
    for item in items:
        code_str = str(item['code'])
        let_code_num = None
        
        # Extract numeric part from various code formats
        numeric_match = re.search(r'(\d+)$', code_str)
        if numeric_match:
            let_code_num = numeric_match.group(1)
        elif code_str.startswith('scene_'):
            scene_match = re.search(r'scene_(\d+)', code_str)
            let_code_num = scene_match.group(1) if scene_match else '0'
        elif code_str.startswith('crop'):
            crop_match = re.search(r'crop(\d+)', code_str)
            let_code_num = crop_match.group(1) if crop_match else '0'
        else:
            let_code_num = code_str
        
        matching_segment = next((s for s in segments if str(s['index']) == let_code_num), None)
        
        print(f"  Item '{item['name']}' (code: {item['code']}) -> Segment: {'Found' if matching_segment else 'Not found'}")
    
    # Test filtering
    filtered_items = [item for item in items if item.get('nullify') == False]
    print(f"\n✅ Items after nullify filtering: {len(filtered_items)}")
    
    print(f"\n📈 Summary:")
    print(f"  - Backend items: {len(items)}")
    print(f"  - Non-nullified items: {len(filtered_items)}")
    print(f"  - Segments created: {len(segments)}")
    print(f"  - Items that should display: {len(filtered_items)}")
    
    if len(filtered_items) > 0:
        print("✅ Items should be visible in the frontend table!")
    else:
        print("❌ No items will be displayed in the frontend table!")

if __name__ == "__main__":
    test_exact_data_structure() 