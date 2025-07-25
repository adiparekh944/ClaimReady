import cv2
import numpy as np
import json
import os
from datetime import datetime

def analyze_image_and_detections():
    """Analyze the actual image and compare with detection results"""
    
    # Load the original image
    img_path = 'C:/Users/Arnav/Downloads/Room3.jpg'
    img = cv2.imread(img_path)
    
    if img is None:
        print("Could not load image!")
        return
    
    print(f"Image shape: {img.shape}")
    print(f"Image size: {img.shape[1]}x{img.shape[0]} pixels")
    
    # Load detection results
    metadata_file = "final_universal_detected_masks/Room3_metadata_20250722_221514.json"
    
    if not os.path.exists(metadata_file):
        print(f"Metadata file not found: {metadata_file}")
        return
    
    with open(metadata_file, 'r') as f:
        data = json.load(f)
    
    detections = data['detections']
    print(f"\nTotal detections: {len(detections)}")
    
    # Expected objects from your list
    expected_objects = [
        "chair", "couch", "tv", "dresser", "paintings", "table", "clock", "stool",
        "candle", "magazines", "vase", "pot", "media console", "media console shelf 1", "media console shelf 2"
    ]
    
    print(f"\nExpected objects: {len(expected_objects)}")
    for obj in expected_objects:
        print(f"  - {obj}")
    
    # Analyze detections by area and position
    print(f"\n=== DETECTION ANALYSIS ===")
    
    # Group detections by area size
    tiny_objects = []      # < 500 pixels
    small_objects = []     # 500-2000 pixels  
    medium_objects = []    # 2000-10000 pixels
    large_objects = []     # > 10000 pixels
    
    for det in detections:
        area = det['area']
        score = det['score']
        box = det['box']
        
        if area < 500:
            tiny_objects.append(det)
        elif area < 2000:
            small_objects.append(det)
        elif area < 10000:
            medium_objects.append(det)
        else:
            large_objects.append(det)
    
    print(f"Tiny objects (<500px): {len(tiny_objects)}")
    print(f"Small objects (500-2000px): {len(small_objects)}")
    print(f"Medium objects (2000-10000px): {len(medium_objects)}")
    print(f"Large objects (>10000px): {len(large_objects)}")
    
    # Analyze by confidence
    high_conf = [d for d in detections if d['score'] > 0.5]
    medium_conf = [d for d in detections if 0.2 <= d['score'] <= 0.5]
    low_conf = [d for d in detections if d['score'] < 0.2]
    
    print(f"\nHigh confidence (>0.5): {len(high_conf)}")
    print(f"Medium confidence (0.2-0.5): {len(medium_conf)}")
    print(f"Low confidence (<0.2): {len(low_conf)}")
    
    # Show top detections with their positions
    print(f"\n=== TOP 10 DETECTIONS BY SCORE ===")
    sorted_detections = sorted(detections, key=lambda x: x['score'], reverse=True)
    
    for i, det in enumerate(sorted_detections[:10]):
        box = det['box']
        x_center = (box[0] + box[2]) / 2
        y_center = (box[1] + box[3]) / 2
        width = box[2] - box[0]
        height = box[3] - box[1]
        
        print(f"  {i+1}. Score: {det['score']:.3f}, Area: {det['area']}, "
              f"Center: ({x_center:.1f}, {y_center:.1f}), Size: {width:.1f}x{height:.1f}")
    
    # Analyze small objects that might be missing items
    print(f"\n=== SMALL OBJECTS (<2000px) - POTENTIAL MISSING ITEMS ===")
    small_detections = tiny_objects + small_objects
    small_detections.sort(key=lambda x: x['score'], reverse=True)
    
    for i, det in enumerate(small_detections[:15]):  # Show top 15 small objects
        box = det['box']
        x_center = (box[0] + box[2]) / 2
        y_center = (box[1] + box[3]) / 2
        
        print(f"  {i+1}. Score: {det['score']:.3f}, Area: {det['area']}, "
              f"Center: ({x_center:.1f}, {y_center:.1f})")
    
    # Check if we have the visualization image
    vis_path = "final_universal_detection_outputs/Room3_final_detection_20250722_221514.png"
    if os.path.exists(vis_path):
        print(f"\nVisualization saved at: {vis_path}")
        print("Please check this image to see what was actually detected!")
    else:
        print(f"\nVisualization not found at: {vis_path}")
    
    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"We detected {len(detections)} objects total")
    print(f"We expected to detect {len(expected_objects)} specific objects")
    print(f"Small objects detected: {len(small_detections)}")
    print(f"High confidence detections: {len(high_conf)}")
    
    # Recommendations
    print(f"\n=== RECOMMENDATIONS ===")
    if len(high_conf) < 5:
        print("- Need more high-confidence detections")
    if len(small_detections) < 10:
        print("- Need more small object detections")
    if len(detections) < 20:
        print("- Overall detection count seems low")
    
    print(f"\nPlease check the visualization image to see what was actually detected!")

if __name__ == "__main__":
    analyze_image_and_detections() 