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
OUTPUT_IMAGE = os.path.join(OUTPUT_DIR, 'IMG_4025_fast_dynamic_output.png')

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === FAST DYNAMIC DETECTOR PARAMETERS ===
# Minimal hardcoded values, everything else computed dynamically
SCALES = [640, 1280]  # Reduced scales for speed
IOU_NMS = 0.85
MASK_THRESH = 0.01

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

def run_single_detection(img_bgr, model, conf_thresh=0.1):
    """Single fast detection pass"""
    boxes = []
    masks = []
    
    for sz in SCALES:
        res = model.predict(img_bgr, imgsz=sz, conf=conf_thresh, iou=IOU_NMS,
                            agnostic_nms=True, verbose=False)
        for b in res[0].boxes:
            x1, y1, x2, y2 = b.xyxy[0].cpu().numpy()
            score = float(b.conf[0])
            boxes.append([x1, y1, x2, y2, score])
        
        # Collect masks
        if hasattr(res[0], "masks") and res[0].masks is not None and res[0].masks.data is not None:
            m = res[0].masks.data.cpu().numpy()
            m = (m > MASK_THRESH).astype(np.uint8)
            masks.extend(m)
    
    return boxes, masks

def compute_adaptive_thresholds(boxes, masks=None, img_shape=None):
    """Compute adaptive thresholds from single detection pass"""
    if len(boxes) == 0:
        return {}
    
    # Extract features
    areas = []
    confidences = []
    aspect_ratios = []
    
    for box in boxes:
        x1, y1, x2, y2, conf = box
        area = (x2 - x1) * (y2 - y1)
        aspect_ratio = (x2 - x1) / (y2 - y1 + 1e-6)
        
        areas.append(area)
        confidences.append(conf)
        aspect_ratios.append(aspect_ratio)
    
    areas = np.array(areas)
    confidences = np.array(confidences)
    aspect_ratios = np.array(aspect_ratios)
    
    # Adaptive thresholds based on data distribution
    
    # 1. Confidence: Use median to separate good from noise
    conf_threshold = np.median(confidences) * 0.8
    
    # 2. Area: Use percentiles to eliminate extremes
    area_q25, area_q75 = np.percentile(areas, [25, 75])
    min_area = max(area_q25 * 0.5, 100)  # At least 100px
    max_area = min(area_q75 * 2.0, areas.max() * 0.9)  # Not too large
    
    # 3. Aspect ratio: Use percentiles
    aspect_q25, aspect_q75 = np.percentile(aspect_ratios, [25, 75])
    min_aspect = max(aspect_q25 * 0.5, 0.1)
    max_aspect = min(aspect_q75 * 2.0, 10.0)
    
    # 4. IoU threshold: Based on object count
    if len(boxes) > 50:  # Many objects
        iou_threshold = 0.6
    elif len(boxes) > 20:  # Medium objects
        iou_threshold = 0.5
    else:  # Few objects
        iou_threshold = 0.4
    
    return {
        'conf_threshold': conf_threshold,
        'min_area': min_area,
        'max_area': max_area,
        'min_aspect_ratio': min_aspect,
        'max_aspect_ratio': max_aspect,
        'iou_threshold': iou_threshold
    }

def filter_meaningful_objects(boxes, masks=None, thresholds=None):
    """Filter for meaningful objects using adaptive thresholds"""
    if not thresholds or len(boxes) == 0:
        return boxes, masks if masks else []
    
    meaningful_boxes = []
    meaningful_masks = []
    
    for i, box in enumerate(boxes):
        x1, y1, x2, y2, conf = box
        area = (x2 - x1) * (y2 - y1)
        aspect_ratio = (x2 - x1) / (y2 - y1 + 1e-6)
        
        # Apply adaptive filters
        if (conf >= thresholds['conf_threshold'] and
            area >= thresholds['min_area'] and area <= thresholds['max_area'] and
            aspect_ratio >= thresholds['min_aspect_ratio'] and aspect_ratio <= thresholds['max_aspect_ratio']):
            
            meaningful_boxes.append(box)
            if masks and i < len(masks):
                meaningful_masks.append(masks[i])
    
    return meaningful_boxes, meaningful_masks

def fast_deduplication(boxes, masks=None, thresholds=None):
    """Fast deduplication using adaptive thresholds"""
    if len(boxes) == 0:
        return boxes, masks if masks else []
    
    # Sort by confidence
    sorted_indices = np.argsort([-box[4] for box in boxes])
    sorted_boxes = [boxes[i] for i in sorted_indices]
    sorted_masks = [masks[i] for i in sorted_indices] if masks else []
    
    final_boxes = []
    final_masks = []
    
    for i, box in enumerate(sorted_boxes):
        mask = sorted_masks[i] if sorted_masks and i < len(sorted_masks) else None
        should_keep = True
        
        for kept_box in final_boxes:
            kept_mask = final_masks[len(final_boxes) - 1] if final_masks else None
            
            # Calculate overlap
            box_iou = _iou(box, kept_box)
            mask_overlap = calculate_mask_overlap(mask, kept_mask)
            
            # Use adaptive IoU threshold
            iou_thresh = thresholds['iou_threshold'] if thresholds else 0.5
            if box_iou > iou_thresh or mask_overlap > iou_thresh:
                should_keep = False
                break
        
        if should_keep:
            final_boxes.append(box)
            if mask is not None:
                final_masks.append(mask)
    
    return final_boxes, final_masks

def fast_dynamic_detection(img_bgr, model):
    """Fast dynamic detection with single pass and adaptive thresholds"""
    print("Running fast dynamic detection...")
    
    # Single detection pass with low confidence to get all candidates
    print("Stage 1: Single detection pass...")
    boxes, masks = run_single_detection(img_bgr, model, conf_thresh=0.05)
    print(f"Initial detections: {len(boxes)}")
    
    if len(boxes) == 0:
        return [], []
    
    # Compute adaptive thresholds
    print("Stage 2: Computing adaptive thresholds...")
    thresholds = compute_adaptive_thresholds(boxes, masks, img_bgr.shape)
    print(f"Adaptive thresholds: {thresholds}")
    
    # Filter meaningful objects
    print("Stage 3: Filtering meaningful objects...")
    meaningful_boxes, meaningful_masks = filter_meaningful_objects(boxes, masks, thresholds)
    print(f"Meaningful objects: {len(meaningful_boxes)}")
    
    # Fast deduplication
    print("Stage 4: Fast deduplication...")
    final_boxes, final_masks = fast_deduplication(meaningful_boxes, meaningful_masks, thresholds)
    print(f"Final objects: {len(final_boxes)}")
    
    return final_boxes, final_masks

def draw_fast_detections(image, detections, masks=None):
    """Draw fast detections"""
    result_image = image.copy()
    
    for i, detection in enumerate(detections):
        bbox = detection
        confidence = detection[4] if len(detection) > 4 else 0.0
        
        x1, y1, x2, y2 = map(int, bbox[:4])
        area = (x2 - x1) * (y2 - y1)
        
        # Color based on confidence
        if confidence > 0.6:
            color = (0, 255, 0)  # Green for high confidence
        elif confidence > 0.3:
            color = (255, 255, 0)  # Yellow for medium confidence
        else:
            color = (0, 255, 255)  # Cyan for low confidence
        
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
        label = f"obj_{i}: {confidence:.3f} ({area:.0f})"
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
    
    print("Running fast dynamic detection...")
    start_time = time.time()
    
    # Run fast dynamic detection pipeline
    final_boxes, final_masks = fast_dynamic_detection(img, model)
    
    total_time = time.time() - start_time
    
    print("Drawing results...")
    result_image = draw_fast_detections(img, final_boxes, final_masks)
    
    # Save result
    cv2.imwrite(OUTPUT_IMAGE, result_image)
    
    # Print results
    print(f"\n=== FAST DYNAMIC DETECTOR RESULTS ===")
    print(f"Total time: {total_time:.2f}s")
    print(f"Final detections: {len(final_boxes)}")
    print(f"Results saved to: {OUTPUT_IMAGE}")
    
    # Analyze results
    high_conf = 0
    medium_conf = 0
    low_conf = 0
    
    for box in final_boxes:
        conf = box[4]
        if conf > 0.6:
            high_conf += 1
        elif conf > 0.3:
            medium_conf += 1
        else:
            low_conf += 1
    
    print("\n=== DETECTION BREAKDOWN ===")
    print(f"High confidence (>0.6): {high_conf}")
    print(f"Medium confidence (0.3-0.6): {medium_conf}")
    print(f"Low confidence (<0.3): {low_conf}")
    
    # Print detection details
    print("\n=== DETECTION DETAILS ===")
    for i, detection in enumerate(final_boxes):
        x1, y1, x2, y2, confidence = detection
        area = (x2 - x1) * (y2 - y1)
        print(f"{i+1}. [{x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}] - Conf: {confidence:.3f} - Area: {area:.0f}")

if __name__ == "__main__":
    main() 