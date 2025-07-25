# === CLAIMREADY BACKEND SERVER ===
# Advanced YOLO + Gemini AI Insurance Claim Analysis
#
# DETECTION MODES:
# 1. Basic YOLO (commented out) - Simple single-pass detection
# 2. Advanced YOLO (default) - Multi-test pipeline with feature-based duplicate detection
# 3. SAHI Detection (optional) - Slicing Aided Hyper Inference (most advanced)
#    Enable with: export USE_SAHI=true
#
# The system now uses the FULL COMPLEX YOLO DETECTION PIPELINE by default:
# - Multi-scale detection (640, 1280, 1920)
# - Multi-test pipeline (Original + Grayscale + Edge-overlay)
# - Feature-based duplicate detection
# - Mask-based similarity checking
# - Advanced confidence thresholds (0.25, 0.05, 0.01)
# - Box merging with 95% similarity threshold
import time
import os
import base64
import io
import json
import logging
import random
import math
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from PIL import Image
import cv2
import numpy as np
import google.generativeai as genai

# Object Detection Imports
from ultralytics import YOLO
import multiprocessing as mp
from functools import partial
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import threading
import psutil
import colorsys

# Replace the color palette with 100 human-friendly color names and hex codes
COLOR_PALETTE = [
    ("Red", "#FF0000"),
    ("Lime", "#00FF00"),
    ("Blue", "#0000FF"),
    ("Yellow", "#FFFF00"),
    ("Magenta", "#FF00FF"),
    ("Cyan", "#00FFFF"),
    ("Maroon", "#800000"),
    ("Green", "#008000"),
    ("Navy", "#000080"),
    ("Olive", "#808000"),
    ("Purple", "#800080"),
    ("Teal", "#008080"),
    ("Silver", "#C0C0C0"),
    ("Orange", "#FFA500"),
    ("Brown", "#A52A2A"),
    ("Sea Green", "#2E8B57"),
    ("Indigo", "#4B0082"),
    ("Crimson", "#DC143C"),
    ("Deep Pink", "#FF1493"),
    ("Light Sea Green", "#20B2AA"),
    ("Dark Orchid", "#9932CC"),
    ("Green Yellow", "#ADFF2F"),
    ("Dark Turquoise", "#00CED1"),
    ("Orange Red", "#FF4500"),
    ("Lawn Green", "#7CFC00"),
    ("Dodger Blue", "#1E90FF"),
    ("Orchid", "#DA70D6"),
    ("Firebrick", "#B22222"),
    ("Medium Spring Green", "#00FA9A"),
    ("Medium Orchid", "#BA55D3"),
    ("Indian Red", "#CD5C5C"),
    ("Medium Sea Green", "#3CB371"),
    ("Midnight Blue", "#191970"),
    ("Gold", "#FFD700"),
    ("Hot Pink", "#FF69B4"),
    ("Cornflower Blue", "#6495ED"),
    ("Tomato", "#FF6347"),
    ("Slate Blue", "#6A5ACD"),
    ("Light Coral", "#F08080"),
    ("Dark Red", "#8B0000"),
    ("Forest Green", "#228B22"),
    ("Cadet Blue", "#5F9EA0"),
    ("Deep Sky Blue", "#00BFFF"),
    ("Dark Orange", "#FF8C00"),
    ("Yellow Green", "#9ACD32"),
    ("Royal Blue", "#4169E1"),
    ("Navajo White", "#FFDEAD"),
    ("Spring Green", "#00FF7F"),
    ("Dark Goldenrod", "#B8860B"),
    ("Goldenrod", "#DAA520"),
    ("Medium Purple", "#9370DB"),
    ("Sandy Brown", "#F4A460"),
    ("Blue Violet", "#8A2BE2"),
    ("Medium Turquoise", "#48D1CC"),
    ("Medium Slate Blue", "#7B68EE"),
    ("Chocolate", "#D2691E"),
    ("Aquamarine", "#7FFFD4"),
    ("Burlywood", "#DEB887"),
    ("Thistle", "#D8BFD8"),
    ("Pale Green", "#98FB98"),
    ("Bisque", "#FFE4C4"),
    ("Slate Gray", "#708090"),
    ("Light Pink", "#FFB6C1"),
    ("Rosy Brown", "#BC8F8F"),
    ("Turquoise", "#40E0D0"),
    ("Lime Green", "#32CD32"),
    ("Khaki", "#F0E68C"),
    ("Dark Magenta", "#8B008B"),
    ("Dark Salmon", "#E9967A"),
    ("Olive Drab", "#6B8E23"),
    ("Sky Blue", "#87CEEB"),
    ("Peru", "#CD853F"),
    ("Steel Blue", "#4682B4"),
    ("Dark Sea Green", "#8FBC8F"),
    ("Light Steel Blue", "#B0C4DE"),
    ("Light Green", "#90EE90"),
    ("Dark Brown", "#993333"),
    ("Dark Khaki", "#BDB76B"),
    ("Powder Blue", "#B0E0E6"),
    ("Dark Olive Green", "#556B2F"),
    ("Lavender", "#E6E6FA"),
    ("Light Slate Gray", "#778899"),
    ("Dark Gray", "#A9A9A9"),
    ("Plum", "#DDA0DD"),
    ("Moccasin", "#FFE4B5"),
    ("Coral", "#FF7F50"),
    ("Tan", "#D2B48C"),
    ("Pale Turquoise", "#AFEEEE"),
    ("Salmon", "#FA8072"),
    ("Papaya Whip", "#FFEFD5"),
    ("Wheat", "#F5DEB3"),
    ("Pale Goldenrod", "#EEE8AA"),
    ("Light Cyan", "#E0FFFF"),
    ("Light Gray", "#D3D3D3"),
    ("Lemon Chiffon", "#FFFACD"),
    ("Old Lace", "#FDF5E6"),
    ("Floral White", "#FFFAF0"),
    ("Honeydew", "#F0FFF0"),
    ("White Smoke", "#F5F5F5"),
    ("White", "#FFFFFF"),
]

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

# Assign colors to boxes in order, always returning a list of (color_name, hex_code) tuples

def assign_colors_to_boxes(bboxes):
    assigned = []
    for i, bbox in enumerate(bboxes):
        color_name, hex_code = COLOR_PALETTE[i % len(COLOR_PALETTE)]
        assigned.append((color_name, hex_code))
    return assigned

# Utility to compute average color in a region
import numpy as np

def average_color(image, bbox):
    x1, y1, x2, y2 = bbox
    region = image[y1:y2, x1:x2]
    if region.size == 0:
        return (0, 0, 0)
    avg = np.mean(region.reshape(-1, 3), axis=0)
    return tuple(int(x) for x in avg)

def color_distance(rgb1, rgb2):
    # Euclidean distance in RGB
    return np.sqrt(sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

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

# Load YOLO model once
YOLO_MODEL_PATH = os.environ.get("YOLO_MODEL_PATH", "yolo11n-seg.pt")
YOLO_MODEL = YOLO(YOLO_MODEL_PATH)

# Gemini config from env
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyDVIppKcsZwVa3vkZWazztC9XY_-oZUufU")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")
genai.configure(api_key=GEMINI_API_KEY)
GEMINI_GEN_MODEL = genai.GenerativeModel(GEMINI_MODEL)

# Gemini response schema (now without nullify)
GEMINI_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "imageAttachment": {"type": "string"},
                    "bbox": {"type": "array", "items": {"type": "integer"}, "minItems": 4, "maxItems": 4},
                    "name": {"type": "string"},
                    "category": {"type": "string"},
                    "price_usd": {"type": "number"},
                    "description": {"type": "string"}
                },
                "required": ["code", "imageAttachment", "bbox", "name", "category", "price_usd", "description"]
            }
        }
    },
    "required": ["items"]
}

# === OBJECT DETECTION FUNCTIONS ===

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

def draw_detections(image, detections, masks=None, title="Detection Results", show_popup=True):
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
    
    # Show the result as a popup only if requested
    if show_popup:
        cv2.imshow(title, result_image)
        cv2.waitKey(0)  # Wait for any key press
        cv2.destroyAllWindows()  # Close all windows
    
    return result_image

# Drawing function always uses the same tuple for both label and rectangle

def draw_detections_colored(image, boxes, color_tuples, masks=None, title="Detection Results", show_popup=True):
    """Draw detections with all bounding boxes in lime green."""
    print(f"[DEBUG] draw_detections_colored called with {len(boxes)} boxes, show_popup={show_popup}")
    if len(boxes) == 0:
        print("[DEBUG] No boxes to draw, skipping popup.")
        return image

    result_image = image.copy()
    height, width = image.shape[:2]
    min_dimension = min(height, width)
    # Ensure line thickness is always visible
    line_thickness = max(3, int(3 * min_dimension / 1000))

    # Use lime green color for all boxes
    box_color = (0, 255, 0)  # Lime green in BGR

    for i, box in enumerate(boxes):
        if len(box) == 5:
            x1, y1, x2, y2, conf = box
        elif len(box) == 4:
            x1, y1, x2, y2 = box
            conf = 1.0
        # Clamp coordinates to image bounds
        x1 = max(0, min(int(x1), width-1))
        y1 = max(0, min(int(y1), height-1))
        x2 = max(0, min(int(x2), width-1))
        y2 = max(0, min(int(y2), height-1))
        if x2 <= x1 or y2 <= y1:
            continue  # skip degenerate boxes
        cv2.rectangle(result_image, (x1, y1), (x2, y2), box_color, line_thickness)

    if show_popup:
        print(f"[DEBUG] Showing popup with title: {title}")
        cv2.imshow(title, result_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        print("[DEBUG] Popup closed")
    return result_image

# Use the color_tuples list everywhere downstream (Gemini, frontend, crops, etc) to ensure consistency.

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

def generate_unique_code(existing):
    while True:
        code = str(random.randint(10000, 99999))
        if code not in existing:
            return code

def pil_image_to_base64(pil_img):
    buffer = io.BytesIO()
    pil_img.save(buffer, format="JPEG")
    buffer.seek(0)
    return f"data:image/jpeg;base64,{base64.b64encode(buffer.read()).decode('utf-8')}"

def safe_price(val):
    try:
        if val is None or (isinstance(val, str) and val.strip().lower() in {"nan", ""}):
            return 0.0
        fval = float(val)
        if math.isnan(fval) or math.isinf(fval):
            return 0.0
        return fval
    except (TypeError, ValueError):
        return 0.0

def format_category(category):
    """
    Clean up category names by removing underscores and capitalizing each word.
    Example: 'architectural_fixture' -> 'Architectural Fixture'
    """
    if not category or not isinstance(category, str):
        return category
    # Replace underscores with spaces and capitalize each word
    return ' '.join(word.capitalize() for word in category.replace('_', ' ').split())

def pil_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def resize_image_maintain_aspect_ratio(image, target_longest_edge):
    """
    Resize image so the longest edge is target_longest_edge pixels while maintaining aspect ratio.
    """
    width, height = image.size
    if width > height:
        new_width = target_longest_edge
        new_height = int(height * target_longest_edge / width)
    else:
        new_height = target_longest_edge
        new_width = int(width * target_longest_edge / height)
    
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

def analyze_scene_with_gemini(scene_pil, crop_pils, codes, bboxes, instructions_override=None, temperature_override=None):
    # This function is kept for backward compatibility but is not used
    # The main analysis is done in analyze_scene_with_gemini_final
    pass

def analyze_scene_with_gemini_final(final_image_pil, crop_pils, codes, bboxes, box_colors=None):
    import google.generativeai as genai
    import time
    
    if box_colors is None:
        box_colors = []

    # Use the original image size (no resizing)
    final_image_resized = final_image_pil
    
    # Get the image dimensions for the prompt
    width, height = final_image_resized.size
    
    # Build a list of dicts with bbox for Gemini
    bbox_info = []
    for i, box in enumerate(bboxes):
        if len(box) == 5:
            x1, y1, x2, y2, conf = box
        elif len(box) == 4:
            x1, y1, x2, y2 = box
            conf = 1.0
        bbox_info.append({
            "bbox": [int(x1), int(y1), int(x2), int(y2)]
        })

    # Update Gemini prompt
    instructions = f"""
You are analyzing an image with detected objects. You will receive:
1. The original image without any bounding boxes drawn on it
2. Bounding box coordinates for each detected object
3. Individual cropped segments for each detected object with their coordinates

For each object with provided coordinates, provide:
- name
- category  
- price_usd
- description (including brand and condition if possible)
- bbox (the coordinates [x1, y1, x2, y2] of the bounding box)

Output a JSON array, one object per bounding box, with fields: name, category, price_usd, description, bbox.
"""
    
    # Build contents with the original image (no bounding boxes) and bbox information
    contents = [instructions, "Room with detected objects:", final_image_pil]
    for i, info in enumerate(bbox_info):
        contents.append(f"Box {i}: bbox={info['bbox']}")
    
    # Add individual cropped segments with their coordinates
    for i, crop in enumerate(crop_pils):
        if i < len(bbox_info):
            bbox = bbox_info[i]['bbox']
            contents.append(f"Crop {i} (bbox={bbox}):")
            contents.append(crop)
    
    print(f"[GEMINI DEBUG] Sending to Gemini:")
    print(f"[GEMINI DEBUG] Instructions: {instructions}")
    print(f"[GEMINI DEBUG] Image size: {final_image_resized.size}")
    print(f"[GEMINI DEBUG] Number of contents: {len(contents)}")
    print(f"[GEMINI DEBUG] Number of crops: {len(crop_pils)}")
    
    try:
        print(f"[GEMINI] Starting API call with image size: {final_image_resized.size}")
        gemini_start = time.perf_counter()
        
        response = GEMINI_GEN_MODEL.generate_content(
            contents,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        
        gemini_end = time.perf_counter()
        print(f"[GEMINI] API call completed in {gemini_end - gemini_start:.2f} seconds")
        
        # Extract items from the structured response
        raw = response.text
        # Remove Markdown code block if present
        if raw.strip().startswith('```'):
            lines = raw.strip().splitlines()
            if lines[0].startswith('```') and lines[-1].startswith('```'):
                raw = '\n'.join(lines[1:-1])
        
        import json
        print(f"[GEMINI DEBUG] Raw response from Gemini: {raw}")
        print(f"[GEMINI DEBUG] Response length: {len(raw)}")
        
        # Simple JSON parsing
        try:
            parsed = json.loads(raw)
            items = parsed.get('items', []) if isinstance(parsed, dict) else parsed
            print(f"[GEMINI DEBUG] Parsed items: {items}")
            print(f"[GEMINI DEBUG] Number of items: {len(items)}")
        except Exception as e:
            print(f"[GEMINI DEBUG] JSON parsing error: {e}")
            items = []
        
        # Map response items to codes and bboxes
        mapped_items = []
        
        # Map items using Gemini's provided bounding box coordinates
        print(f"[GEMINI DEBUG] Mapping {len(items)} items to codes")
        for item in items:
            print(f"[GEMINI DEBUG] Processing item: {item}")
            if 'bbox' in item:
                # Use Gemini's bbox coordinates directly
                gemini_bbox = item['bbox']
                print(f"[GEMINI DEBUG] Item has bbox: {gemini_bbox}")
                # Create a unique code for each Gemini item
                item['code'] = f"gemini_{len(mapped_items)}"
                item['imageAttachment'] = f"crop{len(mapped_items)}"
                # Keep Gemini's bbox coordinates
                item['bbox'] = gemini_bbox
                mapped_items.append(item)
                print(f"[GEMINI DEBUG] Mapped item with code: {item['code']}")
            else:
                print(f"[GEMINI DEBUG] Item has no bbox, using fallback")
                # Fallback: map by order if no bbox provided
                if len(mapped_items) < len(codes):
                    i = len(mapped_items)
                    item['code'] = codes[i]
                    item['imageAttachment'] = f"crop{i}"
                    item['bbox'] = list(bboxes[i])
                    mapped_items.append(item)
                    print(f"[GEMINI DEBUG] Fallback mapped item with code: {item['code']}")
        
        print(f"[GEMINI DEBUG] Final mapped items: {mapped_items}")
        
        # When creating code_to_image, use Gemini's bbox coordinates for cropping
        code_to_image = {}
        for item in mapped_items:
            if 'bbox' in item:
                # Use Gemini's bbox coordinates for cropping (no scaling needed)
                bbox = item['bbox']
                x1, y1, x2, y2 = bbox
                print(f"[DEBUG] Using Gemini bbox for {item['code']}: {x1}, {y1}, {x2}, {y2}")
                
                # Get the original image dimensions
                original_width, original_height = final_image_pil.size
                print(f"[DEBUG] Original image size: {original_width}x{original_height}")
                
                # Ensure coordinates are within image bounds
                x1 = max(0, min(x1, original_width - 1))
                y1 = max(0, min(y1, original_height - 1))
                x2 = max(x1 + 1, min(x2, original_width))
                y2 = max(y1 + 1, min(y2, original_height))
                
                print(f"[DEBUG] Final bbox coordinates: {x1}, {y1}, {x2}, {y2}")
                
                # Crop the original image using Gemini's coordinates
                cropped_image = final_image_pil.crop((x1, y1, x2, y2))
                print(f"[DEBUG] Cropped image size: {cropped_image.size}")
                
                # Convert to base64
                cropped_base64 = pil_image_to_base64(cropped_image)
                code_to_image[item['code']] = cropped_base64
                item['gemini_bbox'] = bbox
                print(f"[DEBUG] Added Gemini-cropped image for {item['code']}")
            else:
                # Fallback to full image if no bbox
                code_to_image[item['code']] = pil_image_to_base64(final_image_pil)
                print(f"[DEBUG] Added full image for {item['code']} (no bbox)")
        
        print(f"[DEBUG] Created {len(code_to_image)} images")
        print(f"[DEBUG] Image codes: {list(code_to_image.keys())}")
        
        print(f"[API] Returning response with {len(mapped_items)} items.")
        return mapped_items
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return []  # Return empty list instead of raising
        raise

def analyze_single_image(image_data):
    """
    Analyze a single image using the ultra-optimized detection pipeline.
    """
    try:
        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img_bgr is None:
            return {"error": "Failed to decode image"}
        
        # Use the ultra-optimized detection pipeline
        boxes, masks = diagnostic_detection(img_bgr, YOLO_MODEL)
        
        # Ensure bboxes is always defined before use
        if len(boxes) > 0:
            # Process detected objects
            crop_pils, codes, bboxes = [], [], []
            for i, box in enumerate(boxes):
                if len(box) == 5:
                    x1, y1, x2, y2, confidence = box
                elif len(box) == 4:
                    x1, y1, x2, y2 = box
                    confidence = 1.0
                # Ensure coordinates are within image bounds
                H, W = img_bgr.shape[:2]
                x1 = max(0, int(x1))
                y1 = max(0, int(y1))
                x2 = min(W - 1, int(x2))
                y2 = min(H - 1, int(y2))
                # Crop the detected object
                crop = img_bgr[y1:y2+1, x1:x2+1]
                if crop.size == 0:
                    continue
                # Convert to PIL for Gemini
                crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                crop_pil = Image.fromarray(crop_rgb)
                # Generate unique code
                code = str(i)
                crop_pils.append(crop_pil)
                codes.append(code)
                bboxes.append((x1, y1, x2, y2))
        else:
            bboxes = []

        # Analyze with Gemini
        if crop_pils:
            # Use the original PIL image for the scene
            scene_pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
            analysis_result = analyze_scene_with_gemini_final(scene_pil, crop_pils, codes, bboxes, box_colors=[])
            return analysis_result
        else:
            return {"error": "No valid objects to analyze"}
            
    except Exception as e:
        logger.error(f"Error in analyze_single_image: {str(e)}")
        return {"error": f"Analysis failed: {str(e)}"}

@app.route("/api/analyze-image", methods=["POST"])
def analyze_image():
    import time
    bboxes = []  # Always define at the start
    try:
        print("[API] /api-analyze-image endpoint called.")
        start_time = time.perf_counter()
        if "image" not in request.files:
            print("[API] No 'image' file in request.")
            return jsonify({'status': 'error', 'error': 'No image file provided', 'items': [], 'objects': [], 'total_items': 0, 'total_value': 0}), 400
        print("[API] Image file received.")
        file = request.files["image"]
        file_bytes = file.read()
        print(f"[API] Read {len(file_bytes)} bytes from uploaded file.")
        np_arr = np.frombuffer(file_bytes, np.uint8)
        cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        print(f"[API] Decoded image: {'Success' if cv_image is not None else 'Failed'}.")
        if cv_image is None:
            print("[API] Image decoding failed. Returning error response.")
            return jsonify({'status': 'error', 'error': 'Invalid image data', 'items': [], 'objects': [], 'total_items': 0, 'total_value': 0}), 400
        
        # Run detection to get boxes
        print("[API] Running object detection.")
        yolo_start = time.perf_counter()
        boxes, masks = diagnostic_detection(cv_image, YOLO_MODEL)
        yolo_end = time.perf_counter()
        print(f"[API] Detection time: {yolo_end - yolo_start:.2f} seconds.")
        
        # Ensure bboxes is always defined before use
        if len(boxes) > 0:
            # Convert to PIL for processing
            scene_pil = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
            
            # Show detection results as popup
            if len(boxes) > 0:
                draw_detections_colored(cv_image, boxes, [], masks, "Object Detection Results", show_popup=True)
            
            # Create the final image with bounding boxes for Gemini
            final_image_with_boxes = draw_detections_colored(cv_image, boxes, [], masks, "For Gemini", show_popup=False)
            
            # Show the final image with all bounding boxes as a popup
            print("[DEBUG] Showing final image with all bounding boxes")
            cv2.imshow("Final Image with All Bounding Boxes", final_image_with_boxes)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            print("[DEBUG] Final image popup closed")
            
            # Convert to PIL for Gemini
            final_image_rgb = cv2.cvtColor(final_image_with_boxes, cv2.COLOR_BGR2RGB)
            final_image_pil = Image.fromarray(final_image_rgb)
            
            # Process detected objects for individual analysis
            crop_pils, codes, bboxes = [], [], []
            for i, box in enumerate(boxes):
                if len(box) == 5:
                    x1, y1, x2, y2, confidence = box
                elif len(box) == 4:
                    x1, y1, x2, y2 = box
                    confidence = 1.0
                # Ensure coordinates are within image bounds
                H, W = cv_image.shape[:2]
                x1 = max(0, int(x1))
                y1 = max(0, int(y1))
                x2 = min(W - 1, int(x2))
                y2 = min(H - 1, int(y2))
                # Crop the detected object
                crop = cv_image[y1:y2+1, x1:x2+1]
                if crop.size == 0:
                    continue
                # Convert to PIL for base64 conversion
                crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                crop_pil = Image.fromarray(crop_rgb)
                crop_pils.append(crop_pil)
                codes.append(str(i))
                bboxes.append((x1, y1, x2, y2))
        else:
            bboxes = []

        # Analyze with Gemini using the final image with bounding boxes
        if len(boxes) > 0:
            analysis_result = analyze_scene_with_gemini_final(final_image_pil, crop_pils, codes, bboxes, box_colors=[])
            # Use the original image (without bounding boxes) for cropping
            # Convert the original BGR image to RGB PIL
            original_image_pil = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
            # Create individual cropped images for each item using Gemini's bounding boxes
            code_to_image = {}
            print(f"[DEBUG] Creating cropped images for {len(analysis_result)} items")
            print(f"[DEBUG] Analysis result items: {[item.get('name', 'Unknown') for item in analysis_result]}")
            for i, item in enumerate(analysis_result):
                # Use YOLO bbox for cropping
                if i < len(bboxes):
                    x1, y1, x2, y2 = bboxes[i]
                    print(f"[DEBUG] YOLO bbox: {x1}, {y1}, {x2}, {y2}")
                    # Ensure coordinates are within image bounds
                    original_width, original_height = original_image_pil.size
                    x1 = max(0, min(x1, original_width - 1))
                    y1 = max(0, min(y1, original_height - 1))
                    x2 = max(x1 + 1, min(x2, original_width))
                    y2 = max(y1 + 1, min(y2, original_height))
                    crop = original_image_pil.crop((x1, y1, x2, y2))
                    cropped_base64 = pil_image_to_base64(crop)
                    code_to_image[item['code']] = cropped_base64
                    print(f"[DEBUG] Added YOLO-cropped image for {item['code']}")
                    # Add YOLO bbox to item for frontend
                    item['yolo_bbox'] = [x1, y1, x2, y2]
                else:
                    # Fallback to full image if no bbox
                    code_to_image[item['code']] = pil_image_to_base64(final_image_pil)
                    print(f"[DEBUG] Added full image for {item['code']} (no bbox)")
            
            print(f"[DEBUG] Created {len(code_to_image)} images")
            print(f"[DEBUG] Image codes: {list(code_to_image.keys())}")
            
            print(f"[API] Returning response with {len(analysis_result)} items.")
            total_time = time.perf_counter() - start_time
            print(f"[API] Total endpoint time: {total_time:.2f} seconds.")
            return jsonify(items=analysis_result, total_items=len(analysis_result), images=code_to_image)
        else:
            return jsonify({'error': 'No valid objects to analyze', 'items': [], 'total_items': 0, 'images': {}})
        
    except Exception as e:
        print(f"[API] Exception occurred: {e}")
        print(f"Error processing image: {e}")
        return jsonify({'error': str(e), 'status': 'error', 'items': []}), 500

@app.route('/api/analyze-multiple-images', methods=['POST'])
def analyze_multiple_images():
    try:
        data = request.get_json()
        if not data or 'images' not in data:
            return jsonify({'error': 'Missing images data', 'status': 'error', 'items': []}), 400
        images = data['images']
        if not isinstance(images, list):
            return jsonify({'error': 'Images must be a list', 'status': 'error', 'items': []}), 400
        
        print(f"[API] /api/analyze-multiple-images called with {len(images)} images.")
        
        # Optimize workers based on current CPU usage
        optimal_workers = optimize_workers()
        print(f"[API] Using {optimal_workers} worker processes for batch analysis.")
        
        all_items = []
        all_objects = []
        total_value = 0.0
        
        # Process images in parallel
        with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
            futures = []
            for image_data in images:
                future = executor.submit(analyze_single_image, image_data)
                futures.append(future)
            
            # Collect results
            for future in futures:
                result = future.result()
                if "error" not in result:
                    all_items.extend(result)
                    # Calculate total value
                    for item in result:
                        price = safe_price(item.get('price_usd', 0))
                        total_value += price
        
        print(f"[API] Batch processing complete. Found {len(all_items)} total items.")
        
        return jsonify({
            'status': 'success',
            'items': all_items,
            'objects': all_objects,
            'total_items': len(all_items),
            'total_value': total_value
        }), 200
    except Exception as e:
        print(f"Error processing multiple images: {e}")
        return jsonify({
            'error': str(e),
            'status': 'error',
            'items': []
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'}), 200

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True) 