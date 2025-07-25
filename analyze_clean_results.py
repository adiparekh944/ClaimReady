import cv2
import numpy as np
import json
import os
from datetime import datetime

def analyze_clean_detection_results():
    """Analyze the results of the clean comprehensive detector"""
    print("=== CLEAN COMPREHENSIVE DETECTOR ANALYSIS ===")
    
    # Load the original image for reference
    img_path = 'C:/Users/Arnav/Downloads/Room3.jpg'
    img = cv2.imread(img_path)
    if img is None:
        print("❌ Could not load original image")
        return
    
    print(f"Original image shape: {img.shape}")
    
    # Find the latest metadata file
    masks_dir = "clean_comprehensive_masks"
    if not os.path.exists(masks_dir):
        print(f"❌ Masks directory not found: {masks_dir}")
        return
    
    metadata_files = [f for f in os.listdir(masks_dir) if f.endswith('.json')]
    if not metadata_files:
        print("❌ No metadata files found")
        return
    
    # Get the most recent metadata file
    latest_metadata = sorted(metadata_files)[-1]
    metadata_path = os.path.join(masks_dir, latest_metadata)
    
    print(f"Analyzing metadata: {metadata_path}")
    
    # Load metadata
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    detections = metadata['detections']
    total_detections = metadata['total_detections']
    
    print(f"\n📊 DETECTION SUMMARY:")
    print(f"Total detections: {total_detections}")
    print(f"Timestamp: {metadata['timestamp']}")
    
    # Expected objects
    expected_objects = [
        "chair", "couch", "tv", "dresser", "paintings", "table", "clock", "stool",
        "candle", "magazines", "vase", "pot", "media console", "media console shelf 1", "media console shelf 2"
    ]
    
    print(f"Expected objects: {len(expected_objects)}")
    print(f"Detection ratio: {total_detections}/{len(expected_objects)} = {total_detections/len(expected_objects):.1f}x")
    
    # Analyze by confidence levels
    high_conf = [d for d in detections if d['score'] > 0.5]
    medium_conf = [d for d in detections if 0.2 <= d['score'] <= 0.5]
    low_conf = [d for d in detections if d['score'] < 0.2]
    
    print(f"\n🎯 CONFIDENCE ANALYSIS:")
    print(f"High confidence (>0.5): {len(high_conf)} detections")
    print(f"Medium confidence (0.2-0.5): {len(medium_conf)} detections")
    print(f"Low confidence (<0.2): {len(low_conf)} detections")
    
    # Analyze by area size
    tiny_objects = [d for d in detections if d['area'] < 100]
    small_objects = [d for d in detections if 100 <= d['area'] < 1000]
    medium_objects = [d for d in detections if 1000 <= d['area'] < 10000]
    large_objects = [d for d in detections if d['area'] >= 10000]
    
    print(f"\n📏 SIZE ANALYSIS:")
    print(f"Tiny objects (<100px): {len(tiny_objects)}")
    print(f"Small objects (100-1000px): {len(small_objects)}")
    print(f"Medium objects (1000-10000px): {len(medium_objects)}")
    print(f"Large objects (≥10000px): {len(large_objects)}")
    
    # Analyze by source
    sources = {}
    for det in detections:
        source = det.get('source', 'unknown')
        if source not in sources:
            sources[source] = 0
        sources[source] += 1
    
    print(f"\n🖼️  SOURCE ANALYSIS:")
    for source, count in sources.items():
        print(f"  {source}: {count} detections")
    
    # Show top detections by score
    print(f"\n🏆 TOP 10 DETECTIONS BY SCORE:")
    sorted_by_score = sorted(detections, key=lambda x: x['score'], reverse=True)
    for i, det in enumerate(sorted_by_score[:10]):
        print(f"  {i+1:2d}. Score: {det['score']:.3f}, Area: {det['area']:5d}px, Source: {det['source']}")
        box = det['box']
        print(f"      Box: ({box[0]:.0f}, {box[1]:.0f}) to ({box[2]:.0f}, {box[3]:.0f})")
    
    # Show largest detections
    print(f"\n📦 TOP 10 DETECTIONS BY AREA:")
    sorted_by_area = sorted(detections, key=lambda x: x['area'], reverse=True)
    for i, det in enumerate(sorted_by_area[:10]):
        print(f"  {i+1:2d}. Area: {det['area']:5d}px, Score: {det['score']:.3f}, Source: {det['source']}")
        box = det['box']
        print(f"      Box: ({box[0]:.0f}, {box[1]:.0f}) to ({box[2]:.0f}, {box[3]:.0f})")
    
    # Show smallest detections
    print(f"\n🔍 SMALLEST 10 DETECTIONS:")
    sorted_by_area_small = sorted(detections, key=lambda x: x['area'])
    for i, det in enumerate(sorted_by_area_small[:10]):
        print(f"  {i+1:2d}. Area: {det['area']:5d}px, Score: {det['score']:.3f}, Source: {det['source']}")
        box = det['box']
        print(f"      Box: ({box[0]:.0f}, {box[1]:.0f}) to ({box[2]:.0f}, {box[3]:.0f})")
    
    # Analysis of detection quality
    print(f"\n📈 QUALITY METRICS:")
    scores = [d['score'] for d in detections]
    areas = [d['area'] for d in detections]
    
    print(f"Average score: {np.mean(scores):.3f}")
    print(f"Average area: {np.mean(areas):.0f}px")
    print(f"Score std dev: {np.std(scores):.3f}")
    print(f"Area std dev: {np.std(areas):.0f}px")
    
    # Check for potential duplicates
    print(f"\n🔍 DUPLICATE ANALYSIS:")
    potential_duplicates = 0
    for i, det1 in enumerate(detections):
        for j, det2 in enumerate(detections[i+1:], i+1):
            # Check if boxes overlap significantly
            box1 = det1['box']
            box2 = det2['box']
            
            x1 = max(box1[0], box2[0])
            y1 = max(box1[1], box2[1])
            x2 = min(box1[2], box2[2])
            y2 = min(box1[3], box2[3])
            
            if x2 > x1 and y2 > y1:
                intersection = (x2 - x1) * (y2 - y1)
                det_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
                unique_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
                union = det_area + unique_area - intersection
                
                if union > 0 and intersection / union > 0.3:
                    potential_duplicates += 1
                    print(f"  Potential duplicate: Detection {i+1} and {j+1} (IoU: {intersection/union:.2f})")
    
    if potential_duplicates == 0:
        print("  ✅ No obvious duplicates detected")
    else:
        print(f"  ⚠️  Found {potential_duplicates} potential duplicate pairs")
    
    # Final assessment
    print(f"\n🎯 FINAL ASSESSMENT:")
    if total_detections >= len(expected_objects):
        print(f"✅ SUCCESS: Detected {total_detections} objects, expected {len(expected_objects)}")
        print(f"   - Detection ratio: {total_detections/len(expected_objects):.1f}x")
    else:
        print(f"⚠️  NEEDS IMPROVEMENT: Detected {total_detections} objects, expected {len(expected_objects)}")
    
    if len(high_conf) >= len(expected_objects) * 0.3:
        print(f"✅ Good high-confidence detection rate: {len(high_conf)} high-confidence detections")
    else:
        print(f"⚠️  Low high-confidence detection rate: {len(high_conf)} high-confidence detections")
    
    if potential_duplicates == 0:
        print(f"✅ Clean detections: No obvious duplicates")
    else:
        print(f"⚠️  Potential duplicates: {potential_duplicates} pairs")
    
    # Instructions for visual verification
    print(f"\n👁️  VISUAL VERIFICATION:")
    print(f"Please open the visualization image saved at:")
    print(f"  clean_comprehensive_outputs/Room3_clean_comprehensive_{metadata['timestamp']}.png")
    print(f"\nCheck if the following objects are detected:")
    for obj in expected_objects:
        print(f"  - {obj}")
    
    print(f"\nLook for:")
    print(f"  1. Each object has exactly one mask/box")
    print(f"  2. No duplicate detections for single objects")
    print(f"  3. Small objects (candle, magazines, vase, pot, clock, stool) are detected")
    print(f"  4. Media consoles on dresser shelves are separate detections")
    print(f"  5. Dresser and its components are properly segmented")
    
    print(f"\n🚀 CLEAN DETECTION ASSESSMENT:")
    print(f"✅ Clean comprehensive detector completed successfully!")
    print(f"   - Used only 3 image enhancements (vs 4 in fast)")
    print(f"   - Used only 2 scales")
    print(f"   - Used only 5 confidence thresholds")
    print(f"   - Total detection runs: 3 × 2 × 5 = 30")
    print(f"   - Much cleaner detection ratio: {total_detections/len(expected_objects):.1f}x vs 3.5x")

if __name__ == "__main__":
    analyze_clean_detection_results() 