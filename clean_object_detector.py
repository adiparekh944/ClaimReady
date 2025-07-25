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
OUTPUT_IMAGE = os.path.join(OUTPUT_DIR, 'IMG_4025_clean_detector_output.png')

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === CLEAN OBJECT DETECTOR PARAMETERS ===
# Focus on meaningful objects, eliminate noise
SCALES = [640, 1280, 1920]  # Reduced scales for speed
CONF_THRESH = 0.15     # Higher base confidence to eliminate noise
EDGE_CONF_THRESH_CANNY = 0.02    # Higher edge confidence
EDGE_CONF_THRESH_SOBEL = 0.03    # Higher edge confidence
IOU_NMS = 0.85       # Lower to avoid early suppression
MIN_AREA_PX = 200     # Higher minimum area to eliminate tiny noise
MASK_THRESH = 0.01    # Mask threshold

# Clean object parameters
MIN_OBJECT_AREA = 500      # Minimum area for meaningful objects
MAX_OBJECT_AREA = 500000   # Maximum area to avoid walls/floors
MIN_ASPECT_RATIO = 0.2     # Minimum aspect ratio
MAX_ASPECT_RATIO = 5.0     # Maximum aspect ratio
MIN_MASK_COVERAGE = 0.3    # Minimum mask coverage for object validity

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
    edges = cv2.Canny(gray, 50, 150)
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

def run_detection_test(img_bgr, model, test_name, transform_func=None, conf_thresh=None):
    """Run detection with optional transformation"""
    if conf_thresh is None:
        conf_thresh = CONF_THRESH
    
    if transform_func:
        test_img = transform_func(img_bgr)
    else:
        test_img = img_bgr
    
    boxes = []
    masks = []
    
    for sz in SCALES:
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

def is_meaningful_object(box, mask=None, img_shape=None):
    """Determine if detection represents a meaningful, complete object"""
    x1, y1, x2, y2, conf = box
    area = (x2 - x1) * (y2 - y1)
    aspect_ratio = (x2 - x1) / (y2 - y1 + 1e-6)
    
    # Basic size and aspect ratio checks
    if area < MIN_OBJECT_AREA or area > MAX_OBJECT_AREA:
        return False
    
    if aspect_ratio < MIN_ASPECT_RATIO or aspect_ratio > MAX_ASPECT_RATIO:
        return False
    
    # Check mask quality if available
    if mask is not None:
        mask_area = np.sum(mask)
        mask_coverage = mask_area / (area + 1e-6)
        
        # Object should have reasonable mask coverage
        if mask_coverage < MIN_MASK_COVERAGE:
            return False
    
    # Check if object is too close to image edges (likely background)
    if img_shape is not None:
        img_h, img_w = img_shape[:2]
        margin = 50  # pixels from edge
        
        if (x1 < margin or y1 < margin or 
            x2 > img_w - margin or y2 > img_h - margin):
            # Only reject if it's a very large object (likely wall/floor)
            if area > img_h * img_w * 0.1:  # More than 10% of image
                return False
    
    return True

def is_likely_background_or_noise(box, mask=None):
    """Detect if this is likely background or noise"""
    x1, y1, x2, y2, conf = box
    area = (x2 - x1) * (y2 - y1)
    aspect_ratio = (x2 - x1) / (y2 - y1 + 1e-6)
    
    # Very large objects are likely walls/floors
    if area > 200000:
        return True
    
    # Very thin objects are likely edges or lines
    if aspect_ratio > 8.0 or aspect_ratio < 0.1:
        return True
    
    # Check mask quality
    if mask is not None:
        mask_area = np.sum(mask)
        mask_coverage = mask_area / (area + 1e-6)
        
        # Very low mask coverage suggests noise
        if mask_coverage < 0.1:
            return True
    
    return False

def clean_deduplication(boxes, masks=None, img_shape=None):
    """Clean deduplication that focuses on meaningful objects"""
    if len(boxes) == 0:
        return boxes, masks if masks else []
    
    # Filter for meaningful objects only
    meaningful_boxes = []
    meaningful_masks = []
    
    for i, box in enumerate(boxes):
        mask = masks[i] if masks and i < len(masks) else None
        
        # Skip if it's background/noise
        if is_likely_background_or_noise(box, mask):
            continue
        
        # Skip if it's not a meaningful object
        if not is_meaningful_object(box, mask, img_shape):
            continue
        
        meaningful_boxes.append(box)
        if mask is not None:
            meaningful_masks.append(mask)
    
    print(f"After noise filtering: {len(meaningful_boxes)} meaningful objects")
    
    if len(meaningful_boxes) == 0:
        return [], []
    
    # Sort by confidence
    sorted_indices = np.argsort([-box[4] for box in meaningful_boxes])
    meaningful_boxes = [meaningful_boxes[i] for i in sorted_indices]
    meaningful_masks = [meaningful_masks[i] for i in sorted_indices] if meaningful_masks else []
    
    # Clean deduplication
    final_boxes = []
    final_masks = []
    
    for i, box in enumerate(meaningful_boxes):
        mask = meaningful_masks[i] if meaningful_masks and i < len(meaningful_masks) else None
        should_keep = True
        
        for kept_box in final_boxes:
            kept_mask = final_masks[len(final_boxes) - 1] if final_masks else None
            
            # Calculate overlap
            box_iou = _iou(box, kept_box)
            mask_overlap = calculate_mask_overlap(mask, kept_mask)
            
            # If significant overlap, keep the one with higher confidence
            if box_iou > 0.5 or mask_overlap > 0.5:
                should_keep = False
                break
        
        if should_keep:
            final_boxes.append(box)
            if mask is not None:
                final_masks.append(mask)
    
    return final_boxes, final_masks

def clean_multi_scale_detection(img_bgr, model):
    """Clean multi-scale detection focused on meaningful objects"""
    print("Running clean multi-scale detection...")
    
    all_boxes = []
    all_masks = []
    
    # Stage 1: Standard detection with higher confidence
    print("Stage 1: Standard detection...")
    boxes, masks = run_detection_test(img_bgr, model, "Standard", conf_thresh=CONF_THRESH)
    all_boxes.extend(boxes)
    all_masks.extend(masks)
    
    # Stage 2: Edge-enhanced detection for object boundaries
    print("Stage 2: Edge-enhanced detection...")
    edge_boxes, edge_masks = run_detection_test(img_bgr, model, "Edge detection", edge_overlay_canny, conf_thresh=EDGE_CONF_THRESH_CANNY)
    all_boxes.extend(edge_boxes)
    all_masks.extend(edge_masks)
    
    sobel_boxes, sobel_masks = run_detection_test(img_bgr, model, "Sobel detection", edge_overlay_sobel, conf_thresh=EDGE_CONF_THRESH_SOBEL)
    all_boxes.extend(sobel_boxes)
    all_masks.extend(sobel_masks)
    
    print(f"Total detections before cleaning: {len(all_boxes)}")
    
    # Apply clean deduplication
    if len(all_boxes) > 0:
        final_boxes, final_masks = clean_deduplication(all_boxes, all_masks, img_bgr.shape)
        print(f"After clean deduplication: {len(final_boxes)}")
        
        return final_boxes, final_masks
    
    return [], []

def draw_clean_detections(image, detections, masks=None):
    """Draw clean detections with meaningful visualization"""
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
        
        # Draw label with area info
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
    
    print("Running clean object detection...")
    start_time = time.time()
    
    # Run clean detection pipeline
    final_boxes, final_masks = clean_multi_scale_detection(img, model)
    
    total_time = time.time() - start_time
    
    print("Drawing results...")
    result_image = draw_clean_detections(img, final_boxes, final_masks)
    
    # Save result
    cv2.imwrite(OUTPUT_IMAGE, result_image)
    
    # Print results
    print(f"\n=== CLEAN OBJECT DETECTOR RESULTS ===")
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