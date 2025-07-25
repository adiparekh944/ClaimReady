import json
import os

def analyze_detection_results(metadata_file):
    """Analyze detection results from metadata"""
    with open(metadata_file, 'r') as f:
        data = json.load(f)
    
    print(f"\n=== ANALYSIS OF {os.path.basename(metadata_file)} ===")
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
    
    print("\nLARGE OBJECTS (>10,000 pixels):")
    for det in detections:
        if det['area'] > 10000:
            box = det['box']
            print(f"  Score: {det['score']:.3f}, Area: {det['area']}, Box: [{box[0]:.1f}, {box[1]:.1f}, {box[2]:.1f}, {box[3]:.1f}]")
    
    print("\nSMALL OBJECTS (<1,000 pixels):")
    for det in detections:
        if det['area'] < 1000:
            box = det['box']
            print(f"  Score: {det['score']:.3f}, Area: {det['area']}, Box: [{box[0]:.1f}, {box[1]:.1f}, {box[2]:.1f}, {box[3]:.1f}]")
    
    # Analyze box positions to understand what we're detecting
    print("\nBOX POSITION ANALYSIS:")
    for i, det in enumerate(detections[:10]):  # Top 10 by score
        box = det['box']
        x_center = (box[0] + box[2]) / 2
        y_center = (box[1] + box[3]) / 2
        width = box[2] - box[0]
        height = box[3] - box[1]
        print(f"  Detection {i+1}: Center({x_center:.1f}, {y_center:.1f}), Size({width:.1f}x{height:.1f}), Score: {det['score']:.3f}")

# Analyze all our detection results
metadata_files = [
    "ultimate_detected_masks/Room3_metadata_20250722_213613.json",
    "refined_detected_masks/Room3_metadata_20250722_213257.json"
]

for metadata_file in metadata_files:
    if os.path.exists(metadata_file):
        analyze_detection_results(metadata_file)
    else:
        print(f"File not found: {metadata_file}")

print("\n=== SUMMARY ===")
print("Based on the analysis above, we can see what objects are being detected.")
print("The bounding box coordinates and areas help us understand:")
print("1. Large objects (likely furniture like couch, dresser)")
print("2. Medium objects (likely TV, chairs, tables)")
print("3. Small objects (likely items on surfaces)")
print("4. Position of detections (left/right, top/bottom of image)") 