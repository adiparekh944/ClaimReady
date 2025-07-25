import os
import time
import cv2
import numpy as np
from ultralytics import YOLO

# Paths
MODEL_PATH = 'yolo11n-seg.pt'
IMAGE_PATH = 'C:/Users/Arnav/Downloads/IMG_4025.jpg'
OUTPUT_DIR = 'yoloimprvoedoutput'
OUTPUT_IMAGE = os.path.join(OUTPUT_DIR, 'IMG_4025_balanced_output.png')

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === BALANCED PARAMETERS ===
SCALES = (640, 1280, 1920)  # Restore full scale set for better detection
CONF_THRESH = 0.15     # Lower confidence to catch more objects
EDGE_CONF_THRESH_CANNY = 0.01  # Lower threshold for edge detection
EDGE_CONF_THRESH_SOBEL = 0.05  # Restore Sobel for better coverage
IOU_NMS = 0.8      # Balanced initial NMS
NMS_IOU = 0.4      # Less aggressive final NMS
MASK_THRESH = 0.01

# Balanced deduplication thresholds
MASK_IOU_THRESH = 0.5  # Higher = less aggressive
FEATURE_THRESH = 0.8   # Higher = less aggressive
DISTANCE_THRESH = 50   # Larger = less aggressive
MIN_AREA = 500       # Lower minimum area to catch smaller objects

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

def edge_overlay_canny(img, alpha=0.5):
    """Canny edge detection overlay"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
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
    """Run a single detection test"""
    if conf_thresh is None:
        conf_thresh = CONF_THRESH
    
    # Apply transformation if provided
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
            
            # Filter out very tiny detections but keep small objects
            area = (x2 - x1) * (y2 - y1)
            if area < MIN_AREA:
                continue
                
            boxes.append([x1, y1, x2, y2, score])
        
        # Collect masks (if available)
        if hasattr(res[0], "masks") and res[0].masks is not None and res[0].masks.data is not None:
            m = res[0].masks.data.cpu().numpy()
            m = (m > MASK_THRESH).astype(np.uint8)
            masks.extend(m)
    
    return boxes, masks

def calculate_mask_overlap(mask1, mask2):
    """Calculate overlap between two masks"""
    if mask1 is None or mask2 is None:
        return 0.0
    
    # Ensure masks are same size
    if mask1.shape != mask2.shape:
        mask1 = cv2.resize(mask1.astype(np.uint8), (mask2.shape[1], mask2.shape[0]), interpolation=cv2.INTER_NEAREST)
    
    intersection = np.logical_and(mask1 > 0, mask2 > 0).sum()
    union = np.logical_or(mask1 > 0, mask2 > 0).sum()
    
    if union == 0:
        return 0.0
    
    return intersection / union

def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    a_norm = a / (np.linalg.norm(a) + 1e-8)
    b_norm = b / (np.linalg.norm(b) + 1e-8)
    return np.dot(a_norm, b_norm)

def extract_simple_features(box, mask=None):
    """Extract simple features from box and mask"""
    x1, y1, x2, y2, conf = box
    w, h = x2 - x1, y2 - y1
    area = w * h
    aspect_ratio = w / (h + 1e-6)
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    
    # Basic features
    features = [conf, area, aspect_ratio, center_x, center_y, w, h]
    
    # Add mask features if available
    if mask is not None:
        mask_area = np.sum(mask)
        mask_ratio = mask_area / (area + 1e-6)
        features.extend([mask_area, mask_ratio])
    else:
        features.extend([0, 0])
    
    # Pad to consistent size
    if len(features) < 15:
        features.extend([0] * (15 - len(features)))
    else:
        features = features[:15]
    
    return np.array(features, dtype=np.float32)

def is_duplicate_balanced(box1, box2, mask1, mask2, features1, features2):
    """Balanced duplicate detection - less aggressive"""
    # Calculate centers
    x1_1, y1_1, x2_1, y2_1 = box1[:4]
    x1_2, y1_2, x2_2, y2_2 = box2[:4]
    center1 = ((x1_1 + x2_1) / 2, (y1_1 + y2_1) / 2)
    center2 = ((x1_2 + x2_2) / 2, (y1_2 + y2_2) / 2)
    distance = np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
    
    # If too far apart, not duplicates
    if distance > DISTANCE_THRESH:
        return False
    
    # Calculate box IoU
    box_iou = _iou(box1, box2)
    
    # Balanced IoU threshold - only remove very overlapping boxes
    if box_iou > 0.6:
        return True
    
    # Calculate mask overlap if masks are available
    if mask1 is not None and mask2 is not None:
        mask_overlap = calculate_mask_overlap(mask1, mask2)
        if mask_overlap > MASK_IOU_THRESH:
            return True
    
    # Calculate feature similarity - only remove very similar objects
    feature_sim = cosine_similarity(features1, features2)
    if feature_sim > FEATURE_THRESH and box_iou > 0.3:
        return True
    
    return False

def balanced_nms(boxes, masks=None):
    """Balanced NMS - less aggressive"""
    if len(boxes) == 0:
        return boxes, masks if masks else []
    
    boxes = np.array(boxes, dtype=np.float32)
    masks_list = list(masks) if masks else []
    
    # Sort by confidence
    idxs = np.argsort(-boxes[:, 4])
    keep = []
    keep_masks = []
    
    for i in idxs:
        b = boxes[i]
        m = masks_list[i] if masks_list else None
        
        # Check against already kept boxes
        should_keep = True
        for j in keep:
            kept_box = boxes[j]
            kept_mask = masks_list[j] if masks_list else None
            
            # Extract features for comparison
            features1 = extract_simple_features(b, m)
            features2 = extract_simple_features(kept_box, kept_mask)
            
            if is_duplicate_balanced(b, kept_box, m, kept_mask, features1, features2):
                should_keep = False
                break
        
        if should_keep:
            keep.append(i)
            if masks_list:
                keep_masks.append(m)
    
    result_boxes = boxes[keep]
    result_masks = [masks_list[i] for i in keep] if masks_list else []
    
    return result_boxes, result_masks

def balanced_multi_test_detection(img_bgr, model):
    """Balanced multi-test detection with better coverage"""
    print("Running balanced multi-test detection...")
    
    # Stage 1: Original detection with lower confidence
    print("Stage 1: Original detection...")
    original_boxes, original_masks = run_detection_test(img_bgr, model, "Original (conf=0.15)", conf_thresh=CONF_THRESH)
    print(f"Original detection: {len(original_boxes)} boxes")
    
    if len(original_boxes) == 0:
        return [], []
    
    # Stage 2: Canny edge detection
    print("Stage 2: Canny edge detection...")
    edge_boxes, edge_masks = run_detection_test(img_bgr, model, "Edge-overlay (Canny, conf=0.01)", 
                                               edge_overlay_canny, conf_thresh=EDGE_CONF_THRESH_CANNY)
    print(f"Canny edge detection: {len(edge_boxes)} boxes")
    
    # Stage 3: Sobel edge detection (restored for better coverage)
    print("Stage 3: Sobel edge detection...")
    sobel_boxes, sobel_masks = run_detection_test(img_bgr, model, "Edge-overlay (Sobel, conf=0.05)", 
                                                  edge_overlay_sobel, conf_thresh=EDGE_CONF_THRESH_SOBEL)
    print(f"Sobel edge detection: {len(sobel_boxes)} boxes")
    
    # Combine all detections
    all_boxes = original_boxes + edge_boxes + sobel_boxes
    all_masks = original_masks + edge_masks + sobel_masks
    
    print(f"Total detections before deduplication: {len(all_boxes)}")
    
    # Apply balanced deduplication
    if len(all_boxes) > 0:
        final_boxes, final_masks = balanced_nms(all_boxes, all_masks)
        print(f"After balanced NMS: {len(final_boxes)}")
        
        return final_boxes, final_masks
    
    return [], []

def draw_detections_with_masks(image, detections, masks=None):
    """Draw detections with mask outlines"""
    result_image = image.copy()
    
    for i, detection in enumerate(detections):
        bbox = detection
        confidence = detection[4] if len(detection) > 4 else 0.0
        
        x1, y1, x2, y2 = map(int, bbox[:4])
        
        # Color based on confidence
        if confidence > 0.7:
            color = (0, 255, 0)  # Green for high confidence
        elif confidence > 0.4:
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
        label = f"obj_{i}: {confidence:.3f}"
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
    
    print("Running balanced detection...")
    start_time = time.time()
    
    # Run balanced detection with better coverage
    final_boxes, final_masks = balanced_multi_test_detection(img, model)
    
    total_time = time.time() - start_time
    
    print("Drawing results...")
    result_image = draw_detections_with_masks(img, final_boxes, final_masks)
    
    # Save result
    cv2.imwrite(OUTPUT_IMAGE, result_image)
    
    # Print results
    print(f"\n=== BALANCED DETECTION RESULTS ===")
    print(f"Total time: {total_time:.2f}s")
    print(f"Final detections: {len(final_boxes)}")
    print(f"Results saved to: {OUTPUT_IMAGE}")
    
    # Print detection details
    print("\n=== DETECTION DETAILS ===")
    for i, detection in enumerate(final_boxes):
        x1, y1, x2, y2, confidence = detection
        area = (x2 - x1) * (y2 - y1)
        mask_area = np.sum(final_masks[i]) if final_masks and i < len(final_masks) else 0
        print(f"{i+1}. Box: [{x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}] - Conf: {confidence:.3f} - Area: {area:.0f}, Mask: {mask_area:.0f}")

if __name__ == "__main__":
    main() 