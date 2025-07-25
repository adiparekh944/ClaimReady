import time
import os
import cv2
import numpy as np
import torch
from ultralytics import YOLO
from datetime import datetime
import json

# ================= CONFIGURATION =================
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "yolo11n-seg.pt")

# Quick detection parameters for missing objects
SCALES = [1280, 1920]  # Focus on medium scales
CONF_THRESHOLDS = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1]  # Very low thresholds
IOU_NMS = 0.1  # Very low NMS for maximum detections
MASK_IOU_THRESH = 0.1  # Very low threshold for duplicate removal
MIN_MASK_AREA = 5  # Extremely small minimum
MAX_MASK_AREA = 50000  # Reasonable maximum

# Output directories
OUTPUT_DIR = "quick_missing_detection_outputs"
MASKS_DIR = "quick_missing_detected_masks"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MASKS_DIR, exist_ok=True)

# Load model once
yolo_model = YOLO(YOLO_MODEL_PATH)

# ================= HELPERS =================

def get_timestamp():
    """Get current timestamp for unique filenames"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def mask_iou(mask1, mask2):
    """Calculate IoU between two masks"""
    if mask1 is None or mask2 is None:
        return 0.0
    intersection = np.logical_and(mask1, mask2)
    union = np.logical_or(mask1, mask2)
    if np.sum(union) == 0:
        return 0.0
    return np.sum(intersection) / np.sum(union)

def mask_area(mask):
    """Calculate area of mask"""
    if mask is None:
        return 0
    return np.sum(mask > 0)

def process_masks(results, img_shape):
    """Extract and process masks from YOLO results"""
    masks = []
    scores = []
    boxes = []
    
    if results.masks is not None:
        for i, mask_tensor in enumerate(results.masks.data):
            # Convert tensor to numpy and resize to original image size
            mask = mask_tensor.cpu().numpy()
            mask = cv2.resize(mask, (img_shape[1], img_shape[0]))
            mask = (mask > 0.1).astype(np.uint8)  # Very low threshold
            
            area = mask_area(mask)
            
            # Filter by area constraints
            if MIN_MASK_AREA <= area <= MAX_MASK_AREA:
                masks.append(mask)
                
                # Get corresponding score and box
                if results.boxes is not None and i < len(results.boxes):
                    score = float(results.boxes[i].conf[0])
                    box = results.boxes[i].xyxy[0].cpu().numpy()
                else:
                    score = 1.0
                    box = [0, 0, img_shape[1], img_shape[0]]
                
                scores.append(score)
                boxes.append(box)
    
    return masks, scores, boxes

def is_duplicate_mask(mask1, mask2, threshold=0.2):
    """Check if two masks are duplicates"""
    return mask_iou(mask1, mask2) > threshold

def remove_duplicates(detections):
    """Remove duplicate detections"""
    if not detections:
        return []
    
    # Sort by score in descending order
    detections.sort(key=lambda x: x['score'], reverse=True)
    
    unique_detections = []
    for det in detections:
        should_add = True
        
        # Check against all existing unique detections
        for unique_det in unique_detections:
            if is_duplicate_mask(det['mask'], unique_det['mask']):
                should_add = False
                break
        
        if should_add:
            unique_detections.append(det)
    
    return unique_detections

def filter_by_quality(detections, min_score=0.001, min_area=5):
    """Filter detections by quality metrics - extremely permissive"""
    filtered = []
    for det in detections:
        score = det['score']
        area = mask_area(det['mask'])
        
        # Keep everything with very low thresholds
        if score >= min_score or area >= min_area:
            filtered.append(det)
    
    return filtered

def quick_detection(img, model):
    """Run quick detection with minimal processing"""
    all_detections = []
    
    # Original image detection
    for scale in SCALES:
        for conf_thresh in CONF_THRESHOLDS:
            results = model.predict(
                img, 
                imgsz=scale, 
                conf=conf_thresh, 
                iou=IOU_NMS, 
                verbose=False,
                max_det=1000  # Very high max detections
            )
            
            for result in results:
                masks, scores, boxes = process_masks(result, img.shape[:2])
                
                for mask, score, box in zip(masks, scores, boxes):
                    detection = {
                        'mask': mask,
                        'score': score,
                        'box': box,
                        'scale': scale,
                        'conf_thresh': conf_thresh,
                        'source': 'original'
                    }
                    all_detections.append(detection)
    
    # Enhanced image detection (simple contrast enhancement)
    enhanced = cv2.convertScaleAbs(img, alpha=1.3, beta=10)
    for scale in SCALES:
        for conf_thresh in CONF_THRESHOLDS:
            results = model.predict(
                enhanced, 
                imgsz=scale, 
                conf=conf_thresh, 
                iou=IOU_NMS, 
                verbose=False,
                max_det=1000
            )
            
            for result in results:
                masks, scores, boxes = process_masks(result, img.shape[:2])
                
                for mask, score, box in zip(masks, scores, boxes):
                    detection = {
                        'mask': mask,
                        'score': score,
                        'box': box,
                        'scale': scale,
                        'conf_thresh': conf_thresh,
                        'source': 'enhanced'
                    }
                    all_detections.append(detection)
    
    print(f"Total detections before filtering: {len(all_detections)}")
    return all_detections

def visualize_detections(img, detections, title, save_path):
    """Visualize detections and save to disk"""
    vis = img.copy()
    
    # Create mask overlay
    mask_overlay = np.zeros_like(img)
    
    # Generate colors for each detection
    colors = []
    for i in range(len(detections)):
        hue = int(180 * i / max(1, len(detections)))
        color = cv2.cvtColor(np.uint8([[[hue, 255, 255]]]), cv2.COLOR_HSV2BGR)[0][0]
        colors.append(tuple(int(c) for c in color))
    
    for i, det in enumerate(detections):
        mask = det['mask']
        score = det['score']
        box = det['box']
        
        if mask is not None:
            # Use different color for each detection
            color = colors[i % len(colors)] if i < len(colors) else (255, 255, 255)
            
            # Apply colored mask
            mask_overlay[mask > 0] = color
            
            # Draw bounding box
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
            
            # Add score text
            cv2.putText(vis, f'{score:.3f}', (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.putText(vis, f'{score:.3f}', (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Blend mask overlay with original image
    if np.any(mask_overlay):
        vis = cv2.addWeighted(vis, 0.4, mask_overlay, 0.6, 0)
    
    # Save image
    cv2.imwrite(save_path, vis)
    print(f"Saved visualization: {save_path}")

def save_detection_results(detections, output_dir, base_filename):
    """Save detection results and metadata"""
    timestamp = get_timestamp()
    
    # Save individual masks
    for i, det in enumerate(detections):
        mask = det['mask']
        score = det['score']
        box = det['box']
        
        if mask is not None:
            mask_filename = f"{base_filename}_mask_{i+1:03d}_score_{score:.3f}.png"
            mask_path = os.path.join(output_dir, mask_filename)
            cv2.imwrite(mask_path, (mask * 255).astype(np.uint8))
    
    # Save metadata
    metadata = {
        'timestamp': timestamp,
        'total_detections': len(detections),
        'detections': []
    }
    
    for i, det in enumerate(detections):
        metadata['detections'].append({
            'id': i + 1,
            'score': float(det['score']),
            'area': int(mask_area(det['mask'])),
            'box': det['box'].tolist(),
            'scale': det.get('scale', 0),
            'conf_thresh': det.get('conf_thresh', 0),
            'source': det.get('source', 'unknown')
        })
    
    metadata_path = os.path.join(output_dir, f"{base_filename}_metadata_{timestamp}.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Saved metadata: {metadata_path}")

def quick_detect_missing_objects(img, model):
    """Main quick detection function for missing objects"""
    print("Starting quick detection for missing items...")
    print("Targeting: media consoles, candle, magazines, vase, pot, clock...")
    
    # Get all detections
    all_detections = quick_detection(img, model)
    
    # Remove duplicates
    print("Removing duplicates...")
    unique_detections = remove_duplicates(all_detections)
    print(f"After duplicate removal: {len(unique_detections)} detections")
    
    # Filter by quality
    print("Filtering by quality...")
    final_detections = filter_by_quality(unique_detections)
    print(f"After quality filtering: {len(final_detections)} detections")
    
    # Sort by score
    final_detections.sort(key=lambda x: x['score'], reverse=True)
    
    return final_detections

def analyze_detection_quality(detections, expected_objects):
    """Analyze detection quality against expected objects"""
    print("\n=== QUICK MISSING DETECTION QUALITY ANALYSIS ===")
    print(f"Expected objects: {len(expected_objects)}")
    print(f"Detected objects: {len(detections)}")
    
    # Analyze score distribution
    scores = [det['score'] for det in detections]
    areas = [mask_area(det['mask']) for det in detections]
    
    print(f"Score range: {min(scores):.3f} - {max(scores):.3f}")
    print(f"Area range: {min(areas)} - {max(areas)} pixels")
    
    # Count high-confidence detections
    high_conf = [d for d in detections if d['score'] > 0.5]
    medium_conf = [d for d in detections if 0.2 <= d['score'] <= 0.5]
    low_conf = [d for d in detections if d['score'] < 0.2]
    
    print(f"High confidence (>0.5): {len(high_conf)}")
    print(f"Medium confidence (0.2-0.5): {len(medium_conf)}")
    print(f"Low confidence (<0.2): {len(low_conf)}")
    
    # Analyze by source
    sources = {}
    for det in detections:
        source = det.get('source', 'unknown')
        if source not in sources:
            sources[source] = 0
        sources[source] += 1
    
    print(f"Detections by source: {sources}")
    
    return {
        'total_detections': len(detections),
        'high_conf_count': len(high_conf),
        'medium_conf_count': len(medium_conf),
        'low_conf_count': len(low_conf),
        'avg_score': np.mean(scores),
        'avg_area': np.mean(areas),
        'sources': sources
    }

# Main execution
if __name__ == "__main__":
    img_path = 'C:/Users/Arnav/Downloads/Room3.jpg'
    img = cv2.imread(img_path)
    
    if img is None:
        raise FileNotFoundError(f"Failed to load image at {img_path}")
    
    print(f"Loaded image with shape: {img.shape}")
    
    # Expected objects in the image
    expected_objects = [
        "chair", "couch", "tv", "dresser", "paintings", "table", "clock", "stool",
        "candle", "magazines", "vase", "pot", "media console", "media console shelf 1", "media console shelf 2"
    ]
    
    # Run quick detection
    detections = quick_detect_missing_objects(img, yolo_model)
    
    # Analyze quality
    quality_metrics = analyze_detection_quality(detections, expected_objects)
    
    # Save results
    timestamp = get_timestamp()
    base_name = os.path.splitext(os.path.basename(img_path))[0]
    
    # Save visualization
    vis_path = os.path.join(OUTPUT_DIR, f"{base_name}_final_detection_{timestamp}.png")
    visualize_detections(img, detections, "Quick Missing Detection", vis_path)
    
    # Save individual masks and metadata
    save_detection_results(detections, MASKS_DIR, base_name)
    
    print(f"\nQuick missing detection complete!")
    print(f"Final detections: {len(detections)}")
    print(f"Results saved to: {OUTPUT_DIR} and {MASKS_DIR}") 