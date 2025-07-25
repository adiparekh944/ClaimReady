import time
import os
import cv2
import numpy as np
import torch
from ultralytics import YOLO
from datetime import datetime
import json
# Removed complex dependencies for faster loading

# ================= CONFIGURATION =================
YOLO_MODEL_PATH = "yolo11n-seg.pt"

# Advanced comprehensive parameters - optimized for speed and flat surface detection
SCALES = [640, 1280]  # Back to 2 scales for speed
CONF_THRESHOLDS = [0.001, 0.005, 0.01, 0.05, 0.1]  # Reduced but still aggressive
IOU_NMS = 0.05  # Very low NMS for maximum coverage
MASK_IOU_THRESH = 0.2  # Reasonable threshold for speed
MIN_MASK_AREA = 10  # Small minimum
MAX_MASK_AREA = 150000  # Large maximum for flat surfaces

# Output directories
OUTPUT_DIR = "fast_comprehensive_outputs"
MASKS_DIR = "fast_comprehensive_masks"
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

def mask_contains(mask1, mask2, threshold=0.6):
    """Check if mask1 contains mask2"""
    if mask1 is None or mask2 is None:
        return False
    intersection = np.logical_and(mask1, mask2)
    if np.sum(mask2) == 0:
        return False
    return np.sum(intersection) / np.sum(mask2) > threshold

def create_fast_enhancements(img):
    """Create fast but effective image enhancements with focus on flat surfaces"""
    enhanced_images = []
    
    # Original image
    enhanced_images.append(("original", img))
    
    # CLAHE - most effective for small object detection
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    lab[:,:,0] = clahe.apply(lab[:,:,0])
    enhanced1 = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    enhanced_images.append(("clahe", enhanced1))
    
    # Edge enhancement - good for flat surfaces and furniture
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 30, 100)  # Adjusted for furniture edges
    edges_col = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    enhanced2 = cv2.addWeighted(img, 0.7, edges_col, 0.3, 0)
    enhanced_images.append(("edge_enhanced", enhanced2))
    
    # High contrast enhancement - helps reveal flat surfaces
    enhanced3 = cv2.convertScaleAbs(img, alpha=2.0, beta=30)
    enhanced_images.append(("high_contrast", enhanced3))
    
    # Gamma correction for better visibility of dark furniture
    gamma = 0.7
    enhanced4 = np.power(img/255.0, gamma) * 255.0
    enhanced4 = enhanced4.astype(np.uint8)
    enhanced_images.append(("gamma_corrected", enhanced4))
    
    return enhanced_images

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
            mask = (mask > 0.01).astype(np.uint8)  # Very low threshold
            
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

def fast_duplicate_removal(detections):
    """
    Fast and Effective Duplicate Removal - optimized for speed and accuracy
    
    This algorithm uses:
    1. Fast IoU calculation for overlap detection
    2. Confidence-based prioritization
    3. Area-based containment logic
    4. Efficient single-pass processing
    """
    if not detections:
        return []

    if len(detections) == 1:
        return detections

    # Sort by confidence (high to low) for greedy selection
    detections.sort(key=lambda x: x['score'], reverse=True)
    
    final_detections = []
    
    for i, det in enumerate(detections):
        should_keep = True
        
        # Check against already accepted detections
        for accepted_det in final_detections:
            # Fast IoU calculation
            iou = mask_iou(det['mask'], accepted_det['mask'])
            
            # High overlap threshold - likely the same object
            if iou > MASK_IOU_THRESH:
                should_keep = False
                break
            
            # Check if current detection is contained within accepted detection
            if mask_contains(accepted_det['mask'], det['mask'], threshold=0.7):
                should_keep = False
                break
            
            # Check if accepted detection is contained within current detection
            if mask_contains(det['mask'], accepted_det['mask'], threshold=0.7):
                # Replace the accepted detection with the current one if it's larger and reasonably confident
                det_area = mask_area(det['mask'])
                accepted_area = mask_area(accepted_det['mask'])
                if det_area > accepted_area * 1.2 and det['score'] > accepted_det['score'] * 0.5:
                    # Find and remove the accepted detection
                    for idx, fd in enumerate(final_detections):
                        if fd is accepted_det:
                            final_detections.pop(idx)
                            break
                    should_keep = True
                    break
                else:
                    should_keep = False
                    break
        
        if should_keep:
            final_detections.append(det)
    
    print(f"Fast duplicate removal: {len(detections)} -> {len(final_detections)} detections")
    return final_detections

def adaptive_quality_filtering(detections, img_shape):
    """Improved adaptive quality filtering optimized for furniture detection"""
    if not detections:
        return detections
    
    # Calculate statistics
    scores = [det['score'] for det in detections]
    areas = [mask_area(det['mask']) for det in detections]
    
    mean_score = np.mean(scores)
    std_score = np.std(scores)
    mean_area = np.mean(areas)
    
    filtered_detections = []
    
    for det in detections:
        score = det['score']
        area = mask_area(det['mask'])
        
        # Keep high-confidence detections
        if score > 0.3:
            filtered_detections.append(det)
            continue
        
        # Keep medium-confidence detections with reasonable area
        if 0.05 <= score <= 0.3 and 50 <= area <= 100000:
            filtered_detections.append(det)
            continue
        
        # Be more permissive for larger objects (likely furniture)
        if area > 5000 and score > 0.01:  # Large flat surfaces
            filtered_detections.append(det)
            continue
        
        # Keep small objects with decent confidence
        if area < 1000 and score > 0.02:
            filtered_detections.append(det)
            continue
        
        # Keep detections that are significantly above average
        if score > mean_score + 0.1 * std_score:
            filtered_detections.append(det)
            continue
        
        # Keep large area detections even with low confidence (for furniture)
        if area > mean_area + 1.0 * std_score and score > 0.005:
            filtered_detections.append(det)
            continue
    
    return filtered_detections

def fast_comprehensive_detection(img, model):
    """Fast comprehensive detection with optimized parameters"""
    all_detections = []
    
    # Create fast enhancements
    enhanced_images = create_fast_enhancements(img)
    print(f"Created {len(enhanced_images)} image enhancements")
    
    for enhancement_name, enhanced_img in enhanced_images:
        print(f"Processing {enhancement_name} enhancement...")
        
        for scale in SCALES:
            for conf_thresh in CONF_THRESHOLDS:
                results = model.predict(
                    enhanced_img, 
                    imgsz=scale, 
                    conf=conf_thresh, 
                    iou=IOU_NMS, 
                    verbose=False,
                    max_det=500
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
                                'source': enhancement_name
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
            'box': [float(x) for x in (det['box'].tolist() if hasattr(det['box'], 'tolist') else det['box'])],
            'scale': det.get('scale', 0),
            'conf_thresh': det.get('conf_thresh', 0),
            'source': det.get('source', 'unknown')
        })
    
    metadata_path = os.path.join(output_dir, f"{base_filename}_metadata_{timestamp}.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Saved metadata: {metadata_path}")

def fast_comprehensive_detect_objects(img, model):
    """Main fast comprehensive detection function"""
    print("Starting fast comprehensive object detection...")
    print("Using optimized parameters for speed and effectiveness...")
    
    # Get all detections with fast parameters
    all_detections = fast_comprehensive_detection(img, model)
    
    # Apply fast duplicate removal
    print("Applying fast duplicate removal...")
    unique_detections = fast_duplicate_removal(all_detections)
    print(f"After duplicate removal: {len(unique_detections)} detections")
    
    # Add furniture detection pass
    furniture_detections = detect_furniture_objects(img, model, unique_detections)
    if furniture_detections:
        unique_detections.extend(furniture_detections)
        print(f"After furniture detection: {len(unique_detections)} detections")
        
        # Run duplicate removal again to handle any overlaps
        unique_detections = fast_duplicate_removal(unique_detections)
        print(f"After final duplicate removal: {len(unique_detections)} detections")
    
    # Apply adaptive quality filtering
    print("Applying adaptive quality filtering...")
    final_detections = adaptive_quality_filtering(unique_detections, img.shape[:2])
    print(f"After quality filtering: {len(final_detections)} detections")
    
    # Sort by score
    final_detections.sort(key=lambda x: x['score'], reverse=True)
    
    return final_detections

def analyze_detection_quality(detections):
    """Analyze detection quality"""
    print("\n=== FAST COMPREHENSIVE DETECTION QUALITY ANALYSIS ===")
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

def detect_furniture_objects(img, model, existing_detections):
    """Focused detection pass for furniture using very low confidence thresholds"""
    print("Running focused furniture detection pass...")
    furniture_detections = []
    
    # Create mask of existing detections to avoid overlap
    img_height, img_width = img.shape[:2]
    existing_mask = np.zeros((img_height, img_width), dtype=bool)
    
    for det in existing_detections:
        if det['mask'] is not None:
            existing_mask = np.logical_or(existing_mask, det['mask'] > 0)
    
    # Enhanced image specifically for furniture
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply bilateral filter to smooth while preserving edges
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # Convert back to BGR
    furniture_enhanced = cv2.cvtColor(filtered, cv2.COLOR_GRAY2BGR)
    
    # Apply gamma correction to brighten dark furniture
    gamma = 0.6
    furniture_enhanced = np.power(furniture_enhanced/255.0, gamma) * 255.0
    furniture_enhanced = furniture_enhanced.astype(np.uint8)
    
    # Run detection with very low confidence
    results = model.predict(
        furniture_enhanced,
        imgsz=640,
        conf=0.001,  # Very low confidence
        iou=0.05,    # Very low NMS
        verbose=False,
        max_det=1000
    )
    
    for result in results:
        masks, scores, boxes = process_masks(result, img.shape[:2])
        
        for mask, score, box in zip(masks, scores, boxes):
            area = mask_area(mask)
            
            # Focus on larger objects that might be furniture
            if area > 2000:  # Reasonable furniture size
                # Check if this area is mostly uncovered by existing detections
                overlap_ratio = np.sum(np.logical_and(mask > 0, existing_mask)) / np.sum(mask > 0)
                
                if overlap_ratio < 0.4:  # Less than 40% overlap with existing
                    # Check if it has furniture-like characteristics
                    box_width = box[2] - box[0]
                    box_height = box[3] - box[1]
                    aspect_ratio = box_width / box_height if box_height > 0 else 1
                    
                    # Furniture is often rectangular with reasonable aspect ratios
                    if 0.3 <= aspect_ratio <= 4.0:
                        detection = {
                            'mask': mask,
                            'score': max(score, 0.01),  # Boost very low scores slightly
                            'box': box,
                            'scale': 640,
                            'conf_thresh': 0.001,
                            'source': 'furniture_detection'
                        }
                        furniture_detections.append(detection)
    
    print(f"Found {len(furniture_detections)} potential furniture objects")
    return furniture_detections

# Main execution
if __name__ == "__main__":
    img_path = 'C:/Users/Arnav/Downloads/IMG_4025.jpg'
    img = cv2.imread(img_path)
    
    if img is None:
        raise FileNotFoundError(f"Failed to load image at {img_path}")
    
    print(f"Loaded image with shape: {img.shape}")
    
    # Expected objects for testing
    expected_objects = [
        "chair", "couch", "tv", "dresser", "paintings", "table", "clock", "stool",
        "candle", "magazines", "vase", "pot", "media console", "media console shelf 1", "media console shelf 2"
    ]
    
    print(f"Expected objects: {len(expected_objects)}")
    for obj in expected_objects:
        print(f"  - {obj}")
    
    # Run fast comprehensive detection
    detections = fast_comprehensive_detect_objects(img, yolo_model)
    
    # Analyze quality
    quality_metrics = analyze_detection_quality(detections)
    
    # Save results
    timestamp = get_timestamp()
    base_name = os.path.splitext(os.path.basename(img_path))[0]
    
    # Save visualization
    vis_path = os.path.join(OUTPUT_DIR, f"{base_name}_fast_comprehensive_{timestamp}.png")
    visualize_detections(img, detections, "Fast Comprehensive Detection", vis_path)
    
    # Save individual masks and metadata
    save_detection_results(detections, MASKS_DIR, base_name)
    
    print(f"\nFast comprehensive detection complete!")
    print(f"Final detections: {len(detections)}")
    print(f"Expected objects: {len(expected_objects)}")
    print(f"Results saved to: {OUTPUT_DIR} and {MASKS_DIR}")
    
    # Check if we detected enough objects
    if len(detections) >= len(expected_objects):
        print(f"✅ SUCCESS: Detected {len(detections)} objects, expected {len(expected_objects)}")
    else:
        print(f"⚠️  NEEDS IMPROVEMENT: Detected {len(detections)} objects, expected {len(expected_objects)}") 