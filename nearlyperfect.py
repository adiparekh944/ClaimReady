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
OUTPUT_IMAGE = os.path.join(OUTPUT_DIR, 'IMG_4025_dynamic_detector_output.png')

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === DETECTION PARAMETERS ===
SCALES = [640, 1280, 1920]
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

def run_detection_test(img_bgr, model, test_name, transform_func=None, conf_thresh=None):
    """Run detection with optional transformation"""
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

def smart_deduplication(boxes, masks=None):
    """Smart deduplication that preserves important objects"""
    if len(boxes) == 0:
        return boxes, masks if masks else []
    
    # Sort by confidence (highest first)
    sorted_indices = np.argsort([-box[4] for box in boxes])
    sorted_boxes = [boxes[i] for i in sorted_indices]
    sorted_masks = [masks[i] for i in sorted_indices] if masks else []
    
    final_boxes = []
    final_masks = []
    
    for i, box in enumerate(sorted_boxes):
        mask = sorted_masks[i] if sorted_masks and i < len(sorted_masks) else None
        should_keep = True
        
        x1, y1, x2, y2, conf = box
        area = (x2 - x1) * (y2 - y1)
        
        # Check for overlaps with existing detections
        for kept_box in final_boxes:
            kept_mask = final_masks[len(final_boxes) - 1] if final_masks else None
            
            # Calculate overlap
            box_iou = _iou(box, kept_box)
            mask_overlap = calculate_mask_overlap(mask, kept_mask)
            
            # Use IoU threshold based on object size
            if area > 1000000:  # Large objects (desk, chair)
                iou_threshold = 0.4
            elif area > 100000:  # Medium objects (monitor, laptop)
                iou_threshold = 0.5
            elif area > 10000:  # Small objects (medals, small items)
                iou_threshold = 0.6
            else:  # Very small objects
                iou_threshold = 0.7
            
            if box_iou > iou_threshold or mask_overlap > iou_threshold:
                should_keep = False
                break
        
        if should_keep:
            final_boxes.append(box)
            if mask is not None:
                final_masks.append(mask)
    
    return final_boxes, final_masks

def effective_detection(img_bgr, model):
    """Comprehensive detection using YOLO with multiple strategies"""
    print("Running comprehensive detection...")
    
    all_boxes = []
    all_masks = []
    
    # Stage 1: Standard detection with reasonable confidence
    print("Stage 1: Standard detection...")
    standard_boxes, standard_masks = run_detection_test(img_bgr, model, "Standard", conf_thresh=0.20)
    all_boxes.extend(standard_boxes)
    all_masks.extend(standard_masks)
    
    # Stage 2: Lower confidence detection for missed objects
    print("Stage 2: Lower confidence detection...")
    low_conf_boxes, low_conf_masks = run_detection_test(img_bgr, model, "Low confidence", conf_thresh=0.10)
    all_boxes.extend(low_conf_boxes)
    all_masks.extend(low_conf_masks)
    
    # Stage 3: Very low confidence detection for small objects
    print("Stage 3: Very low confidence detection...")
    very_low_boxes, very_low_masks = run_detection_test(img_bgr, model, "Very low confidence", conf_thresh=0.05)
    all_boxes.extend(very_low_boxes)
    all_masks.extend(very_low_masks)
    
    # Stage 4: Edge-enhanced detection
    print("Stage 4: Edge-enhanced detection...")
    def edge_enhance(img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edges_3ch = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        return cv2.addWeighted(img, 0.8, edges_3ch, 0.2, 0)
    
    edge_boxes, edge_masks = run_detection_test(img_bgr, model, "Edge enhanced", edge_enhance, conf_thresh=0.15)
    all_boxes.extend(edge_boxes)
    all_masks.extend(edge_masks)
    
    # Stage 5: Brightness enhancement for light objects (desk, medals)
    print("Stage 5: Brightness enhancement...")
    def brightness_enhance(img):
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hsv[:, :, 2] = cv2.add(hsv[:, :, 2], 30)  # Increase brightness
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    
    bright_boxes, bright_masks = run_detection_test(img_bgr, model, "Brightness enhanced", brightness_enhance, conf_thresh=0.12)
    all_boxes.extend(bright_boxes)
    all_masks.extend(bright_masks)
    
    # Stage 6: Contrast enhancement for small objects
    print("Stage 6: Contrast enhancement...")
    def contrast_enhance(img):
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
    contrast_boxes, contrast_masks = run_detection_test(img_bgr, model, "Contrast enhanced", contrast_enhance, conf_thresh=0.08)
    all_boxes.extend(contrast_boxes)
    all_masks.extend(contrast_masks)
    
    # Stage 7: Grayscale detection for structural objects
    print("Stage 7: Grayscale detection...")
    def grayscale_enhance(img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_3ch = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        return gray_3ch
    
    gray_boxes, gray_masks = run_detection_test(img_bgr, model, "Grayscale detection", grayscale_enhance, conf_thresh=0.06)
    all_boxes.extend(gray_boxes)
    all_masks.extend(gray_masks)
    
    print(f"Total detections before deduplication: {len(all_boxes)}")
    
    # Apply smart deduplication
    if len(all_boxes) > 0:
        final_boxes, final_masks = smart_deduplication(all_boxes, all_masks)
        print(f"After deduplication: {len(final_boxes)}")
        
        return final_boxes, final_masks
    
    return [], []

def draw_detections(image, detections, masks=None):
    """Draw detections with proper visualization"""
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
    
    print("Running effective object detection...")
    start_time = time.time()
    
    # Run effective detection pipeline
    final_boxes, final_masks = effective_detection(img, model)
    
    total_time = time.time() - start_time
    
    print("Drawing results...")
    result_image = draw_detections(img, final_boxes, final_masks)
    
    # Save result
    cv2.imwrite(OUTPUT_IMAGE, result_image)
    
    # Print results
    print(f"\n=== EFFECTIVE DETECTOR RESULTS ===")
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