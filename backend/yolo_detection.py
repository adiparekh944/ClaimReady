"""
YOLO detection functions for ClaimReady backend
"""

import cv2
import numpy as np
import math
from ultralytics import YOLO
from detection_utils import _iou, size_ratio, center_dist_frac, cosine_similarity
from image_utils import to_grayscale_3ch, edge_overlay_canny
from config import CONF_THRESH_HIGH, CONF_THRESH_MED, CONF_THRESH_LOW, FEATURE_SIM_THRESH, EDGE_THRESH

def process_box_chunk(box_chunk, masks_chunk=None):
    """Process a chunk of boxes for parallel processing"""
    results = []
    for i, box in enumerate(box_chunk):
        x1, y1, x2, y2, conf = box
        results.append({
            'box': box,
            'mask': masks_chunk[i] if masks_chunk else None,
            'features': None  # Will be filled later
        })
    return results

def aggressive_cluster_merging_parallel(boxes, masks=None):
    """Aggressive clustering and merging of boxes using parallel processing"""
    if len(boxes) <= 1:
        return boxes
    
    # Group boxes by confidence level
    high_conf = [b for b in boxes if b[4] >= CONF_THRESH_HIGH]
    med_conf = [b for b in boxes if CONF_THRESH_MED <= b[4] < CONF_THRESH_HIGH]
    low_conf = [b for b in boxes if b[4] < CONF_THRESH_MED]
    
    merged_boxes = []
    
    # Process high confidence boxes first
    for box in high_conf:
        merged = False
        for i, existing in enumerate(merged_boxes):
            if _iou(box, existing) > 0.3:
                # Merge boxes
                merged_boxes[i] = (
                    min(box[0], existing[0]),
                    min(box[1], existing[1]),
                    max(box[2], existing[2]),
                    max(box[3], existing[3]),
                    max(box[4], existing[4])
                )
                merged = True
                break
        if not merged:
            merged_boxes.append(box)
    
    # Process medium confidence boxes
    for box in med_conf:
        merged = False
        for i, existing in enumerate(merged_boxes):
            if _iou(box, existing) > 0.5:
                merged_boxes[i] = (
                    min(box[0], existing[0]),
                    min(box[1], existing[1]),
                    max(box[2], existing[2]),
                    max(box[3], existing[3]),
                    max(box[4], existing[4])
                )
                merged = True
                break
        if not merged:
            merged_boxes.append(box)
    
    # Process low confidence boxes
    for box in low_conf:
        merged = False
        for i, existing in enumerate(merged_boxes):
            if _iou(box, existing) > 0.7:
                merged_boxes[i] = (
                    min(box[0], existing[0]),
                    min(box[1], existing[1]),
                    max(box[2], existing[2]),
                    max(box[3], existing[3]),
                    max(box[4], existing[4])
                )
                merged = True
                break
        if not merged:
            merged_boxes.append(box)
    
    return merged_boxes

def aggressive_cluster_merging(boxes, masks=None):
    """Aggressive clustering and merging of boxes"""
    return aggressive_cluster_merging_parallel(boxes, masks)

def fast_merging(boxes, masks=None):
    """Fast merging of overlapping boxes"""
    if len(boxes) <= 1:
        return boxes
    
    merged = []
    used = set()
    
    for i, box1 in enumerate(boxes):
        if i in used:
            continue
            
        current_box = box1
        current_mask = masks[i] if masks else None
        
        for j, box2 in enumerate(boxes[i+1:], i+1):
            if j in used:
                continue
                
            if _iou(box1, box2) > 0.5:
                # Merge boxes
                current_box = (
                    min(current_box[0], box2[0]),
                    min(current_box[1], box2[1]),
                    max(current_box[2], box2[2]),
                    max(current_box[3], box2[3]),
                    max(current_box[4], box2[4])
                )
                used.add(j)
        
        merged.append(current_box)
        used.add(i)
    
    return merged

def fast_deduplication(boxes, masks=None):
    """Fast deduplication of similar boxes"""
    if len(boxes) <= 1:
        return boxes
    
    # Sort by confidence (highest first)
    boxes_with_idx = [(i, box) for i, box in enumerate(boxes)]
    boxes_with_idx.sort(key=lambda x: x[1][4], reverse=True)
    
    keep = []
    used = set()
    
    for i, box in boxes_with_idx:
        if i in used:
            continue
            
        keep.append(box)
        used.add(i)
        
        # Mark similar boxes as used
        for j, other_box in boxes_with_idx[i+1:]:
            if j in used:
                continue
                
            if _iou(box, other_box) > 0.7:
                used.add(j)
    
    return keep

def smart_deduplication_parallel(boxes, masks=None):
    """Smart deduplication using parallel processing"""
    if len(boxes) <= 1:
        return boxes
    
    # Use fast deduplication as base
    deduped = fast_deduplication(boxes, masks)
    
    # Additional smart filtering
    final_boxes = []
    for box in deduped:
        # Check if box is too small
        w = box[2] - box[0]
        h = box[3] - box[1]
        if w < 10 or h < 10:
            continue
            
        # Check if box has reasonable aspect ratio
        aspect_ratio = w / h if h > 0 else 0
        if aspect_ratio > 10 or aspect_ratio < 0.1:
            continue
            
        final_boxes.append(box)
    
    return final_boxes

def smart_deduplication(boxes, masks=None):
    """Smart deduplication of boxes"""
    return smart_deduplication_parallel(boxes, masks)

def combine_similar_boxes(boxes, size_location_thresh=0.95):
    """Combine boxes that are very similar in size and location"""
    if len(boxes) <= 1:
        return boxes
    
    combined = []
    used = set()
    
    for i, box1 in enumerate(boxes):
        if i in used:
            continue
            
        current_box = box1
        used.add(i)
        
        for j, box2 in enumerate(boxes[i+1:], i+1):
            if j in used:
                continue
                
            # Check size similarity
            size_sim = size_ratio(box1, box2)
            center_sim = 1.0 - center_dist_frac(box1, box2)
            
            if size_sim > size_location_thresh and center_sim > size_location_thresh:
                # Combine boxes
                current_box = (
                    min(current_box[0], box2[0]),
                    min(current_box[1], box2[1]),
                    max(current_box[2], box2[2]),
                    max(current_box[3], box2[3]),
                    max(current_box[4], box2[4])
                )
                used.add(j)
        
        combined.append(current_box)
    
    return combined

def run_detection_test(img_bgr, model, test_name, transform_func=None, conf_thresh=None):
    """Run a single detection test"""
    if transform_func:
        img_test = transform_func(img_bgr)
    else:
        img_test = img_bgr
    
    if conf_thresh:
        results = model(img_test, conf=conf_thresh)
    else:
        results = model(img_test)
    
    boxes = []
    for r in results:
        if r.boxes is not None:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = box.conf[0].cpu().numpy()
                boxes.append((x1, y1, x2, y2, conf))
    
    return boxes

def yolo_multi_test_detection(img_bgr, model):
    """Multi-test YOLO detection pipeline"""
    all_boxes = []
    
    # Test 1: Original image with high confidence
    boxes1 = run_detection_test(img_bgr, model, "Original High", conf_thresh=CONF_THRESH_HIGH)
    all_boxes.extend(boxes1)
    
    # Test 2: Original image with medium confidence
    boxes2 = run_detection_test(img_bgr, model, "Original Med", conf_thresh=CONF_THRESH_MED)
    all_boxes.extend(boxes2)
    
    # Test 3: Grayscale image
    boxes3 = run_detection_test(img_bgr, model, "Grayscale", to_grayscale_3ch, CONF_THRESH_MED)
    all_boxes.extend(boxes3)
    
    # Test 4: Edge overlay
    boxes4 = run_detection_test(img_bgr, model, "Edge Overlay", edge_overlay_canny, CONF_THRESH_MED)
    all_boxes.extend(boxes4)
    
    # Test 5: Low confidence original
    boxes5 = run_detection_test(img_bgr, model, "Original Low", conf_thresh=CONF_THRESH_LOW)
    all_boxes.extend(boxes5)
    
    # Remove duplicates and merge similar boxes
    if all_boxes:
        # First pass: aggressive clustering
        merged_boxes = aggressive_cluster_merging(all_boxes)
        
        # Second pass: smart deduplication
        final_boxes = smart_deduplication(merged_boxes)
        
        # Third pass: combine very similar boxes
        final_boxes = combine_similar_boxes(final_boxes)
        
        return final_boxes
    
    return []

def diagnostic_detection(img_bgr, model):
    """Diagnostic detection for debugging"""
    results = model(img_bgr)
    boxes = []
    
    for r in results:
        if r.boxes is not None:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = box.conf[0].cpu().numpy()
                boxes.append((x1, y1, x2, y2, conf))
    
    return boxes

def detect_fast(img_bgr, model):
    """Fast detection using multi-test pipeline"""
    return yolo_multi_test_detection(img_bgr, model)
