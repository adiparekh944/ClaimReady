#!/usr/bin/env python3
"""
Test script for hardcoded room lookup system.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hardcoded_lookup import HardcodedRoomLookup, is_hardcoded_room, get_hardcoded_response

def test_hardcoded_system():
    """Test the hardcoded room lookup system."""
    print("Testing Hardcoded Room Lookup System")
    print("=" * 50)
    
    # Test 1: Check if hardcoded rooms are detected
    test_files = ["svdorm.jpg", "room3.jpg", "arnavroom.jpg", "normal_image.jpg", "SVDORM.JPG"]
    
    print("\n1. Testing hardcoded room detection:")
    for filename in test_files:
        is_hardcoded = is_hardcoded_room(filename)
        print(f"   {filename}: {'✓ HARDCODED' if is_hardcoded else '✗ Normal'}")
    
    # Test 2: Load hardcoded data
    print("\n2. Testing hardcoded data loading:")
    for filename in ["svdorm.jpg", "room3.jpg", "arnavroom.jpg"]:
        if is_hardcoded_room(filename):
            response = get_hardcoded_response(filename)
            items = response.get('items', [])
            total_value = sum(item.get('price_usd', 0) for item in items)
            print(f"   {filename}: {len(items)} items, Total Value: ${total_value:.2f}")
            
            # Show first item as example
            if items:
                first_item = items[0]
                print(f"      Example: {first_item.get('name')} - ${first_item.get('price_usd')}")
    
    # Test 3: Test lookup class directly
    print("\n3. Testing HardcodedRoomLookup class:")
    lookup = HardcodedRoomLookup()
    available_rooms = lookup.get_available_rooms()
    print(f"   Available rooms: {available_rooms}")
    
    # Test 4: Test error handling
    print("\n4. Testing error handling:")
    error_response = get_hardcoded_response("nonexistent.jpg")
    print(f"   Non-existent file: {error_response.get('error', 'No error')}")
    
    print("\n" + "=" * 50)
    print("Hardcoded system test completed!")

if __name__ == "__main__":
    test_hardcoded_system()
