import json
import os

def analyze_comprehensive_results(metadata_file):
    """Analyze comprehensive detection results"""
    with open(metadata_file, 'r') as f:
        data = json.load(f)
    
    print(f"\n=== COMPREHENSIVE ANALYSIS OF {os.path.basename(metadata_file)} ===")
    print(f"Total detections: {data['total_detections']}")
    
    detections = data['detections']
    
    # Sort by score
    detections.sort(key=lambda x: x['score'], reverse=True)
    
    print("\nHIGH CONFIDENCE DETECTIONS (>0.5):")
    for det in detections:
        if det['score'] > 0.5:
            box = det['box']
            area = det['area']
            print(f"  Score: {det['score']:.3f}, Area: {area}, Box: [{box[0]:.1f}, {box[1]:.1f}, {box[2]:.1f}, {box[3]:.1f}]")
    
    print("\nMEDIUM CONFIDENCE DETECTIONS (0.2-0.5):")
    for det in detections:
        if 0.2 <= det['score'] <= 0.5:
            box = det['box']
            area = det['area']
            print(f"  Score: {det['score']:.3f}, Area: {area}, Box: [{box[0]:.1f}, {box[1]:.1f}, {box[2]:.1f}, {box[3]:.1f}]")
    
    print("\nSMALL OBJECTS (<1,000 pixels) - Potential missing items:")
    for det in detections:
        if det['area'] < 1000:
            box = det['box']
            print(f"  Score: {det['score']:.3f}, Area: {det['area']}, Box: [{box[0]:.1f}, {box[1]:.1f}, {box[2]:.1f}, {box[3]:.1f}]")
    
    print("\nMEDIUM OBJECTS (1,000-10,000 pixels) - Potential furniture pieces:")
    for det in detections:
        if 1000 <= det['area'] <= 10000:
            box = det['box']
            print(f"  Score: {det['score']:.3f}, Area: {det['area']}, Box: [{box[0]:.1f}, {box[1]:.1f}, {box[2]:.1f}, {box[3]:.1f}]")
    
    print("\nLARGE OBJECTS (>10,000 pixels) - Major furniture:")
    for det in detections:
        if det['area'] > 10000:
            box = det['box']
            print(f"  Score: {det['score']:.3f}, Area: {det['area']}, Box: [{box[0]:.1f}, {box[1]:.1f}, {box[2]:.1f}, {box[3]:.1f}]")
    
    # Analyze box positions to understand what we're detecting
    print("\nBOX POSITION ANALYSIS (Top 15 by score):")
    for i, det in enumerate(detections[:15]):
        box = det['box']
        x_center = (box[0] + box[2]) / 2
        y_center = (box[1] + box[3]) / 2
        width = box[2] - box[0]
        height = box[3] - box[1]
        print(f"  Detection {i+1}: Center({x_center:.1f}, {y_center:.1f}), Size({width:.1f}x{height:.1f}), Score: {det['score']:.3f}, Area: {det['area']}")

# Analyze comprehensive results
metadata_file = "comprehensive_detected_masks/Room3_metadata_20250722_214744.json"

if os.path.exists(metadata_file):
    analyze_comprehensive_results(metadata_file)
else:
    print(f"File not found: {metadata_file}")

print("\n=== COMPREHENSIVE DETECTION SUMMARY ===")
print("This model uses:")
print("1. Multiple image enhancements (contrast, edge, sharpening, high contrast)")
print("2. Very low confidence thresholds (0.01-0.25)")
print("3. Very low NMS (0.4) for maximum detections")
print("4. Very small minimum area (20 pixels) for tiny objects")
print("5. Multiple scales (640-2560) for different object sizes")
print("6. High max detections (500) per run")
print("\nThis should detect more small objects like media consoles, candle, magazines, vase, and pot.") 