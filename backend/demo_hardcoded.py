#!/usr/bin/env python3
"""
Demo script showing how the hardcoded room system works.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hardcoded_lookup import get_hardcoded_response, is_hardcoded_room

def demo_hardcoded_rooms():
    """Demonstrate the hardcoded room system."""
    print("🏠 ClaimReady Hardcoded Room System Demo")
    print("=" * 60)
    
    # Test different room types
    rooms = ["svdorm.jpg", "room3.jpg", "arnavroom.jpg", "normal_image.jpg"]
    
    for room in rooms:
        print(f"\n📸 Testing: {room}")
        print("-" * 40)
        
        # Check if it's a hardcoded room
        if is_hardcoded_room(room):
            print("✅ Hardcoded room detected!")
            
            # Get the hardcoded response
            response = get_hardcoded_response(room)
            
            if response.get('error'):
                print(f"❌ Error: {response['error']}")
            else:
                items = response.get('items', [])
                total_value = sum(item.get('price_usd', 0) for item in items)
                
                print(f"📊 Found {len(items)} items")
                print(f"💰 Total estimated value: ${total_value:.2f}")
                print("\n📋 Items:")
                
                for i, item in enumerate(items, 1):
                    name = item.get('name', 'Unknown')
                    price = item.get('price_usd', 0)
                    category = item.get('category', 'Unknown')
                    print(f"   {i}. {name} ({category}) - ${price:.2f}")
        else:
            print("🔄 Normal image - would use ML pipeline")
    
    print("\n" + "=" * 60)
    print("✨ Demo completed!")
    print("\nTo use this in your API:")
    print("1. Upload an image named 'svdorm.jpg', 'room3.jpg', or 'arnavroom.jpg'")
    print("2. The system will automatically return hardcoded data")
    print("3. Check the response for 'hardcoded': true flag")

if __name__ == "__main__":
    demo_hardcoded_rooms()
