import time
import os
import cv2
import numpy as np
import torch
from ultralytics import YOLO
from datetime import datetime

# ================= CONFIGURATION =================
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "yolo11n-seg.pt")
SCALES = [640, 1280, 1920]
CONF_THRESH = 0.15
EDGE_CONF_CANNY = 0.01
EDGE_CONF_SOBEL = 0.05
IOU_NMS = 0.9
NMS_IOU_FINAL = 0.3
MASK_THRESH = 0.01
EDGE_THRESH = 15
MASK_IOU_THRESH = 0.5  # Threshold for mask-based IoU
MIN_MASK_AREA = 100  # Minimum mask area to keep

# Output directory for saved images
OUTPUT_DIR = "detection_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

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
    
    if results.masks is not None:
        for i, mask_tensor in enumerate(results.masks.data):
            # Convert tensor to numpy and resize to original image size
            mask = mask_tensor.cpu().numpy()
            mask = cv2.resize(mask, (img_shape[1], img_shape[0]))
            mask = (mask > MASK_THRESH).astype(np.uint8)
            
            # Filter out small masks
            if mask_area(mask) >= MIN_MASK_AREA:
                masks.append(mask)
                # Get corresponding score
                if results.boxes is not None and i < len(results.boxes):
                    score = float(results.boxes[i].conf[0])
                else:
                    score = 1.0  # Default score if no boxes
                scores.append(score)
    
    return masks, scores


def non_max_suppression_masks(detections, iou_thresh):
    """NMS for masks only"""
    if not detections:
        return []
    
    masks = [d['mask'] for d in detections]
    scores = [d['score'] for d in detections]
    
    # Sort by score in descending order
    idxs = np.argsort([-s for s in scores])
    keep = []
    
    for i in idxs:
        should_keep = True
        for j in keep:
            mask_iou_val = mask_iou(masks[i], masks[j])
            
            # If mask IoU is above threshold, suppress this detection
            if mask_iou_val > iou_thresh:
                should_keep = False
                break
        
        if should_keep:
            keep.append(i)
    
    return [detections[i] for i in keep]


def expand_mask(mask, iterations=2):
    """Expand mask using morphological operations"""
    if mask is None:
        return None
    
    kernel = np.ones((3, 3), np.uint8)
    expanded_mask = cv2.dilate(mask, kernel, iterations=iterations)
    return expanded_mask


def edge_overlay_canny(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    edges_col = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    return cv2.addWeighted(img, 0.5, edges_col, 0.5, 0)


def edge_overlay_sobel(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    mag = cv2.magnitude(sobelx, sobely)
    mag = np.uint8(np.clip(mag, 0, 255))
    return cv2.cvtColor(mag, cv2.COLOR_GRAY2BGR)


def is_duplicate_mask(mask1, mask2, threshold=0.7):
    """Check if two masks are duplicates"""
    return mask_iou(mask1, mask2) > threshold


def visualize_masks_only(img, detections, title, colors=None):
    """Visualize masks only with different colors and save to disk"""
    vis = img.copy()
    
    # Create mask overlay
    mask_overlay = np.zeros_like(img)
    
    if colors is None:
        # Generate different colors for each mask
        colors = []
        for i in range(len(detections)):
            hue = int(180 * i / max(1, len(detections)))
            color = cv2.cvtColor(np.uint8([[[hue, 255, 255]]]), cv2.COLOR_HSV2BGR)[0][0]
            colors.append(tuple(int(c) for c in color))
    
    for i, det in enumerate(detections):
        mask = det['mask']
        score = det['score']
        
        if mask is not None:
            # Use different color for each mask
            color = colors[i % len(colors)] if i < len(colors) else (255, 255, 255)
            
            # Apply colored mask
            mask_overlay[mask > 0] = color
            
            # Add score text at mask centroid
            moments = cv2.moments(mask)
            if moments['m00'] > 0:
                cx = int(moments['m10'] / moments['m00'])
                cy = int(moments['m01'] / moments['m00'])
                cv2.putText(vis, f'{score:.2f}', (cx-20, cy), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                cv2.putText(vis, f'{score:.2f}', (cx-20, cy), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Blend mask overlay with original image
    if np.any(mask_overlay):
        vis = cv2.addWeighted(vis, 0.4, mask_overlay, 0.6, 0)
    
    # Save image to disk instead of showing
    timestamp = get_timestamp()
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    filename = f"{safe_title}_{timestamp}.png"
    filepath = os.path.join(OUTPUT_DIR, filename)
    cv2.imwrite(filepath, vis)
    print(f"Saved visualization: {filepath}")


def run_detection_test_masks_only(img, model, name, transform, conf_thresh):
    """Single test runner for masks only"""
    test_img = transform(img) if transform else img
    detections = []
    
    for sz in SCALES:
        results = model.predict(test_img, imgsz=sz, conf=conf_thresh, iou=IOU_NMS, verbose=False)
        
        for result in results:
            masks, scores = process_masks(result, img.shape[:2])
            
            for mask, score in zip(masks, scores):
                detection = {
                    'mask': mask,
                    'score': score,
                    'source': name
                }
                detections.append(detection)
    
    # Visualize masks
    print(f"{name}: Found {len(detections)} masks")
    visualize_masks_only(img, detections, f"{name or 'Original'} Masks")
    
    return detections


def yolo_multi_test_detection_masks_only(img, model):
    """Full pipeline with masks only"""
    original_dets = run_detection_test_masks_only(img, model, 'Original', None, CONF_THRESH)
    canny_dets = run_detection_test_masks_only(img, model, 'Canny', edge_overlay_canny, EDGE_CONF_CANNY)
    sobel_dets = run_detection_test_masks_only(img, model, 'Sobel', edge_overlay_sobel, EDGE_CONF_SOBEL)
    
    # Filter out duplicates from edge-enhanced detections
    filtered_dets = []
    for det in canny_dets + sobel_dets:
        if not any(is_duplicate_mask(det['mask'], orig_det['mask']) for orig_det in original_dets):
            filtered_dets.append(det)
    
    print(f"After filtering duplicates: {len(filtered_dets)} additional masks from edge tests")
    return original_dets + filtered_dets


def merge_overlapping_masks(detections, iou_t):
    """Merge overlapping masks"""
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
            
            if mask_iou_val > iou_t:
                group.append(detections[j])
                used[j] = True
        
        # Merge masks by taking union
        merged_mask = group[0]['mask'].copy()
        max_score = max(g['score'] for g in group)
        
        for g in group[1:]:
            if g['mask'] is not None:
                merged_mask = np.logical_or(merged_mask, g['mask']).astype(np.uint8)
        
        # Expand merged mask slightly to ensure connectivity
        merged_mask = expand_mask(merged_mask, iterations=1)
        
        merged_detection = {
            'mask': merged_mask,
            'score': max_score,
            'source': 'merged'
        }
        merged.append(merged_detection)
    
    return merged


def refine_mask_edges(mask, original_img):
    """Refine mask edges using image gradients"""
    if mask is None:
        return None
    
    # Get image gradients
    gray = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    gradient_mag = cv2.magnitude(grad_x, grad_y)
    
    # Normalize gradient magnitude
    gradient_mag = cv2.normalize(gradient_mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    
    # Use gradient to refine mask edges
    mask_edges = cv2.Canny((mask * 255).astype(np.uint8), 50, 150)
    
    # Find contours and refine
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    refined_mask = np.zeros_like(mask)
    for contour in contours:
        # Smooth contour
        epsilon = 0.005 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        cv2.fillPoly(refined_mask, [approx], 1)
    
    return refined_mask


def detect_masks_only(img, model):
    """Main detect & show function for masks only"""
    print("Running multi-test detection with masks only...")
    
    # Get all mask detections from different tests
    all_detections = yolo_multi_test_detection_masks_only(img, model)
    print(f"Total detections before NMS: {len(all_detections)}")
    
    # Apply NMS with masks
    print("Applying NMS with mask IoU...")
    post_nms = non_max_suppression_masks(all_detections, MASK_IOU_THRESH)
    print(f"After NMS: {len(post_nms)} masks")
    
    # Visualize after initial NMS
    visualize_masks_only(img, post_nms, 'After Initial NMS')
    
    # Merge overlapping detections
    print("Merging overlapping masks...")
    final_detections = merge_overlapping_masks(post_nms, NMS_IOU_FINAL)
    print(f"After merging: {len(final_detections)} final masks")
    
    # Refine mask edges
    print("Refining mask edges...")
    for det in final_detections:
        det['mask'] = refine_mask_edges(det['mask'], img)
    
    # Visualize final results
    visualize_masks_only(img, final_detections, 'Final Masks Only')
    
    return final_detections


def save_masks(detections, output_dir, base_filename):
    """Save individual masks as separate files"""
    os.makedirs(output_dir, exist_ok=True)
    
    for i, det in enumerate(detections):
        mask = det['mask']
        score = det['score']
        
        if mask is not None:
            # Save as binary image
            mask_filename = f"{base_filename}_mask_{i+1:03d}_score_{score:.3f}.png"
            mask_path = os.path.join(output_dir, mask_filename)
            cv2.imwrite(mask_path, (mask * 255).astype(np.uint8))
            
            print(f"Saved mask {i+1}: {mask_filename}")


# Example usage:
if __name__ == "__main__":
    img_path = 'C:/Users/Arnav/Downloads/Room3.jpg'
    img = cv2.imread(img_path)
    
    if img is None:
        raise FileNotFoundError(f"Failed to load image at {img_path}")
    
    print(f"Loaded image with shape: {img.shape}")
    print("Starting mask-only detection...")
    print(f"Output images will be saved to: {OUTPUT_DIR}")
    
    detections = detect_masks_only(img, yolo_model)
    
    print(f"Final mask detections: {len(detections)}")
    for i, det in enumerate(detections):
        area = mask_area(det['mask'])
        score = det['score']
        print(f"Mask {i+1}: Area={area} pixels, Score={score:.3f}")
    
    # Save masks to files
    output_dir = "detected_masks"
    base_name = os.path.splitext(os.path.basename(img_path))[0]
    save_masks(detections, output_dir, base_name)
    
    print(f"\nAll detection outputs saved to: {OUTPUT_DIR}")
    print(f"Individual masks saved to: {output_dir}")