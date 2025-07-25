import os
import time
import cv2
import numpy as np
from ultralytics import YOLO
from collections import defaultdict

# Paths
MODEL_PATH = 'yolo11n-seg.pt'
IMAGE_PATH = 'C:/Users/Arnav/Downloads/IMG_4025.jpg'
OUTPUT_DIR = 'yoloimprvoedoutput'
OUTPUT_IMAGE = os.path.join(OUTPUT_DIR, 'IMG_4025_final_perfect_output.png')

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === FINAL PERFECT DETECTOR PARAMETERS ===
# Ultra-aggressive for chair parts, ultra-sensitive for small objects
SCALES = [640, 1280, 1920, 2560]  # Added 2560 for tiny objects
CONF_THRESH = 0.05     # Very low base confidence
EDGE_CONF_THRESH_CANNY = 0.005    # Ultra-low for edge detection
EDGE_CONF_THRESH_SOBEL = 0.01     # Ultra-low for edge detection
IOU_NMS = 0.98       # Very high to avoid early suppression
MIN_AREA_PX = 25      # Tiny minimum area
MASK_THRESH = 0.01    # Mask threshold

# Problem-specific parameters
CHAIR_DEDUP_AGGRESSION = 0.2  # Ultra-aggressive for chair parts
SMALL_OBJECT_BOOST = 0.3      # High boost for small objects
MONITOR_BOOST = 0.25          # Boost for monitor-like objects
MOUSE_BOOST = 0.35            # Boost for mouse-like objects

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
    edges = cv2.Canny(gray, 30, 100)  # Lower thresholds for more edges
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

def enhance_for_monitor_detection(img):
    """Enhance image specifically for monitor detection"""
    # Brighten and increase contrast
    enhanced = cv2.convertScaleAbs(img, alpha=1.2, beta=10)
    
    # Apply gamma correction
    gamma = 0.8
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    enhanced = cv2.LUT(enhanced, table)
    
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

def classify_detection(box):
    """Classify detection based on size"""
    x1, y1, x2, y2, conf = box
    area = (x2 - x1) * (y2 - y1)
    
    if area < 2000:
        return 'tiny'
    elif area < 5000:
        return 'small'
    elif area < 20000:
        return 'medium'
    else:
        return 'large'

def is_likely_chair_part(box, mask=None):
    """Detect if this is likely a chair part for ultra-aggressive deduplication"""
    x1, y1, x2, y2, conf = box
    area = (x2 - x1) * (y2 - y1)
    aspect_ratio = (x2 - x1) / (y2 - y1 + 1e-6)
    
    # Chair parts are typically large, rectangular, and in lower part of image
    img_height = 4000  # Approximate image height
    center_y = (y1 + y2) / 2
    
    return (area > 8000 and 
            aspect_ratio > 0.4 and aspect_ratio < 2.5 and
            center_y > img_height * 0.3)

def is_likely_monitor(box):
    """Detect if this is likely a monitor"""
    x1, y1, x2, y2, conf = box
    area = (x2 - x1) * (y2 - y1)
    aspect_ratio = (x2 - x1) / (y2 - y1 + 1e-6)
    
    # Monitors are typically rectangular with aspect ratio around 16:9 or 4:3
    return (area > 2000 and area < 50000 and
            aspect_ratio > 1.2 and aspect_ratio < 2.5)

def is_likely_mouse(box):
    """Detect if this is likely a mouse"""
    x1, y1, x2, y2, conf = box
    area = (x2 - x1) * (y2 - y1)
    aspect_ratio = (x2 - x1) / (y2 - y1 + 1e-6)
    
    # Mice are typically small, compact, and have reasonable aspect ratios
    return (area > 100 and area < 3000 and
            aspect_ratio > 0.5 and aspect_ratio < 2.0)

def is_likely_small_object(box):
    """Detect if this is likely a small object that should be preserved"""
    x1, y1, x2, y2, conf = box
    area = (x2 - x1) * (y2 - y1)
    aspect_ratio = (x2 - x1) / (y2 - y1 + 1e-6)
    
    return (area < 5000 and 
            aspect_ratio > 0.2 and aspect_ratio < 4.0 and
            conf > 0.05)

def apply_confidence_boost(box, is_small=False, is_monitor=False, is_mouse=False):
    """Apply confidence boost based on object type"""
    x1, y1, x2, y2, conf = box
    
    boost = 0.0
    if is_small:
        boost += SMALL_OBJECT_BOOST
    if is_monitor:
        boost += MONITOR_BOOST
    if is_mouse:
        boost += MOUSE_BOOST
    
    boosted_conf = min(1.0, conf + boost)
    return [x1, y1, x2, y2, boosted_conf]

def final_deduplication(boxes, masks=None):
    """Final deduplication that addresses all specific problems"""
    if len(boxes) == 0:
        return boxes, masks if masks else []
    
    # Classify and boost detections
    classified_boxes = []
    for i, box in enumerate(boxes):
        mask = masks[i] if masks and i < len(masks) else None
        category = classify_detection(box)
        is_small = is_likely_small_object(box)
        is_chair = is_likely_chair_part(box, mask)
        is_monitor = is_likely_monitor(box)
        is_mouse = is_likely_mouse(box)
        
        boosted_box = apply_confidence_boost(box, is_small, is_monitor, is_mouse)
        classified_boxes.append({
            'box': boosted_box,
            'category': category,
            'is_small': is_small,
            'is_chair': is_chair,
            'is_monitor': is_monitor,
            'is_mouse': is_mouse,
            'mask': mask,
            'original_index': i
        })
    
    # Sort by confidence
    classified_boxes.sort(key=lambda x: x['box'][4], reverse=True)
    
    final_boxes = []
    final_masks = []
    
    for item in classified_boxes:
        should_keep = True
        
        for kept_item in final_boxes:
            # Calculate overlap metrics
            box_iou = _iou(item['box'], kept_item['box'])
            mask_overlap = calculate_mask_overlap(item['mask'], kept_item['mask'])
            
            # Ultra-aggressive deduplication for chair parts
            if item['is_chair'] and kept_item['is_chair']:
                if box_iou > CHAIR_DEDUP_AGGRESSION or mask_overlap > CHAIR_DEDUP_AGGRESSION:
                    should_keep = False
                    break
            
            # Preserve small objects unless very similar
            elif item['is_small'] and kept_item['is_small']:
                if box_iou > 0.8 or mask_overlap > 0.8:  # Very high threshold
                    should_keep = False
                    break
            
            # Preserve monitors unless very similar
            elif item['is_monitor'] and kept_item['is_monitor']:
                if box_iou > 0.6 or mask_overlap > 0.6:
                    should_keep = False
                    break
            
            # Preserve mice unless very similar
            elif item['is_mouse'] and kept_item['is_mouse']:
                if box_iou > 0.7 or mask_overlap > 0.7:
                    should_keep = False
                    break
            
            # Standard deduplication for other objects
            else:
                if box_iou > 0.5 or mask_overlap > 0.5:
                    should_keep = False
                    break
        
        if should_keep:
            final_boxes.append(item)
            if item['mask'] is not None:
                final_masks.append(item['mask'])
    
    return [item['box'] for item in final_boxes], final_masks

def final_multi_scale_detection(img_bgr, model):
    """Final multi-scale detection with all optimizations"""
    print("Running final multi-scale detection...")
    
    all_boxes = []
    all_masks = []
    
    # Stage 1: Standard detection with ultra-low confidence
    print("Stage 1: Standard detection...")
    boxes, masks = run_detection_test(img_bgr, model, "Standard", conf_thresh=CONF_THRESH)
    all_boxes.extend(boxes)
    all_masks.extend(masks)
    
    # Stage 2: Small object focused detection with large scale
    print("Stage 2: Small object detection...")
    enhanced_img = enhance_for_small_objects(img_bgr)
    small_boxes, small_masks = run_detection_test(enhanced_img, model, "Small objects", conf_thresh=0.02, scale_focus=2560)
    all_boxes.extend(small_boxes)
    all_masks.extend(small_masks)
    
    # Stage 3: Monitor-focused detection
    print("Stage 3: Monitor detection...")
    monitor_img = enhance_for_monitor_detection(img_bgr)
    monitor_boxes, monitor_masks = run_detection_test(monitor_img, model, "Monitor detection", conf_thresh=0.03)
    all_boxes.extend(monitor_boxes)
    all_masks.extend(monitor_masks)
    
    # Stage 4: Edge-enhanced detection
    print("Stage 4: Edge-enhanced detection...")
    edge_boxes, edge_masks = run_detection_test(img_bgr, model, "Edge detection", edge_overlay_canny, conf_thresh=EDGE_CONF_THRESH_CANNY)
    all_boxes.extend(edge_boxes)
    all_masks.extend(edge_masks)
    
    sobel_boxes, sobel_masks = run_detection_test(img_bgr, model, "Sobel detection", edge_overlay_sobel, conf_thresh=EDGE_CONF_THRESH_SOBEL)
    all_boxes.extend(sobel_boxes)
    all_masks.extend(sobel_masks)
    
    print(f"Total detections before deduplication: {len(all_boxes)}")
    
    # Apply final deduplication
    if len(all_boxes) > 0:
        final_boxes, final_masks = final_deduplication(all_boxes, all_masks)
        print(f"After final deduplication: {len(final_boxes)}")
        
        return final_boxes, final_masks
    
    return [], []

def draw_final_detections(image, detections, masks=None):
    """Draw detections with final visualization"""
    result_image = image.copy()
    
    for i, detection in enumerate(detections):
        bbox = detection
        confidence = detection[4] if len(detection) > 4 else 0.0
        
        x1, y1, x2, y2 = map(int, bbox[:4])
        area = (x2 - x1) * (y2 - y1)
        
        # Classify for color coding
        category = classify_detection(detection)
        is_small = is_likely_small_object(detection)
        is_chair = is_likely_chair_part(detection)
        is_monitor = is_likely_monitor(detection)
        is_mouse = is_likely_mouse(detection)
        
        # Color based on classification
        if is_chair:
            color = (0, 255, 0)  # Green for chair parts
        elif is_monitor:
            color = (255, 0, 0)  # Blue for monitors
        elif is_mouse:
            color = (0, 0, 255)  # Red for mice
        elif is_small:
            color = (0, 255, 255)  # Cyan for small objects
        elif category == 'medium':
            color = (255, 255, 0)  # Yellow for medium objects
        else:
            color = (255, 0, 255)  # Magenta for large objects
        
        # Draw bounding box
        cv2.rectangle(result_image, (x1, y1), (x2, y2), color, 2)
        
        # Draw mask outline if available
        if masks is not None and i < len(masks):
            mask = masks[i]
            if mask is not None:
                mask_contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for contour in mask_contours:
                    cv2.drawContours(result_image, [contour], -1, color, 1)
        
        # Draw label
        if is_chair:
            label = f"chair_{i}: {confidence:.3f}"
        elif is_monitor:
            label = f"monitor_{i}: {confidence:.3f}"
        elif is_mouse:
            label = f"mouse_{i}: {confidence:.3f}"
        elif is_small:
            label = f"small_{i}: {confidence:.3f}"
        else:
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
    
    print("Running final perfect detection...")
    start_time = time.time()
    
    # Run final detection pipeline
    final_boxes, final_masks = final_multi_scale_detection(img, model)
    
    total_time = time.time() - start_time
    
    print("Drawing results...")
    result_image = draw_final_detections(img, final_boxes, final_masks)
    
    # Save result
    cv2.imwrite(OUTPUT_IMAGE, result_image)
    
    # Print results
    print(f"\n=== FINAL PERFECT DETECTOR RESULTS ===")
    print(f"Total time: {total_time:.2f}s")
    print(f"Final detections: {len(final_boxes)}")
    print(f"Results saved to: {OUTPUT_IMAGE}")
    
    # Analyze results
    category_counts = defaultdict(int)
    chair_count = 0
    small_count = 0
    monitor_count = 0
    mouse_count = 0
    
    for box in final_boxes:
        category = classify_detection(box)
        category_counts[category] += 1
        
        if is_likely_chair_part(box):
            chair_count += 1
        if is_likely_small_object(box):
            small_count += 1
        if is_likely_monitor(box):
            monitor_count += 1
        if is_likely_mouse(box):
            mouse_count += 1
    
    print("\n=== DETECTION BREAKDOWN ===")
    for category, count in category_counts.items():
        print(f"{category}: {count} detections")
    print(f"Chair parts: {chair_count}")
    print(f"Small objects: {small_count}")
    print(f"Monitors: {monitor_count}")
    print(f"Mice: {mouse_count}")
    
    # Print detection details
    print("\n=== DETECTION DETAILS ===")
    for i, detection in enumerate(final_boxes):
        x1, y1, x2, y2, confidence = detection
        area = (x2 - x1) * (y2 - y1)
        category = classify_detection(detection)
        is_chair = is_likely_chair_part(detection)
        is_small = is_likely_small_object(detection)
        is_monitor = is_likely_monitor(detection)
        is_mouse = is_likely_mouse(detection)
        
        if is_chair:
            obj_type = "chair"
        elif is_monitor:
            obj_type = "monitor"
        elif is_mouse:
            obj_type = "mouse"
        elif is_small:
            obj_type = "small"
        else:
            obj_type = category
        
        print(f"{i+1}. {obj_type}: [{x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}] - Conf: {confidence:.3f} - Area: {area:.0f}")

if __name__ == "__main__":
    main() 