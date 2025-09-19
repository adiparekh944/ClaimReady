"""
Hardcoded room data lookup system for ClaimReady.
Returns predefined data for specific room images (room1.jpg, room2.jpg, room3.jpg)
instead of running the full ML pipeline.
"""

import csv
import os
import json
from typing import List, Dict, Any, Optional

class HardcodedRoomLookup:
    def __init__(self, data_dir: str = "hardcoded_data"):
        self.data_dir = data_dir
        self.room_mappings = {
            "sv-dorm.jpg": "svdorm_data.csv",
            "room3.jpg": "room3_data.csv", 
            "arnav-hotel.jpeg": "arnavroom_data.csv"
        }
    
    def is_hardcoded_room(self, filename: str) -> bool:
        """Check if the filename corresponds to a hardcoded room."""
        return filename.lower() in self.room_mappings
    
    def load_room_data(self, filename: str) -> Optional[List[Dict[str, Any]]]:
        """Load hardcoded data for a specific room."""
        if not self.is_hardcoded_room(filename):
            return None
            
        csv_file = self.room_mappings[filename.lower()]
        csv_path = os.path.join(self.data_dir, csv_file)
        
        if not os.path.exists(csv_path):
            print(f"Warning: Hardcoded data file not found: {csv_path}")
            return None
            
        items = []
        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # Convert CSV row to the expected item format
                    item = {
                        "code": row["code"],
                        "imageAttachment": row["imageAttachment"],
                        "bbox": [
                            int(row["bbox_x1"]),
                            int(row["bbox_y1"]), 
                            int(row["bbox_x2"]),
                            int(row["bbox_y2"])
                        ],
                        "name": row["name"],
                        "category": row["category"],
                        "price_usd": float(row["price_usd"]),
                        "description": row["description"]
                    }
                    items.append(item)
            
            print(f"Loaded {len(items)} hardcoded items for {filename}")
            return items
            
        except Exception as e:
            print(f"Error loading hardcoded data for {filename}: {e}")
            return None
    
    def get_hardcoded_response(self, filename: str) -> Dict[str, Any]:
        """Get the complete hardcoded response for a room image."""
        items = self.load_room_data(filename)
        
        if items is None:
            return {
                "error": f"No hardcoded data found for {filename}",
                "items": [],
                "objects": [],
                "images": {}
            }
        
        # Create mock objects data (bounding boxes for visualization)
        objects = []
        for item in items:
            bbox = item["bbox"]
            # Add confidence score (1.0 for hardcoded items)
            objects.append([bbox[0], bbox[1], bbox[2], bbox[3], 1.0])
        
        # Create mock images data (empty for now, could add placeholder images)
        images = {}
        
        return {
            "items": items,
            "objects": objects,
            "images": images,
            "hardcoded": True,  # Flag to indicate this was hardcoded
            "room": filename
        }
    
    def get_available_rooms(self) -> List[str]:
        """Get list of available hardcoded rooms."""
        return list(self.room_mappings.keys())
    
    def add_room_data(self, filename: str, csv_file: str) -> bool:
        """Add a new room to the hardcoded system."""
        try:
            self.room_mappings[filename.lower()] = csv_file
            return True
        except Exception as e:
            print(f"Error adding room data: {e}")
            return False

# Global instance
hardcoded_lookup = HardcodedRoomLookup()

def is_hardcoded_room(filename: str) -> bool:
    """Convenience function to check if a filename is hardcoded."""
    return hardcoded_lookup.is_hardcoded_room(filename)

def get_hardcoded_response(filename: str) -> Dict[str, Any]:
    """Convenience function to get hardcoded response."""
    return hardcoded_lookup.get_hardcoded_response(filename)
