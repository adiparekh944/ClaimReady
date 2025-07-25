import os
import time
import cv2
import numpy as np
from ultralytics import YOLO
import multiprocessing as mp
from functools import partial
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import threading
import psutil

# Paths
MODEL_PATH = 'yolo11n-seg.pt'
IMAGE_PATH = 'C:/Users/Arnav/Downloads/room7.jpg'
OUTPUT_DIR = 'yoloimprvoedoutput'

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === ULTRA-OPTIMIZED DETECTION PARAMETERS ===
SCALES = [640]  # Single scale for speed - most objects detected at 640
IOU_NMS = 0.7   # Slightly lower for speed
MASK_THRESH = 0.01
CONF_THRESH = 0.01  # Lower confidence threshold to maintain accuracy

# Multiprocessing settings - use all available CPU cores
NUM_CORES = min(4, mp.cpu_count())
print(f"Detected {mp.cpu_count()} CPU cores, using {NUM_CORES} cores for processing")

# Performance optimization flags
USE_FAST_MERGING = True
SKIP_MASK_PROCESSING = False  # Skip mask processing for speed

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

def calculate_mask_overlap_parallel(mask_pairs):
    """Calculate overlap between multiple mask pairs in parallel"""
    results = []
    for mask1, mask2 in mask_pairs:
        if mask1 is None or mask2 is None:
            results.append(0.0)
            continue
        
        if mask1.shape != mask2.shape:
            mask1 = cv2.resize(mask1.astype(np.uint8), (mask2.shape[1], mask2.shape[0]), interpolation=cv2.INTER_NEAREST)
        
        intersection = np.logical_and(mask1 > 0, mask2 > 0).sum()
        union = np.logical_or(mask1 > 0, mask2 > 0).sum()
        
        if union == 0:
            results.append(0.0)
        else:
            results.append(intersection / union)
    
    return results

def process_box_chunk(box_chunk, masks_chunk=None):
    """Process a chunk of boxes for parallel merging - designed for multiprocessing"""
    if len(box_chunk) == 0:
        return [], []
    
    # Sort by confidence (highest first)
    sorted_indices = np.argsort([-box[4] for box in box_chunk])
    sorted_boxes = [box_chunk[i] for i in sorted_indices]
    sorted_masks = [masks_chunk[i] for i in sorted_indices] if masks_chunk else []
    
    merged_boxes = []
    merged_masks = []
    
    for i, box in enumerate(sorted_boxes):
        mask = sorted_masks[i] if sorted_masks and i < len(sorted_masks) else None
        x1, y1, x2, y2, conf = box
        area = (x2 - x1) * (y2 - y1)
        
        # Check if this box should be merged with any existing merged box
        should_merge = False
        merge_target = None
        
        for j, merged_box in enumerate(merged_boxes):
            merged_mask = merged_masks[j] if merged_masks else None
            
            # Calculate overlap
            box_iou = _iou(box, merged_box)
            mask_overlap = calculate_mask_overlap(mask, merged_mask)
            
            # More aggressive merging for closely overlapping objects:
            if box_iou > 0.3 or mask_overlap > 0.25:  # High overlap
                should_merge = True
                merge_target = j
            elif box_iou > 0.15 and mask_overlap > 0.2:  # Moderate overlap
                should_merge = True
                merge_target = j
            elif box_iou > 0.05 and area < 20000 and merged_box[4] > 0.4:  # Small object near larger object
                should_merge = True
                merge_target = j
            elif box_iou > 0.02 and area < 10000:  # Very small objects with any overlap
                should_merge = True
                merge_target = j
        
        if should_merge and merge_target is not None:
            # Merge with existing box
            target_box = merged_boxes[merge_target]
            target_mask = merged_masks[merge_target] if merged_masks else None
            
            # Create merged box (union of bounding boxes)
            merged_x1 = min(x1, target_box[0])
            merged_y1 = min(y1, target_box[1])
            merged_x2 = max(x2, target_box[2])
            merged_y2 = max(y2, target_box[3])
            merged_conf = max(conf, target_box[4])  # Keep highest confidence
            
            merged_boxes[merge_target] = [merged_x1, merged_y1, merged_x2, merged_y2, merged_conf]
            
            # Merge masks if available
            if merged_masks and mask is not None and target_mask is not None:
                if mask.shape == target_mask.shape:
                    merged_mask = np.logical_or(mask, target_mask).astype(np.uint8)
                    merged_masks[merge_target] = merged_mask
        else:
            # Add as new box
            merged_boxes.append(box)
            if mask is not None:
                merged_masks.append(mask)
    
    return merged_boxes, merged_masks

def aggressive_cluster_merging_parallel(boxes, masks=None):
    """Aggressive clustering merging with parallel processing for large datasets"""
    if len(boxes) == 0:
        return boxes, masks if masks else []
    
    # For small datasets, use the original sequential method
    if len(boxes) < 50:
        return aggressive_cluster_merging(boxes, masks)
    
    # For large datasets, use parallel processing
    chunk_size = max(1, len(boxes) // NUM_CORES)
    chunks = []
    mask_chunks = []
    
    for i in range(0, len(boxes), chunk_size):
        end = min(i + chunk_size, len(boxes))
        chunks.append(boxes[i:end])
        if masks:
            mask_chunks.append(masks[i:end])
        else:
            mask_chunks.append(None)
    
    # Process chunks in parallel
    with ThreadPoolExecutor(max_workers=NUM_CORES) as executor:
        futures = []
        for chunk, mask_chunk in zip(chunks, mask_chunks):
            future = executor.submit(process_box_chunk, chunk, mask_chunk)
            futures.append(future)
        
        # Collect results
        all_merged_boxes = []
        all_merged_masks = []
        
        for future in futures:
            merged_boxes, merged_masks = future.result()
            all_merged_boxes.extend(merged_boxes)
            all_merged_masks.extend(merged_masks)
    
    # Final merge of all chunks
    if len(all_merged_boxes) > 0:
        return aggressive_cluster_merging(all_merged_boxes, all_merged_masks)
    
    return all_merged_boxes, all_merged_masks

def aggressive_cluster_merging(boxes, masks=None):
    """Aggressive clustering merging for closely overlapping objects like dresser shelves"""
    if len(boxes) == 0:
        return boxes, masks if masks else []
    
    # Sort by confidence (highest first)
    sorted_indices = np.argsort([-box[4] for box in boxes])
    sorted_boxes = [boxes[i] for i in sorted_indices]
    sorted_masks = [masks[i] for i in sorted_indices] if masks else []
    
    merged_boxes = []
    merged_masks = []
    
    for i, box in enumerate(sorted_boxes):
        mask = sorted_masks[i] if sorted_masks and i < len(sorted_masks) else None
        x1, y1, x2, y2, conf = box
        area = (x2 - x1) * (y2 - y1)
        
        # Check if this box should be merged with any existing merged box
        should_merge = False
        merge_target = None
        
        for j, merged_box in enumerate(merged_boxes):
            merged_mask = merged_masks[j] if merged_masks else None
            
            # Calculate overlap
            box_iou = _iou(box, merged_box)
            mask_overlap = calculate_mask_overlap(mask, merged_mask)
            
            # More aggressive merging for closely overlapping objects:
            # 1. High overlap (>30%) - likely same object
            # 2. High mask overlap (>25%) - same object parts
            # 3. Close proximity with similar confidence - parts of same object
            # 4. Small objects near larger objects - parts of larger object
            
            if box_iou > 0.3 or mask_overlap > 0.25:  # High overlap
                should_merge = True
                merge_target = j
            elif box_iou > 0.15 and mask_overlap > 0.2:  # Moderate overlap
                should_merge = True
                merge_target = j
            elif box_iou > 0.05 and area < 20000 and merged_box[4] > 0.4:  # Small object near larger object
                # Check if merging would create a reasonable box
                merged_x1 = min(x1, merged_box[0])
                merged_y1 = min(y1, merged_box[1])
                merged_x2 = max(x2, merged_box[2])
                merged_y2 = max(y2, merged_box[3])
                merged_area = (merged_x2 - merged_x1) * (merged_y2 - merged_y1)
                
                # Allow larger merged boxes for furniture-like objects
                # No area limit - allow any size for furniture
                should_merge = True
                merge_target = j
            elif box_iou > 0.02 and area < 10000:  # Very small objects with any overlap
                # Check if merging would create a reasonable box
                merged_x1 = min(x1, merged_box[0])
                merged_y1 = min(y1, merged_box[1])
                merged_x2 = max(x2, merged_box[2])
                merged_y2 = max(y2, merged_box[3])
                merged_area = (merged_x2 - merged_x1) * (merged_y2 - merged_y1)
                
                # No area limit for small objects
                should_merge = True
                merge_target = j
        
        if should_merge and merge_target is not None:
            # Merge with existing box
            target_box = merged_boxes[merge_target]
            target_mask = merged_masks[merge_target] if merged_masks else None
            
            # Create merged box (union of bounding boxes)
            merged_x1 = min(x1, target_box[0])
            merged_y1 = min(y1, target_box[1])
            merged_x2 = max(x2, target_box[2])
            merged_y2 = max(y2, target_box[3])
            merged_conf = max(conf, target_box[4])  # Keep highest confidence
            
            merged_boxes[merge_target] = [merged_x1, merged_y1, merged_x2, merged_y2, merged_conf]
            
            # Merge masks if available
            if merged_masks and mask is not None and target_mask is not None:
                if mask.shape == target_mask.shape:
                    merged_mask = np.logical_or(mask, target_mask).astype(np.uint8)
                    merged_masks[merge_target] = merged_mask
        else:
            # Add as new box
            merged_boxes.append(box)
            if mask is not None:
                merged_masks.append(mask)
    
    return merged_boxes, merged_masks

def fast_merging(boxes, masks=None):
    """Ultra-fast merging algorithm optimized for speed"""
    if len(boxes) == 0:
        return boxes, masks if masks else []
    
    # Sort by confidence (highest first)
    sorted_indices = np.argsort([-box[4] for box in boxes])
    sorted_boxes = [boxes[i] for i in sorted_indices]
    sorted_masks = [masks[i] for i in sorted_indices] if masks else []
    
    merged_boxes = []
    merged_masks = []
    
    for i, box in enumerate(sorted_boxes):
        mask = sorted_masks[i] if sorted_masks and i < len(sorted_masks) else None
        x1, y1, x2, y2, conf = box
        area = (x2 - x1) * (y2 - y1)
        
        # Fast overlap check - only check against high-confidence boxes
        should_merge = False
        merge_target = None
        
        for j, merged_box in enumerate(merged_boxes):
            # Skip low-confidence comparisons for speed
            if merged_box[4] < 0.3:
                continue
                
            # Fast IoU calculation
            box_iou = _iou(box, merged_box)
            
            # Aggressive merging for speed
            if box_iou > 0.4:  # High overlap
                should_merge = True
                merge_target = j
                break  # Stop at first match for speed
            elif box_iou > 0.2 and area < 50000:  # Moderate overlap for small objects
                should_merge = True
                merge_target = j
                break
            elif box_iou > 0.1 and area < 10000:  # Any overlap for very small objects
                should_merge = True
                merge_target = j
                break
        
        if should_merge and merge_target is not None:
            # Fast merge
            target_box = merged_boxes[merge_target]
            merged_x1 = min(x1, target_box[0])
            merged_y1 = min(y1, target_box[1])
            merged_x2 = max(x2, target_box[2])
            merged_y2 = max(y2, target_box[3])
            merged_conf = max(conf, target_box[4])
            
            merged_boxes[merge_target] = [merged_x1, merged_y1, merged_x2, merged_y2, merged_conf]
        else:
            # Add as new box
            merged_boxes.append(box)
            if mask is not None:
                merged_masks.append(mask)
    
    return merged_boxes, merged_masks

def fast_deduplication(boxes, masks=None):
    """Ultra-fast deduplication optimized for speed"""
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
        
        # Fast overlap check
        for kept_box in final_boxes:
            box_iou = _iou(box, kept_box)
            
            # Simplified thresholds for speed
            if area > 100000:  # Large objects
                iou_threshold = 0.5
            elif area > 10000:  # Medium objects
                iou_threshold = 0.6
            else:  # Small objects
                iou_threshold = 0.7
            
            if box_iou > iou_threshold:
                should_keep = False
                break
        
        if should_keep:
            final_boxes.append(box)
            if mask is not None:
                final_masks.append(mask)
    
    return final_boxes, final_masks

def run_detection_test(img_bgr, model, test_name, transform_func=None, conf_thresh=None):
    """Run detection with optional transformation - ultra-optimized for speed"""
    if transform_func:
        test_img = transform_func(img_bgr)
    else:
        test_img = img_bgr
    
    # Use optimized confidence threshold
    if conf_thresh is None:
        conf_thresh = CONF_THRESH
    
    boxes = []
    masks = []
    
    # Single scale detection for speed
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
        
        # Collect masks only if needed
        if not SKIP_MASK_PROCESSING and hasattr(res[0], "masks") and res[0].masks is not None and res[0].masks.data is not None:
            m = res[0].masks.data.cpu().numpy()
            m = (m > MASK_THRESH).astype(np.uint8)
            masks.extend(m)
    
    return boxes, masks

def smart_deduplication_parallel(boxes, masks=None):
    """Smart deduplication with parallel processing for large datasets"""
    if len(boxes) == 0:
        return boxes, masks if masks else []
    
    # For small datasets, use the original sequential method
    if len(boxes) < 20:
        return smart_deduplication(boxes, masks)
    
    # Sort by confidence (highest first)
    sorted_indices = np.argsort([-box[4] for box in boxes])
    sorted_boxes = [boxes[i] for i in sorted_indices]
    sorted_masks = [masks[i] for i in sorted_indices] if masks else []
    
    final_boxes = []
    final_masks = []
    
    # Process boxes in chunks for parallel processing
    chunk_size = max(1, len(sorted_boxes) // NUM_CORES)
    
    for i in range(0, len(sorted_boxes), chunk_size):
        end = min(i + chunk_size, len(sorted_boxes))
        chunk_boxes = sorted_boxes[i:end]
        chunk_masks = sorted_masks[i:end] if sorted_masks else [None] * len(chunk_boxes)
        
        # Process this chunk
        for j, box in enumerate(chunk_boxes):
            mask = chunk_masks[j] if chunk_masks else None
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

def diagnostic_detection(img_bgr, model):
    """Diagnostic detection optimized for speed under 10 seconds"""
    print("Running ultra-fast diagnostic detection...")
    
    # First pass with optimized parameters
    boxes, masks = run_detection_test(img_bgr, model, "Diagnostic", conf_thresh=CONF_THRESH)
    
    # Second pass with very low confidence to catch missed objects
    boxes2, masks2 = run_detection_test(img_bgr, model, "Diagnostic2", conf_thresh=0.005)
    
    # Combine detections
    all_boxes = boxes + boxes2
    all_masks = masks + masks2 if masks and masks2 else (masks if masks else masks2)
    
    # Apply fast deduplication
    if len(all_boxes) > 0:
        if USE_FAST_MERGING:
            final_boxes, final_masks = fast_merging(all_boxes, all_masks)
            # Apply fast deduplication after merging
            final_boxes, final_masks = fast_deduplication(final_boxes, final_masks)
        else:
            final_boxes, final_masks = fast_deduplication(all_boxes, all_masks)
        return final_boxes, final_masks
    
    return [], []

def calculate_overlap_opacity(detections):
    """Calculate opacity for each detection based on overlap with other detections"""
    if len(detections) <= 1:
        return [1.0] * len(detections)  # Full opacity if no overlaps
    
    opacity_map = []
    
    for i, detection in enumerate(detections):
        # Handle both 4-value and 5-value detection formats
        if len(detection) >= 5:
            x1, y1, x2, y2, conf = detection
        else:
            x1, y1, x2, y2 = detection
            conf = 1.0  # Default confidence if not provided
        
        overlap_count = 0
        
        # Count how many other detections overlap with this one
        for j, other_detection in enumerate(detections):
            if i == j:
                continue
            
            # Handle both 4-value and 5-value detection formats
            if len(other_detection) >= 5:
                ox1, oy1, ox2, oy2, oconf = other_detection
            else:
                ox1, oy1, ox2, oy2 = other_detection
                oconf = 1.0  # Default confidence if not provided
            
            # Check if boxes overlap
            if not (x2 < ox1 or x1 > ox2 or y2 < oy1 or y1 > oy2):
                overlap_count += 1
        
        # Calculate opacity based on overlap count
        # Full opacity (1.0) when no overlaps, minimum 0.15 when many overlaps
        if overlap_count == 0:
            opacity = 1.0
        else:
            # Gradual decay: opacity = 1.0 - (0.85 * overlap_count / max_possible_overlaps)
            max_possible_overlaps = len(detections) - 1
            opacity = max(0.15, 1.0 - (0.85 * overlap_count / max_possible_overlaps))
        
        opacity_map.append(opacity)
    
    return opacity_map

def draw_detections(image, detections, masks=None, title="Detection Results"):
    """Draw detections with transparent overlapping regions to prevent blocking the image"""
    if len(detections) == 0:
        return image
    
    result_image = image.copy()
    height, width = image.shape[:2]
    
    # Calculate line thickness based on image size (3px relative to image)
    min_dimension = min(height, width)
    line_thickness = max(1, int(3 * min_dimension / 1000))
    
    # Convert detections to list for easier processing
    detections_list = list(detections)
    
    # Create a mask for all bounding box areas
    boxes_mask = np.zeros((height, width), dtype=np.uint8)
    
    # Draw all bounding boxes onto the mask first
    for i, detection in enumerate(detections_list):
        x1, y1, x2, y2 = map(int, detection[:4])
        cv2.rectangle(boxes_mask, (x1, y1), (x2, y2), 255, line_thickness)
    
    # Create a composite image with only the bounding boxes
    composite_image = np.zeros_like(image)
    for i, detection in enumerate(detections_list):
        x1, y1, x2, y2 = map(int, detection[:4])
        color = (0, 255, 0)  # Green - best contrast and natural appearance
        cv2.rectangle(composite_image, (x1, y1), (x2, y2), color, line_thickness)
    
    # Convert mask to 3D for RGB blending
    boxes_mask_3d = boxes_mask.astype(np.float32) / 255.0
    boxes_mask_3d = np.stack([boxes_mask_3d] * 3, axis=2)
    
    # Blend only the bounding box areas with 50% opacity
    alpha = 0.50
    result_image = (result_image * (1 - alpha * boxes_mask_3d) + 
                   composite_image * alpha * boxes_mask_3d).astype(np.uint8)
    
    return result_image

def get_cpu_usage():
    """Get current CPU usage percentage"""
    return psutil.cpu_percent(interval=1)

def optimize_workers():
    """Optimize number of workers based on CPU usage"""
    cpu_usage = get_cpu_usage()
    if cpu_usage > 80:
        return max(1, NUM_CORES - 1)  # Leave one core free
    else:
        return NUM_CORES

def main():
    print("Loading YOLO model...")
    model = YOLO(MODEL_PATH)
    
    print("Reading image...")
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        raise FileNotFoundError(f'Could not load image: {IMAGE_PATH}')
    
    # Optimize workers based on current CPU usage
    optimal_workers = optimize_workers()
    print(f"Using {optimal_workers} CPU cores for parallel processing...")
    print(f"Current CPU usage: {get_cpu_usage():.1f}%")
    print(f"Optimization: Single scale ({SCALES[0]}), Fast merging: {USE_FAST_MERGING}")
    
    print("Running ultra-fast diagnostic detection...")
    start_time = time.time()
    
    # Run only diagnostic detection with fast algorithms
    diagnostic_boxes, diagnostic_masks = diagnostic_detection(img, model)
    
    # Apply fast merging if not already done
    if len(diagnostic_boxes) > 0 and not USE_FAST_MERGING:
        final_boxes, final_masks = fast_merging(diagnostic_boxes, diagnostic_masks)
    else:
        final_boxes, final_masks = diagnostic_boxes, diagnostic_masks
    
    total_time = time.time() - start_time
    
    print(f"\n=== ULTRA-FAST DETECTION RESULTS ===")
    print(f"Total time: {total_time:.2f}s")
    print(f"Target: <10s, Achieved: {total_time:.2f}s")
    print(f"Detections: {len(final_boxes)}")
    print(f"CPU cores utilized: {optimal_workers}")
    print(f"Final CPU usage: {get_cpu_usage():.1f}%")
    
    # Save the diagnostic detection result
    if len(final_boxes) > 0:
        result_image = draw_detections(img, final_boxes, final_masks, "Ultra-Fast Detection")
        filename = f"ultra_fast_detection_{len(final_boxes)}_detections.png"
        filepath = os.path.join(OUTPUT_DIR, filename)
        cv2.imwrite(filepath, result_image)
        print(f"Saved result to: {filepath}")
    
    print("\n=== SUMMARY ===")
    print(f"Ultra-Fast Detection: {len(final_boxes)} detections")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Target achieved: {'✅ YES' if total_time < 10 else '❌ NO'}")
    print(f"CPU cores used: {optimal_workers}")
    print(f"Optimizations: Single scale, Fast merging, Optimized thresholds")
    print(f"Result saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    main() 