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

# Refined detection parameters
SCALES = [640, 1280, 1920]  # Focus on most effective scales
CONF_THRESHOLDS = [0.01, 0.05, 0.1, 0.15, 0.2]  # Lower thresholds to catch more objects
IOU_NMS = 0.6  # Lower NMS for more detections
MASK_IOU_THRESH = 0.4  # Lower threshold for duplicate removal
MIN_MASK_AREA = 50  # Smaller minimum for tiny objects like media consoles
MAX_MASK_AREA = 60000  # Higher maximum to catch large furniture like dressers

# Output directories
OUTPUT_DIR = "refined_detection_outputs"
MASKS_DIR = "refined_detected_masks"
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

def mask_contains(mask1, mask2, threshold=0.7):
    """Check if mask1 contains mask2 (for detecting partial overlaps)"""
    if mask1 is None or mask2 is None:
        return False
    intersection = np.logical_and(mask1, mask2)
    if np.sum(mask2) == 0:
        return False
    return np.sum(intersection) / np.sum(mask2) > threshold

def enhance_image_for_detection(img):
    """Apply image enhancements to improve detection"""
    enhanced = img.copy()
    
    # Contrast enhancement
    lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    l = clahe.apply(l)
    enhanced = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    
    return enhanced

def create_edge_enhanced_image(img):
    """Create edge-enhanced version for better small object detection"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 30, 100)  # Lower thresholds for more edges
    edges_col = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    return cv2.addWeighted(img, 0.8, edges_col, 0.2, 0)

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
            mask = (mask > 0.5).astype(np.uint8)  # Binary threshold
            
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

def is_duplicate_mask(mask1, mask2, threshold=0.5):
    """Check if two masks are duplicates with lower threshold"""
    return mask_iou(mask1, mask2) > threshold

def remove_duplicates_and_partials(detections):
    """Remove duplicates and partial overlaps (like couch parts)"""
    if not detections:
        return []
    
    # Sort by score in descending order
    detections.sort(key=lambda x: x['score'], reverse=True)
    
    unique_detections = []
    for det in detections:
        should_add = True
        
        # Check against all existing unique detections
        for i, unique_det in enumerate(unique_detections):
            # Check for duplicates
            if is_duplicate_mask(det['mask'], unique_det['mask']):
                should_add = False
                break
            
            # Check for partial overlaps (one contains the other)
            if mask_contains(det['mask'], unique_det['mask']) or mask_contains(unique_det['mask'], det['mask']):
                # Keep the larger mask (more complete detection)
                if mask_area(det['mask']) > mask_area(unique_det['mask']):
                    # Replace the smaller one with this one
                    unique_detections[i] = det
                should_add = False
                break
        
        if should_add:
            unique_detections.append(det)
    
    return unique_detections

def merge_overlapping_masks(detections, iou_threshold=0.4):
    """Merge masks that have significant overlap"""
    if not detections:
        return detections
    
    merged = []
    used = [False] * len(detections)
    
    for i, det in enumerate(detections):
        if used[i]:
            continue
            
        group = [det]
        used[i] = True
        
        for j in range(i+1, len(detections)):
            if used[j]:
                continue
                
            mask_iou_val = mask_iou(det['mask'], detections[j]['mask'])
            if mask_iou_val > iou_threshold:
                group.append(detections[j])
                used[j] = True
        
        # Merge masks by taking union
        merged_mask = group[0]['mask'].copy()
        max_score = max(g['score'] for g in group)
        
        for g in group[1:]:
            merged_mask = np.logical_or(merged_mask, g['mask']).astype(np.uint8)
        
        merged_detection = {
            'mask': merged_mask,
            'score': max_score,
            'box': group[0]['box']  # Keep first box
        }
        merged.append(merged_detection)
    
    return merged

def filter_by_quality(detections, min_score=0.05, min_area=100):
    """Filter detections by quality metrics"""
    filtered = []
    for det in detections:
        score = det['score']
        area = mask_area(det['mask'])
        
        # Keep high-confidence detections or medium-confidence with reasonable area
        if score >= min_score or (score >= 0.01 and area >= min_area):
            filtered.append(det)
    
    return filtered

def comprehensive_detection(img, model):
    """Run comprehensive detection with multiple scales, confidence thresholds, and image enhancements"""
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
                max_det=150  # Increase max detections
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
    
    # Enhanced image detection
    enhanced_img = enhance_image_for_detection(img)
    for scale in SCALES:
        for conf_thresh in CONF_THRESHOLDS:
            results = model.predict(
                enhanced_img, 
                imgsz=scale, 
                conf=conf_thresh, 
                iou=IOU_NMS, 
                verbose=False,
                max_det=150
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
    
    # Edge-enhanced image detection for small objects
    edge_img = create_edge_enhanced_image(img)
    for scale in SCALES:
        for conf_thresh in CONF_THRESHOLDS:
            results = model.predict(
                edge_img, 
                imgsz=scale, 
                conf=conf_thresh, 
                iou=IOU_NMS, 
                verbose=False,
                max_det=150
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
                        'source': 'edge_enhanced'
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
            cv2.putText(vis, f'{score:.2f}', (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.putText(vis, f'{score:.2f}', (x1, y1-10), 
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

def refined_detect_objects(img, model):
    """Main refined detection function with better duplicate handling"""
    print("Starting refined object detection...")
    
    # Get all detections
    all_detections = comprehensive_detection(img, model)
    
    # Remove duplicates and partial overlaps
    print("Removing duplicates and partial overlaps...")
    unique_detections = remove_duplicates_and_partials(all_detections)
    print(f"After duplicate/partial removal: {len(unique_detections)} detections")
    
    # Merge overlapping masks
    print("Merging overlapping masks...")
    merged_detections = merge_overlapping_masks(unique_detections)
    print(f"After merging: {len(merged_detections)} detections")
    
    # Filter by quality
    print("Filtering by quality...")
    final_detections = filter_by_quality(merged_detections)
    print(f"After quality filtering: {len(final_detections)} detections")
    
    # Sort by score
    final_detections.sort(key=lambda x: x['score'], reverse=True)
    
    return final_detections

def analyze_detection_quality(detections, expected_objects):
    """Analyze detection quality against expected objects"""
    print("\n=== REFINED DETECTION QUALITY ANALYSIS ===")
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
    
    # Run refined detection
    detections = refined_detect_objects(img, yolo_model)
    
    # Analyze quality
    quality_metrics = analyze_detection_quality(detections, expected_objects)
    
    # Save results
    timestamp = get_timestamp()
    base_name = os.path.splitext(os.path.basename(img_path))[0]
    
    # Save visualization
    vis_path = os.path.join(OUTPUT_DIR, f"{base_name}_final_detection_{timestamp}.png")
    visualize_detections(img, detections, "Refined Detection", vis_path)
    
    # Save individual masks and metadata
    save_detection_results(detections, MASKS_DIR, base_name)
    
    print(f"\nRefined detection complete!")
    print(f"Final detections: {len(detections)}")
    print(f"Results saved to: {OUTPUT_DIR} and {MASKS_DIR}") 