import os
import time
import cv2
import numpy as np
from ultralytics import YOLO
from collections import defaultdict
import math

# Paths
MODEL_PATH = 'yolo11n-seg.pt'
IMAGE_PATH = 'C:/Users/Arnav/Downloads/IMG_4025.jpg'
OUTPUT_DIR = 'yoloimprvoedoutput'
OUTPUT_IMAGE = os.path.join(OUTPUT_DIR, 'IMG_4025_perfect_detector_output.png')

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === PERFECT DETECTOR PARAMETERS ===
# Multi-scale detection for different object sizes
SCALES = [640, 1280, 1920, 2560]  # Added larger scale for small objects
CONF_THRESH = 0.1     # Lower base confidence for better coverage
EDGE_CONF_THRESH_CANNY = 0.005    # Very low for edge detection
EDGE_CONF_THRESH_SOBEL = 0.01     # Very low for edge detection
IOU_NMS = 0.95       # Very high to avoid early suppression
MIN_AREA_PX = 32      # Much smaller minimum area for tiny objects
EDGE_THRESH = 10      # Lower edge threshold
NMS_IOU = 0.05        # Very strict final NMS
MASK_THRESH = 0.01    # Mask threshold

# Object-specific parameters
OBJECT_CATEGORIES = {
    'large_furniture': {
        'classes': ['chair', 'couch', 'dining table', 'tv'],
        'min_area': 5000,
        'max_area': 200000,
        'confidence_boost': 0.1,
        'dedup_aggression': 'high'
    },
    'medium_objects': {
        'classes': ['monitor', 'laptop', 'speaker', 'vase', 'book'],
        'min_area': 500,
        'max_area': 20000,
        'confidence_boost': 0.05,
        'dedup_aggression': 'medium'
    },
    'small_objects': {
        'classes': ['mouse', 'keyboard', 'cup', 'phone', 'remote'],
        'min_area': 32,
        'max_area': 2000,
        'confidence_boost': 0.15,
        'dedup_aggression': 'low'
    }
}

def _iou(a, b):
    """Calculate IoU between two boxes"""
    ax1, ay1, ax2, ay2, _ = a
    bx1, by1, bx2, by2, _ = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2-ix1+1), max(0, iy2-iy1+1)
    inter = iw * ih
    ua = (ax2-ax1+1)*(ay2-ay1+1)
    ub = (bx2-bx1+1)*(by2-by1+1)
    return inter / float(ua + ub - inter + 1e-6)

def calculate_mask_overlap(mask1, mask2):
    """Calculate overlap between two masks"""
    if mask1 is None or mask2 is None:
        return 0.0
    
    if mask1.shape != mask2.shape:
        mask1 = cv2.resize(mask1.astype(np.uint8), (mask2.shape[1], mask2.shape[0]), interpolation=cv2.INTER_NEAREST)
    
    intersection = np.logical_and(mask1 > 0, mask2 > 0).sum()
    union = np.logical_or(mask1 > 0, mask2 > 0).sum()
    
    if union == 0:
        return 0.0
    
    return intersection / union

def edge_overlay_canny(img, alpha=0.5):
    """Canny edge detection overlay"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)  # Lower thresholds for more edges
    edges_col = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    overlay = cv2.addWeighted(img, 1 - alpha, edges_col, alpha, 0)
    return overlay

def edge_overlay_sobel(img):
    """Sobel edge detection"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    sobel = cv2.magnitude(sobelx, sobely)
    sobel = np.uint8(np.clip(sobel, 0, 255))
    sobel_3ch = cv2.cvtColor(sobel, cv2.COLOR_GRAY2BGR)
    return sobel_3ch

def enhance_for_small_objects(img):
    """Enhance image specifically for small object detection"""
    # Increase contrast
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    lab[:,:,0] = clahe.apply(lab[:,:,0])
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
    # Sharpen
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    enhanced = cv2.filter2D(enhanced, -1, kernel)
    
    return enhanced

def run_detection_test(img_bgr, model, test_name, transform_func=None, conf_thresh=None, scale_focus=None):
    """Run detection with optional transformation and scale focus"""
    if conf_thresh is None:
        conf_thresh = CONF_THRESH
    
    if transform_func:
        test_img = transform_func(img_bgr)
    else:
        test_img = img_bgr
    
    boxes = []
    masks = []
    
    # Use specific scales if provided, otherwise use all scales
    scales_to_use = [scale_focus] if scale_focus else SCALES
    
    for sz in scales_to_use:
        res = model.predict(test_img, imgsz=sz, conf=conf_thresh, iou=IOU_NMS,
                            agnostic_nms=True, verbose=False)
        for b in res[0].boxes:
            x1, y1, x2, y2 = b.xyxy[0].cpu().numpy()
            score = float(b.conf[0])
            
            # Map coordinates back if transformation was applied
            if transform_func:
                if "flip" in test_name:
                    H, W = img_bgr.shape[:2]
                    x1, x2 = W - x2, W - x1
                elif "rotate" in test_name:
                    H, W = img_bgr.shape[:2]
                    old_x1, old_y1, old_x2, old_y2 = x1, y1, x2, y2
                    x1, y1 = old_y1, W - old_x2
                    x2, y2 = old_y2, W - old_x1
            
            boxes.append([x1, y1, x2, y2, score])
        
        # Collect masks
        if hasattr(res[0], "masks") and res[0].masks is not None and res[0].masks.data is not None:
            m = res[0].masks.data.cpu().numpy()
            m = (m > MASK_THRESH).astype(np.uint8)
            masks.extend(m)
    
    return boxes, masks

def classify_detection(box, mask=None):
    """Classify detection into object category based on size and features"""
    x1, y1, x2, y2, conf = box
    w, h = x2 - x1, y2 - y1
    area = w * h
    aspect_ratio = w / (h + 1e-6)
    
    # Calculate mask area if available
    mask_area = np.sum(mask) if mask is not None else 0
    mask_ratio = mask_area / (area + 1e-6) if area > 0 else 0
    
    # Classification logic
    if area < 2000:
        return 'small_objects'
    elif area < 20000:
        return 'medium_objects'
    else:
        return 'large_furniture'

def apply_confidence_boost(box, category):
    """Apply confidence boost based on object category"""
    x1, y1, x2, y2, conf = box
    boost = OBJECT_CATEGORIES[category]['confidence_boost']
    boosted_conf = min(1.0, conf + boost)
    return [x1, y1, x2, y2, boosted_conf]

def smart_deduplication(boxes, masks=None):
    """Advanced deduplication that considers object categories"""
    if len(boxes) == 0:
        return boxes, masks if masks else []
    
    # Classify each detection
    classified_boxes = []
    for i, box in enumerate(boxes):
        mask = masks[i] if masks and i < len(masks) else None
        category = classify_detection(box, mask)
        boosted_box = apply_confidence_boost(box, category)
        classified_boxes.append({
            'box': boosted_box,
            'category': category,
            'mask': mask,
            'original_index': i
        })
    
    # Group by category for category-specific deduplication
    category_groups = defaultdict(list)
    for item in classified_boxes:
        category_groups[item['category']].append(item)
    
    final_boxes = []
    final_masks = []
    
    for category, items in category_groups.items():
        print(f"Deduplicating {category}: {len(items)} items")
        
        # Sort by confidence
        items.sort(key=lambda x: x['box'][4], reverse=True)
        
        kept_items = []
        for item in items:
            should_keep = True
            
            for kept_item in kept_items:
                # Get deduplication parameters for this category
                aggression = OBJECT_CATEGORIES[category]['dedup_aggression']
                
                # Calculate overlap metrics
                box_iou = _iou(item['box'], kept_item['box'])
                mask_overlap = calculate_mask_overlap(item['mask'], kept_item['mask'])
                
                # Category-specific thresholds
                if aggression == 'high':
                    iou_thresh = 0.3
                    mask_thresh = 0.2
                elif aggression == 'medium':
                    iou_thresh = 0.5
                    mask_thresh = 0.4
                else:  # low
                    iou_thresh = 0.7
                    mask_thresh = 0.6
                
                # Check if this is a duplicate
                if box_iou > iou_thresh or mask_overlap > mask_thresh:
                    should_keep = False
                    break
            
            if should_keep:
                kept_items.append(item)
        
        # Add kept items to final results
        for item in kept_items:
            final_boxes.append(item['box'])
            if item['mask'] is not None:
                final_masks.append(item['mask'])
    
    return final_boxes, final_masks

def perfect_multi_scale_detection(img_bgr, model):
    """Perfect multi-scale detection with object-specific strategies"""
    print("Running perfect multi-scale detection...")
    
    all_boxes = []
    all_masks = []
    
    # Stage 1: Standard multi-scale detection
    print("Stage 1: Standard multi-scale detection...")
    for scale in SCALES:
        boxes, masks = run_detection_test(img_bgr, model, f"Scale {scale}", conf_thresh=CONF_THRESH, scale_focus=scale)
        all_boxes.extend(boxes)
        all_masks.extend(masks)
    
    # Stage 2: Small object focused detection
    print("Stage 2: Small object focused detection...")
    enhanced_img = enhance_for_small_objects(img_bgr)
    small_boxes, small_masks = run_detection_test(enhanced_img, model, "Small objects", conf_thresh=0.05, scale_focus=2560)
    all_boxes.extend(small_boxes)
    all_masks.extend(small_masks)
    
    # Stage 3: Edge-enhanced detection for complex objects
    print("Stage 3: Edge-enhanced detection...")
    edge_boxes, edge_masks = run_detection_test(img_bgr, model, "Edge detection", edge_overlay_canny, conf_thresh=EDGE_CONF_THRESH_CANNY)
    all_boxes.extend(edge_boxes)
    all_masks.extend(edge_masks)
    
    sobel_boxes, sobel_masks = run_detection_test(img_bgr, model, "Sobel detection", edge_overlay_sobel, conf_thresh=EDGE_CONF_THRESH_SOBEL)
    all_boxes.extend(sobel_boxes)
    all_masks.extend(sobel_masks)
    
    print(f"Total detections before deduplication: {len(all_boxes)}")
    
    # Apply perfect deduplication
    if len(all_boxes) > 0:
        final_boxes, final_masks = smart_deduplication(all_boxes, all_masks)
        print(f"After smart deduplication: {len(final_boxes)}")
        
        return final_boxes, final_masks
    
    return [], []

def draw_perfect_detections(image, detections, masks=None):
    """Draw detections with perfect visualization"""
    result_image = image.copy()
    
    for i, detection in enumerate(detections):
        bbox = detection
        confidence = detection[4] if len(detection) > 4 else 0.0
        
        x1, y1, x2, y2 = map(int, bbox[:4])
        area = (x2 - x1) * (y2 - y1)
        
        # Classify for color coding
        category = classify_detection(detection, masks[i] if masks and i < len(masks) else None)
        
        # Color based on category and confidence
        if category == 'large_furniture':
            if confidence > 0.6:
                color = (0, 255, 0)  # Green for high confidence furniture
            else:
                color = (0, 200, 0)  # Darker green for lower confidence
        elif category == 'medium_objects':
            if confidence > 0.5:
                color = (255, 255, 0)  # Yellow for medium objects
            else:
                color = (200, 200, 0)  # Darker yellow
        else:  # small_objects
            if confidence > 0.4:
                color = (0, 255, 255)  # Cyan for small objects
            else:
                color = (0, 200, 200)  # Darker cyan
        
        # Draw bounding box
        cv2.rectangle(result_image, (x1, y1), (x2, y2), color, 2)
        
        # Draw mask outline if available
        if masks is not None and i < len(masks):
            mask = masks[i]
            if mask is not None:
                mask_contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for contour in mask_contours:
                    cv2.drawContours(result_image, [contour], -1, color, 1)
        
        # Draw label with category and confidence
        label = f"{category[:3]}_{i}: {confidence:.3f}"
        cv2.putText(result_image, label, (x1, y1-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    return result_image

def main():
    print("Loading YOLO model...")
    model = YOLO(MODEL_PATH)
    
    print("Reading image...")
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        raise FileNotFoundError(f'Could not load image: {IMAGE_PATH}')
    
    print("Running perfect object detection...")
    start_time = time.time()
    
    # Run perfect detection pipeline
    final_boxes, final_masks = perfect_multi_scale_detection(img, model)
    
    total_time = time.time() - start_time
    
    print("Drawing results...")
    result_image = draw_perfect_detections(img, final_boxes, final_masks)
    
    # Save result
    cv2.imwrite(OUTPUT_IMAGE, result_image)
    
    # Print results
    print(f"\n=== PERFECT DETECTOR RESULTS ===")
    print(f"Total time: {total_time:.2f}s")
    print(f"Final detections: {len(final_boxes)}")
    print(f"Results saved to: {OUTPUT_IMAGE}")
    
    # Analyze results by category
    category_counts = defaultdict(int)
    for box in final_boxes:
        category = classify_detection(box)
        category_counts[category] += 1
    
    print("\n=== DETECTION BREAKDOWN ===")
    for category, count in category_counts.items():
        print(f"{category}: {count} detections")
    
    # Print detection details
    print("\n=== DETECTION DETAILS ===")
    for i, detection in enumerate(final_boxes):
        x1, y1, x2, y2, confidence = detection
        area = (x2 - x1) * (y2 - y1)
        category = classify_detection(detection)
        mask_area = np.sum(final_masks[i]) if final_masks and i < len(final_masks) else 0
        print(f"{i+1}. {category}: [{x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}] - Conf: {confidence:.3f} - Area: {area:.0f}")

if __name__ == "__main__":
    main() 