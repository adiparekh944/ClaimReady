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
import multiprocessing as mp
from functools import partial
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import threading
import psutil
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from PIL import Image
import cv2
import numpy as np
import google.generativeai as genai
from ultralytics import YOLO

# Import LangChain verifier module
from langchain_verifier import verify_item_name_price, is_verifier_available

# Import required libraries for the full complex YOLO detection pipeline
import torch
# import open_clip  # Unused, remove
# from PIL import Image  # Duplicate, remove
# import torchvision.transforms as T  # Unused, remove
# import requests  # Unused, remove
import uuid
from threading import Lock
from multiprocessing import Pool

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# YOLO config from env
YOLO_MODEL_PATH = os.environ.get("YOLO_MODEL_PATH", "yolo11x-seg.pt")
YOLO_CONF = float(os.environ.get("YOLO_CONF", 0.25))
YOLO_IMGSZ = int(os.environ.get("YOLO_IMGSZ", 640))
CROP_PAD_FRAC = float(os.environ.get("CROP_PAD_FRAC", 0.05))

# === ULTRA-OPTIMIZED DETECTION PARAMETERS ===
SCALES = [640]  # Single scale for speed - most objects detected at 640
IOU_NMS = 0.7   # Slightly lower for speed
MASK_THRESH = 0.01
CONF_THRESH = 0.01  # Lower confidence threshold to maintain accuracy
CONF_THRESH_LOW = 0.005  # Very low confidence for additional tests
FEATURE_SIM_THRESH = 0.85  # Feature similarity threshold for duplicate detection
EDGE_THRESH = 30  # Edge detection threshold for box expansion

# Multiprocessing settings - use all available CPU cores
NUM_CORES = min(4, mp.cpu_count())
print(f"Detected {mp.cpu_count()} CPU cores, using {NUM_CORES} cores for processing")

# Performance optimization flags
USE_FAST_MERGING = True
SKIP_MASK_PROCESSING = False  # Skip mask processing for speed

# Display settings
SHOW_IMAGE_POPUP = False  # Toggle to show/hide image popup with bounding boxes

# ---------------- PEG-DEDUP (CLIP) HELPERS ----------------
_CLIP_MODEL = None
_CLIP_PRE = None
_CLIP_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Try to import open_clip, fallback if not available
try:
    import open_clip
    OPEN_CLIP_AVAILABLE = True
except ImportError:
    OPEN_CLIP_AVAILABLE = False
    print("Warning: open_clip not available. CLIP-based deduplication will be disabled.")

# Load YOLO model once
YOLO_MODEL = YOLO(YOLO_MODEL_PATH)

# Gemini config - hardcoded for local testing
GEMINI_API_KEY = "AIzaSyDVIppKcsZwVa3vkZWazztC9XY_-oZUufU"
GEMINI_MODEL = "gemini-2.5-flash"

# Set environment variables for LangChain
os.environ['GOOGLE_API_KEY'] = GEMINI_API_KEY
os.environ['GEMINI_API_KEY'] = GEMINI_API_KEY
genai.configure(api_key=GEMINI_API_KEY)
GEMINI_GEN_MODEL = genai.GenerativeModel(GEMINI_MODEL)

# LangChain verifier is now handled by the langchain_verifier module

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
                "required": ["code", "imageAttachment", "bbox", "name", "price_usd"]
            }
        }
    },
    "required": ["items"]
}

def generate_unique_code(existing):
    while True:
        code = str(random.randint(10000, 99999))
        if code not in existing:
            return code

# === Advanced YOLO Detection Functions (from yolo_oscf_v7.py) ===

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

def size_ratio(a, b):
    """Calculate size ratio between two boxes"""
    ax1, ay1, ax2, ay2, _ = a
    bx1, by1, bx2, by2, _ = b
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return min(area_a, area_b) / max(area_a, area_b) if max(area_a, area_b) > 0 else 0

def center_dist_frac(a, b):
    """Calculate center distance as fraction of image size"""
    ax1, ay1, ax2, ay2, _ = a
    bx1, by1, bx2, by2, _ = b
    center_a = ((ax1 + ax2) / 2, (ay1 + ay2) / 2)
    center_b = ((bx1 + bx2) / 2, (by1 + by2) / 2)
    dist = math.sqrt((center_a[0] - center_b[0])**2 + (center_a[1] - center_b[1])**2)
    # Normalize by average box size
    avg_size = ((ax2 - ax1) + (ay2 - ay1) + (bx2 - bx1) + (by2 - by1)) / 4
    return dist / max(avg_size, 1)

def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors"""
    import numpy as np
    a = np.array(a)
    b = np.array(b)
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0
    return dot_product / (norm_a * norm_b)

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

def expand_box(img_gray, box):
    x1, y1, x2, y2, score = box
    H, W = img_gray.shape
    gx1, gy1, gx2, gy2 = int(x1), int(y1), int(x2), int(y2)
    max_grow = int(max(gx2-gx1, gy2-gy1) * 0.25)
    for _ in range(max_grow):
        grew = False
        for side in [('l', (gy1,gy2, gx1-1, gx1)),
                     ('r', (gy1,gy2, gx2+1, gx2+2)),
                     ('u', (gy1-1,gy1, gx1,gx2)),
                     ('d', (gy2+1,gy2+2, gx1,gx2))]:
            sy1, sy2, sx1, sx2 = side[1]
            if sy1<0 or sy2>H or sx1<0 or sx2>W:
                continue
            band = img_gray[sy1:sy2, sx1:sx2]
            if band.size and band.std() < EDGE_THRESH:
                if side[0]=='l': gx1 -= 1
                if side[0]=='r': gx2 += 1
                if side[0]=='u': gy1 -= 1
                if side[0]=='d': gy2 += 1
                grew = True
        if not grew:
            break
    return [gx1, gy1, gx2, gy2, score]





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

def combine_similar_boxes(boxes, size_location_thresh=0.95):
    """
    Combine boxes that are 95% the same size and location.
    Returns merged boxes with highest confidence score.
    """
    if len(boxes) == 0:
        return boxes
    
    # Convert to numpy array if needed
    boxes = np.array(boxes, dtype=np.float32)
    
    # Sort by confidence (descending)
    sorted_indices = np.argsort(-boxes[:, 4])
    boxes_sorted = boxes[sorted_indices]
    
    used = np.zeros(len(boxes_sorted), dtype=bool)
    merged_boxes = []
    
    for i in range(len(boxes_sorted)):
        if used[i]:
            continue
        
        current_box = boxes_sorted[i]
        merged_boxes.append(current_box)
        used[i] = True
        
        for j in range(i + 1, len(boxes_sorted)):
            if used[j]:
                continue
            
            other_box = boxes_sorted[j]
            
            # Calculate similarity metrics
            size_ratio_val = size_ratio(current_box, other_box)
            center_dist = center_dist_frac(current_box, other_box)
            
            # Combined similarity score
            combined_similarity = (size_ratio_val + (1 - center_dist)) / 2
            
            if combined_similarity >= size_location_thresh:
                used[j] = True
    
    result = np.array(merged_boxes, dtype=np.float32)
    return result

def to_grayscale_3ch(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

def edge_overlay_canny(img, alpha=0.5):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    edges_col = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    overlay = cv2.addWeighted(img, 1 - alpha, edges_col, alpha, 0)
    return overlay

def extract_backbone_features(model, img_bgr, boxes):
    """
    Extract backbone features for each bounding box.
    Returns feature vectors for each box.
    """
    if len(boxes) == 0:
        return np.zeros((0, 512), dtype=np.float32)  # Default feature dimension
    
    # Get the backbone features from the model
    results = model(img_bgr, verbose=False)
    result = results[0]
    
    # Access backbone features (this may need adjustment based on YOLO version)
    if hasattr(result, 'boxes') and len(result.boxes) > 0:
        # Try to get features from the model's internal state
        # This is a simplified approach - you may need to modify based on your YOLO version
        features = []
        for box in boxes:
            # For now, create a simple feature vector based on box properties
            x1, y1, x2, y2, conf = box
            w, h = x2 - x1, y2 - y1
            area = w * h
            aspect_ratio = w / (h + 1e-6)
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            
            # Create a simple feature vector (you can enhance this)
            feature = np.array([
                conf, area, aspect_ratio, center_x, center_y,
                w, h, x1, y1, x2, y2
            ], dtype=np.float32)
            
            # Pad to 512 dimensions (or use PCA to reduce if needed)
            if len(feature) < 512:
                feature = np.pad(feature, (0, 512 - len(feature)), 'constant')
            else:
                feature = feature[:512]
            
            features.append(feature)
        
        return np.array(features, dtype=np.float32)
    else:
        # Fallback: create simple features
        features = []
        for box in boxes:
            x1, y1, x2, y2, conf = box
            w, h = x2 - x1, y2 - y1
            area = w * h
            aspect_ratio = w / (h + 1e-6)
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            
            feature = np.array([
                conf, area, aspect_ratio, center_x, center_y,
                w, h, x1, y1, x2, y2
            ], dtype=np.float32)
            
            if len(feature) < 512:
                feature = np.pad(feature, (0, 512 - len(feature)), 'constant')
            else:
                feature = feature[:512]
            
            features.append(feature)
        
        return np.array(features, dtype=np.float32)

def is_duplicate_detection(box1, box2, mask1, mask2, features1, features2, mask_iou_thresh=0.5, feature_thresh=0.85):
    """
    Check if two detections are duplicates using mask IoU and feature similarity.
    More accurate than box IoU since masks show actual object boundaries.
    """
    # Compute mask IoU
    if mask1 is None or mask2 is None:
        # Fallback to box IoU if masks are not available
        x1_1, y1_1, x2_1, y2_1, _ = box1
        x1_2, y1_2, x2_2, y2_2, _ = box2
        
        ix1 = max(x1_1, x1_2)
        iy1 = max(y1_1, y1_2)
        ix2 = min(x2_1, x2_2)
        iy2 = min(y2_1, y2_2)
        
        if ix2 <= ix1 or iy2 <= iy1:
            mask_iou = 0.0
        else:
            inter = (ix2 - ix1) * (iy2 - iy1)
            area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
            area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
            union = area1 + area2 - inter
            mask_iou = inter / (union + 1e-8)
    else:
        # Ensure masks are the same size
        if mask1.shape != mask2.shape:
            mask1 = cv2.resize(mask1.astype(np.uint8), (mask2.shape[1], mask2.shape[0]), interpolation=cv2.INTER_NEAREST)
        
        # Compute mask IoU
        intersection = np.logical_and(mask1 > 0, mask2 > 0).sum()
        union = np.logical_or(mask1 > 0, mask2 > 0).sum()
        mask_iou = intersection / (union + 1e-8)
    
    # Compute feature similarity
    feature_sim = cosine_similarity(features1, features2)
    
    # Check if it's a duplicate using mask IoU
    return mask_iou > mask_iou_thresh and feature_sim > feature_thresh

def run_detection_test(img_bgr, model, test_name, transform_func=None, conf_thresh=None):
    """
    Run a single detection test with optional image transformation.
    Returns list of boxes and masks in original image coordinates.
    """
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
            # If transformation was applied, map coordinates back
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
        # Collect masks (if available)
        if hasattr(res[0], "masks") and res[0].masks is not None and res[0].masks.data is not None:
            m = res[0].masks.data.cpu().numpy()
            m = (m > MASK_THRESH).astype(np.uint8)
            masks.extend(m)
    return boxes, masks

# ---------------- PEG-DEDUP (CLIP) HELPERS ----------------

def get_clip_model():
    global _CLIP_MODEL, _CLIP_PRE
    if not OPEN_CLIP_AVAILABLE:
        raise RuntimeError("open_clip not available")
    if _CLIP_MODEL is None:
        model, _, preprocess = open_clip.create_model_and_transforms(
            'ViT-B-32', pretrained='openai'
        )
        model.eval().to(_CLIP_DEVICE)
        _CLIP_MODEL = model
        _CLIP_PRE = preprocess
    return _CLIP_MODEL, _CLIP_PRE

def embed_boxes_clip(img_bgr, boxes):
    """
    Return NxD normalized CLIP embeddings for each box crop.
    """
    if len(boxes) == 0:
        return np.zeros((0,512), np.float32)

    model, preprocess = get_clip_model()

    crops = []
    H,W = img_bgr.shape[:2]
    for b in boxes:
        x1,y1,x2,y2,_ = map(int,b)
        x1 = max(0,x1); y1 = max(0,y1); x2 = min(W-1,x2); y2 = min(H-1,y2)
        crop = img_bgr[y1:y2+1, x1:x2+1]
        if crop.size == 0:
            crop = np.zeros((1,1,3), np.uint8)
        pil = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
        crops.append(preprocess(pil))

    batch = torch.stack(crops).to(_CLIP_DEVICE)
    with torch.no_grad():
        feats = _CLIP_MODEL.encode_image(batch)
    feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats.cpu().numpy()  # NxD

def contain_frac_smaller(a, b):
    # inter / smaller area
    ax1,ay1,ax2,ay2,_ = a; bx1,by1,bx2,by2,_ = b
    ix1,iy1 = max(ax1,bx1), max(ay1,by1)
    ix2,iy2 = min(ax2,bx2), min(ay2,by2)
    iw = max(0, ix2-ix1+1); ih = max(0, iy2-iy1+1)
    inter = iw*ih
    areaA = (ax2-ax1+1)*(ay2-ay1+1)
    areaB = (bx2-bx1+1)*(by2-by1+1)
    return inter / float(min(areaA, areaB)+1e-6)

def iou_boxes(a,b):
    ax1,ay1,ax2,ay2,_ = a; bx1,by1,bx2,by2,_ = b
    ix1,iy1 = max(ax1,bx1), max(ay1,by1)
    ix2,iy2 = min(ax2,bx2), min(ay2,by2)
    iw = max(0, ix2-ix1+1); ih = max(0, iy2-iy1+1)
    inter = iw*ih
    if inter == 0: return 0.0
    areaA = (ax2-ax1+1)*(ay2-ay1+1)
    areaB = (bx2-bx1+1)*(by2-by1+1)
    return inter / float(areaA+areaB-inter+1e-6)

def peg_dedup(boxes, img_bgr,
              contain_t=0.7,
              iou_t=0.6,
              center_t=0.5,
              cos_t=0.8,
              child_keep_ratio=0.4,
              union_similar=True):
    """
    Pretrained Embedding + Geometry dedup.
    Returns new boxes (Nx5).
    """

    if len(boxes) == 0:
        return boxes

    # Embed once
    embs = embed_boxes_clip(img_bgr, boxes)  # NxD
    N = len(boxes)
    keep = []
    used = np.zeros(N, bool)

    # Score sort (descending)
    order = np.argsort(-boxes[:,4])

    for i in order:
        if used[i]:
            continue
        bi = boxes[i].copy()
        used[i] = True

        # start cluster with i
        cluster = [bi]
        cluster_scores = [bi[4]]
        cluster_idx = [i]

        for j in order:
            if used[j]: 
                continue
            bj = boxes[j]
            cfrac = contain_frac_smaller(bi, bj)
            iouv  = iou_boxes(bi, bj)
            if cfrac < contain_t and iouv < iou_t:
                continue

            cdist = center_dist_frac(bi, bj)
            if cdist > center_t:
                continue

            cos = float((embs[i] @ embs[j].T))  # cosine similarity
            if cos < cos_t:
                continue

            # potential duplicate / part
            sr = size_ratio(bi, bj)
            if sr < child_keep_ratio:
                # treat as distinct (child nested) — keep untouched
                continue

            # merge
            cluster.append(bj.copy())
            cluster_scores.append(bj[4])
            cluster_idx.append(j)
            used[j] = True

        if len(cluster) == 1:
            keep.append(bi)
        else:
            if union_similar:
                xs1 = min(c[0] for c in cluster)
                ys1 = min(c[1] for c in cluster)
                xs2 = max(c[2] for c in cluster)
                ys2 = max(c[3] for c in cluster)
                sc  = max(cluster_scores)
                keep.append([xs1,ys1,xs2,ys2,sc])
            else:
                # keep best scoring only
                keep.append(bi)

    return np.array(keep, dtype=np.float32)

def yolo_multi_test_detection(img_bgr, model):
    """
    Run detection with original image first, then additional tests with low confidence.
    Use backbone features to determine if new detections are duplicates.
    """
    
    # Stage 1: Original detection with normal confidence
    original_boxes, original_masks = run_detection_test(img_bgr, model, "Original (conf=0.25)", conf_thresh=CONF_THRESH)
    
    if len(original_boxes) == 0:
        return []
    
    # Extract features for original detections
    original_features = extract_backbone_features(model, img_bgr, original_boxes)
    
    # Stage 2: Additional tests with low confidence
    additional_boxes = []
    additional_masks = []
    
    # Test 1: Grayscale 3-channel with low confidence
    grayscale_boxes, grayscale_masks = run_detection_test(img_bgr, model, "Grayscale (conf=0.05)", 
                                                         to_grayscale_3ch, conf_thresh=0.05)
    additional_boxes.extend(grayscale_boxes)
    additional_masks.extend(grayscale_masks)
    
    # Test 2: Edge-overlay with low confidence
    edge_boxes, edge_masks = run_detection_test(img_bgr, model, "Edge-overlay (conf=0.01)", 
                                               edge_overlay_canny, conf_thresh=CONF_THRESH_LOW)
    additional_boxes.extend(edge_boxes)
    additional_masks.extend(edge_masks)
    
    if len(additional_boxes) == 0:
        return original_boxes
    
    # Extract features for additional detections
    additional_features = extract_backbone_features(model, img_bgr, additional_boxes)
    
    # Filter additional detections to only keep non-duplicates
    filtered_additional = []
    filtered_additional_masks = []
    used_additional = set()  # Track which additional detections we've already processed
    
    for i, (add_box, add_feature) in enumerate(zip(additional_boxes, additional_features)):
        if i in used_additional:
            continue
            
        is_duplicate = False
        
        # Check against all original detections
        for j, (orig_box, orig_feature) in enumerate(zip(original_boxes, original_features)):
            orig_mask = original_masks[j] if j < len(original_masks) else None
            add_mask = additional_masks[i] if i < len(additional_masks) else None
            if is_duplicate_detection(add_box, orig_box, add_mask, orig_mask, add_feature, orig_feature, 
                                   mask_iou_thresh=0.5, feature_thresh=FEATURE_SIM_THRESH):
                is_duplicate = True
                break
        
        # Check against other additional detections (that we haven't processed yet)
        if not is_duplicate:
            for j in range(i+1, len(additional_boxes)):
                if j in used_additional:
                    continue
                add_mask_i = additional_masks[i] if i < len(additional_masks) else None
                add_mask_j = additional_masks[j] if j < len(additional_masks) else None
                if is_duplicate_detection(add_box, additional_boxes[j], add_mask_i, add_mask_j, 
                                       add_feature, additional_features[j], 
                                       mask_iou_thresh=0.5, feature_thresh=FEATURE_SIM_THRESH):
                    is_duplicate = True
                    used_additional.add(j)  # Mark the duplicate as used
                    break
        
        if not is_duplicate:
            filtered_additional.append(add_box)
            if i < len(additional_masks):
                filtered_additional_masks.append(additional_masks[i])
    
    # Combine original and filtered additional detections
    final_boxes = original_boxes + filtered_additional
    final_masks = original_masks + filtered_additional_masks
    
    # Step 4: Combine boxes that are 95% the same size and location
    if len(final_boxes) > 0:
        final_boxes = combine_similar_boxes(final_boxes, size_location_thresh=0.95)
    
    return final_boxes

# Remove all cv2.imshow, cv2.waitKey, and cv2.destroyAllWindows popups

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

def detect_fast(img_bgr, model):
    """
    Detection pipeline that stops at 95% box merging.
    """
    boxes, masks = diagnostic_detection(img_bgr, model)
    return boxes

def pad_and_crop(img, box, pad_pct):
    h, w = img.shape[:2]
    x1, y1, x2, y2 = box
    bw, bh = x2 - x1, y2 - y1
    pad_x = int(bw * pad_pct)
    pad_y = int(bh * pad_pct)
    nx1 = max(0, x1 - pad_x)
    ny1 = max(0, y1 - pad_y)
    nx2 = min(w, x2 + pad_x)
    ny2 = min(h, y2 + pad_y)
    return img[ny1:ny2, nx1:nx2]

def pil_image_to_base64(pil_img):
    buffer = io.BytesIO()
    pil_img.save(buffer, format="JPEG")
    buffer.seek(0)
    base64_str = base64.b64encode(buffer.read()).decode('utf-8')
    data_url = f"data:image/jpeg;base64,{base64_str}"
    return data_url

def build_gemini_contents(scene_pil, crops, codes, instructions):
    """
    Fallback: build a flat contents list of alternating text + PIL images.
    Order matters: [instructions, full_scene, CODE:text, crop_img, CODE:text, crop_img, ...]
    Gemini associates each CODE with the immediately following image.
    """
    assert len(codes) == len(crops), "Mismatch between codes and crops!"
    # Ensure all images are RGB PIL
    if scene_pil.mode != "RGB":
        scene_pil = scene_pil.convert("RGB")
    contents = [instructions, scene_pil]
    for code, crop in zip(codes, crops):
        if crop.mode != "RGB":
            crop = crop.convert("RGB")
        contents.append(f"CODE:{code}")
        contents.append(crop)
    return contents

def _resp_text(resp):
    t = getattr(resp, "text", None)
    if t:
        return t
    try:
        return resp.candidates[0].content.parts[0].text
    except Exception:
        return ""

# === SAHI imports and globals ===
try:
    from sahi import AutoDetectionModel
    from sahi.predict import get_sliced_prediction
    _SAHI_AVAILABLE = True
except Exception:
    _SAHI_AVAILABLE = False

_SAHI_MODEL = None

def _get_sahi_model():
    global _SAHI_MODEL
    if _SAHI_MODEL is None:
        if not _SAHI_AVAILABLE:
            raise RuntimeError("SAHI not installed")
        device = os.getenv("SAHI_DEVICE", "")
        if device == "auto":
            try:
                import torch
                device = "cuda:0" if torch.cuda.is_available() else "cpu"
            except Exception:
                device = "cpu"
        _SAHI_MODEL = AutoDetectionModel.from_pretrained(
            model_type="ultralytics",
            model_path=YOLO_MODEL_PATH,
            confidence_threshold=YOLO_CONF,
            device=device,
        )
    return _SAHI_MODEL

def detect_with_sahi(cv_bgr):
    import logging
    cv_rgb = cv2.cvtColor(cv_bgr, cv2.COLOR_BGR2RGB)
    det_model = _get_sahi_model()
    sh = int(os.getenv("SAHI_SLICE_H", 512))
    sw = int(os.getenv("SAHI_SLICE_W", 512))
    oh = float(os.getenv("SAHI_OVERLAP_H", 0.25))
    ow = float(os.getenv("SAHI_OVERLAP_W", 0.25))
    miou = float(os.getenv("SAHI_MERGE_IOU", 0.5))
    logging.info(f"SAHI slicing: slice_h={sh}, slice_w={sw}, overlap_h={oh}, overlap_w={ow}, merge_iou={miou}")
    result = get_sliced_prediction(
        image=cv_rgb,
        detection_model=det_model,
        slice_height=sh,
        slice_width=sw,
        overlap_height_ratio=oh,
        overlap_width_ratio=ow,
        postprocess_type="nms",
        postprocess_match_metric="IOU",
        postprocess_match_threshold=miou,
    )
    n_tiles = getattr(result, '_sliced_prediction_images_length', None)
    if n_tiles is None and hasattr(result, 'sliced_prediction_images'):  # fallback
        n_tiles = len(result.sliced_prediction_images)
    logging.info(f"SAHI processed {n_tiles} tiles" if n_tiles is not None else "SAHI tile count unavailable")
    boxes = []
    for op in result.object_prediction_list:
        x1, y1, x2, y2 = op.bbox.to_xyxy()
        boxes.append((int(x1), int(y1), int(x2), int(y2)))
    return boxes

def analyze_single_image(image_data):
    """
    Analyze a single image using the FULL COMPLEX YOLO detection pipeline.
    """
    try:
        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img_bgr is None:
            return {"error": "Failed to decode image", "items": [], "objects": []}
        
        # Use the ACTUAL FULL COMPLEX YOLO detection pipeline from yolo_oscf_v7.py
        boxes = detect_fast(img_bgr, YOLO_MODEL)
        
        if not boxes:
            return {"error": "No objects detected", "items": [], "objects": []}
        
        # Process detected objects
        crop_pils, codes, bboxes = [], [], []
        for i, box in enumerate(boxes):
            x1, y1, x2, y2, confidence = box
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
        # Analyze with Gemini
        if crop_pils:
            # Use the original PIL image for the scene
            scene_pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
            analysis_result = analyze_scene_with_gemini(scene_pil, crop_pils, codes, bboxes)
            
            # Generate code_to_image mapping for frontend
            code_to_image = {}
            for i, crop_pil in enumerate(crop_pils):
                code_to_image[codes[i]] = pil_image_to_base64(crop_pil)
            
            # Generate crop images for scene-based items
            for item in analysis_result:
                if item.get('imageAttachment') == 'scene':
                    bbox = item.get('bbox', [])
                    if len(bbox) == 4:
                        x1, y1, x2, y2 = bbox
                        # Crop the scene image using the bounding box
                        scene_crop = scene_pil.crop((x1, y1, x2, y2))
                        # Resize the crop to match other crops
                        scene_crop_resized = resize_image_maintain_aspect_ratio(scene_crop, 384)
                        # Add to code_to_image with the scene code
                        scene_code = item.get('code', 'scene')
                        code_to_image[scene_code] = pil_image_to_base64(scene_crop_resized)
            
            return {"items": analysis_result, "objects": boxes, "images": code_to_image}
        else:
            return {"error": "No valid objects to analyze", "items": [], "objects": [], "images": {}}
            
    except Exception as e:
        logger.error(f"Error in analyze_single_image: {str(e)}")
        return {"error": f"Analysis failed: {str(e)}", "items": [], "objects": []}

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

# verify_item_name_price function is now in langchain_verifier module

def analyze_scene_with_gemini(scene_pil, crop_pils, codes, bboxes, instructions_override=None, temperature_override=None):
    import google.generativeai as genai
    
    # Resize full image to 768px longest edge
    scene_pil_resized = resize_image_maintain_aspect_ratio(scene_pil, 768)
    
    # Resize all segments to 384px longest edge
    crop_pils_resized = [resize_image_maintain_aspect_ratio(crop, 384) for crop in crop_pils]
    
    instructions = """
You are an insurance-claims assistant analyzing room images. You receive:
- A full-room image titled 'scene'
- Segmented images (crop0, crop1, etc.) with CODE:<id> and BBOX:[x1,y1,x2,y2]

CRITICAL REQUIREMENTS:
- You MUST use the provided crop codes (crop0, crop1, etc.) and their corresponding CODE values for segmented items.
- Each segment may contain multiple individual items. Identify and separate each unique item.
- If a segment contains multiple items, create separate JSON entries for each item using the same segment code but with different bounding box coordinates.
- Use context from the full scene to identify items, even if segments are unclear.
- Include every unique item found - make best guesses if uncertain.
- DO NOT add duplicate items - base of spatial reasoning.
- For each item, either choose the segment that shows the item most centered and fills up the most of the frame.
- If you detect an item in the full scene that is not represented by any segment, create a JSON entry with "imageAttachment": "scene" and provide bounding box coordinates for that item.
- When estimating price, make sure to esitmate from an insurance perspective and factor emotional value into the price.

For each individual item, output:
    {
    "code": "<exact_CODE_value_from_segment>",
    "imageAttachment": "<exact_crop_name>",
    "bbox": [x1, y1, x2, y2],
    "name": "<object name>",
    "category": "<e.g. Furniture>",
    "price_usd": <number>,
    "description": "<brief>"
  },
]
"""
    
    contents = [instructions, "scene", scene_pil_resized]
    for i, crop in enumerate(crop_pils_resized):
        x1, y1, x2, y2 = bboxes[i]
        contents.append(f"CODE:{codes[i]} BBOX:[{x1},{y1},{x2},{y2}]")
        contents.append(crop)
    
    try:
        response = GEMINI_GEN_MODEL.generate_content(
            contents,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=1.0
            )
        )
        
        # Extract items from the structured response
        raw = response.text
        # Remove Markdown code block if present
        if raw.strip().startswith('```'):
            lines = raw.strip().splitlines()
            if lines[0].startswith('```') and lines[-1].startswith('```'):
                raw = '\n'.join(lines[1:-1])
        
        import json
        import ast
        # Try to parse as JSON
        try:
            parsed = json.loads(raw)
            items = parsed.get('items', []) if isinstance(parsed, dict) else parsed
        except json.JSONDecodeError:
            # If it's a quoted string, strip quotes and try again
            if raw.startswith('"') and raw.endswith('"'):
                try:
                    parsed = json.loads(raw[1:-1])
                    items = parsed.get('items', []) if isinstance(parsed, dict) else parsed
                except Exception:
                    items = []
            else:
                try:
                    parsed = ast.literal_eval(raw)
                    items = parsed.get('items', []) if isinstance(parsed, dict) else parsed
                except Exception as e:
                    logger.error(f"Failed to parse Gemini response: {e}")
                    items = []
        
        # Map imageAttachment back to actual images and codes
        mapped_items = []
        print(f"\nDEBUG: Raw Gemini response: {raw}")
        print(f"DEBUG: Parsed items: {items}")
        
        # Process all items from Gemini response
        for item in items:
            image_attachment = item.get('imageAttachment', '')
            item_code = item.get('code', '')
            print(f"DEBUG: Processing item with imageAttachment: {image_attachment}, code: {item_code}")
            
            # Handle crop-based items
            if image_attachment.startswith('crop'):
                try:
                    idx = int(image_attachment.replace('crop', ''))
                    print(f"DEBUG: Extracted index: {idx}, codes: {codes}")
                    if idx < len(crop_pils_resized):
                        # Update the code to match the original code for this index
                        item['code'] = codes[idx]
                        mapped_items.append(item)
                        print(f"DEBUG: Successfully mapped {image_attachment} to code {codes[idx]}")
                    else:
                        print(f"DEBUG: Index {idx} out of range for {len(crop_pils_resized)} crops")
                except ValueError:
                    logger.warning(f"Invalid imageAttachment format: {image_attachment}")
                    continue
            
            # Handle scene-based items (items identified from full scene)
            elif image_attachment == 'scene' or item_code == 'scene':
                # Generate a unique code for scene-based items
                scene_code = f"scene_{len(mapped_items)}"
                item['code'] = scene_code
                item['imageAttachment'] = 'scene'
                mapped_items.append(item)
                print(f"DEBUG: Added scene-based item with code {scene_code}")
            
            # Handle items with direct code mapping
            elif item_code in codes:
                mapped_items.append(item)
                print(f"DEBUG: Added item with direct code mapping: {item_code}")
            
            else:
                logger.warning(f"Unexpected imageAttachment/code format: {image_attachment}/{item_code}")
        
        # Fallback: if no items were mapped, try order-based mapping
        if not mapped_items and len(items) == len(crop_pils_resized):
            print("DEBUG: Using fallback order-based mapping")
            for i, item in enumerate(items):
                if i < len(codes):
                    item['code'] = codes[i]
                    item['imageAttachment'] = f"crop{i}"  # Add the missing field
                    item['bbox'] = list(bboxes[i])        # Add bbox if missing
                    mapped_items.append(item)
                    print(f"DEBUG: Fallback mapped item {i} to code {codes[i]}")
        
        print(f"DEBUG: Final mapped_items: {mapped_items}")
        
        # Show Gemini's classification results (no popups)
        print("\n" + "="*80)
        print("GEMINI CLASSIFICATION RESULTS")
        print("="*80)
        
        for i, (crop_pil, code) in enumerate(zip(crop_pils_resized, codes)):
            # Find Gemini's classification for this code
            gemini_item = None
            for item in mapped_items:
                if str(item.get('code', '')) == str(code):
                    gemini_item = item
                    break
            
            # Display the segmentation image info
            print(f"\n--- SEGMENTATION {code} ---")
            print(f"Image size: {crop_pil.size}")
            
            # Remove all popups for each segment
            # (No cv2.imshow, cv2.waitKey, or cv2.destroyAllWindows)
            
            # Show Gemini's classification
            if gemini_item:
                print(f"Gemini Classification:")
                print(f"  Name: {gemini_item.get('name', 'Unknown')}")
                print(f"  Category: {gemini_item.get('category', 'Unknown')}")
                price = gemini_item.get('price_usd')
                print(f"  Price: ${float(price) if price is not None else 0.0:.2f}")
                print(f"  Description: {gemini_item.get('description', 'No description')}")
                print(f"  ImageAttachment: {gemini_item.get('imageAttachment', 'Unknown')}")
                print(f"  BBox: {gemini_item.get('bbox', 'Unknown')}")
            else:
                print("Gemini Classification: NOT FOUND in response")
            
            print("-" * 40)
        
        print("="*80)
        print("END OF CLASSIFICATION RESULTS")
        print("="*80 + "\n")
        
        return mapped_items
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise

# Add dynamic padding function

def dynamic_padding(x1, y1, x2, y2, img_w, img_h, min_pad=0.01, max_pad=1.0):
    seg_area = (x2 - x1) * (y2 - y1)
    img_area = img_w * img_h
    r = seg_area / img_area
    # Log drop-off: more sensitive to medium sizes
    pad_frac = max_pad - (max_pad - min_pad) * np.log10(1 + 9 * r)
    return pad_frac

def get_clamped_padded_box(x1, y1, x2, y2, pad_x, pad_y, img_w, img_h):
    # Calculate padded box
    px1 = x1 - pad_x
    py1 = y1 - pad_y
    px2 = x2 + pad_x
    py2 = y2 + pad_y

    # Clamp to image bounds
    px1 = max(0, px1)
    py1 = max(0, py1)
    px2 = min(img_w, px2)
    py2 = min(img_h, py2)

    # Ensure integer coordinates
    px1, py1, px2, py2 = map(int, [px1, py1, px2, py2])

    # Ensure valid crop (at least 1x1)
    if px2 <= px1 or py2 <= py1:
        return None

    return px1, py1, px2, py2

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

# In-memory progress tracking (for demo; not for production)
# progress_dict = {}
# progress_lock = Lock()

@app.route("/api/analyze-image", methods=["POST"])
def analyze_image():
    import time
    try:
        print("=" * 80)
        print("🚀 [API] /api/analyze-image endpoint called")
        print(f"🕐 Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 Request method: {request.method}")
        print(f"🔗 Request URL: {request.url}")
        print(f"📋 Request headers: {dict(request.headers)}")
        print(f"📊 Request content type: {request.content_type}")
        print(f"📏 Request content length: {request.content_length}")
        print("=" * 80)
        start_time = time.perf_counter()
        if "image" not in request.files:
            print("❌ [API] No 'image' file in request.")
            print(f"📋 Available files in request: {list(request.files.keys())}")
            return jsonify({'status': 'error', 'error': 'No image file provided', 'items': [], 'objects': [], 'total_items': 0, 'total_value': 0}), 400
        
        print("✅ [API] Image file found in request")
        file = request.files["image"]
        print(f"📁 File details: filename='{file.filename}', content_type='{file.content_type}'")
        
        file_bytes = file.read()
        print(f"📊 [API] Read {len(file_bytes)} bytes from uploaded file")
        print(f"📊 File size: {len(file_bytes) / 1024:.2f} KB")
        np_arr = np.frombuffer(file_bytes, np.uint8)
        cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        print(f"[API] Decoded image: {'Success' if cv_image is not None else 'Failed'}.")
        if cv_image is None:
            print("[API] Image decoding failed. Returning error response.")
            return jsonify({'status': 'error', 'error': 'Invalid image data', 'items': [], 'objects': [], 'total_items': 0, 'total_value': 0}), 400
        scene_pil = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
        print("[API] Running YOLO detection on image.")
        yolo_start = time.perf_counter()
        detected_boxes = detect_fast(cv_image, YOLO_MODEL)
        yolo_end = time.perf_counter()
        print(f"[API] YOLO detection returned {len(detected_boxes)} boxes.")
        print(f"[API] YOLO processing time: {yolo_end - yolo_start:.2f} seconds.")
        crop_pils, codes, bboxes = [], [], []
        img_h, img_w = cv_image.shape[:2]
        for i, box in enumerate(detected_boxes):
            x1, y1, x2, y2, conf = map(int, box)
            pad_frac = dynamic_padding(x1, y1, x2, y2, img_w, img_h)
            bw, bh = x2 - x1, y2 - y1
            pad_x = int(bw * pad_frac)
            pad_y = int(bh * pad_frac)
            crop_coords = get_clamped_padded_box(x1, y1, x2, y2, pad_x, pad_y, img_w, img_h)
            if crop_coords is None:
                print(f"[API] Skipping invalid crop for box {i}.")
                continue
            nx1, ny1, nx2, ny2 = crop_coords
            crop = cv_image[ny1:ny2, nx1:nx2]
            crop_pil = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            crop_pils.append(crop_pil)
            codes.append(str(i))
            bboxes.append((x1, y1, x2, y2))
            print(f"[API] Prepared crop {i}: box=({x1},{y1},{x2},{y2}), conf={conf}")
        print(f"[API] Passing {len(crop_pils)} crops to Gemini analysis.")
        gemini_start = time.perf_counter()
        items = analyze_scene_with_gemini(scene_pil, crop_pils, codes, bboxes)
        gemini_end = time.perf_counter()
        print(f"[API] Time taken for Gemini analysis: {gemini_end - gemini_start:.2f} seconds.")
        
        # Run verifier on each item (with fallback if LangChain not available)
        print(f"[API] Running verifier on {len(items)} items.")
        verifier_start = time.perf_counter()
        
        # Convert original image to bytes for verifier
        img_bytes = pil_to_bytes(scene_pil)
        
        # Verify each item
        for i, item in enumerate(items):
            print(f"[API] Verifying item {i+1}/{len(items)}: {item.get('name', 'unknown')}")
            item = verify_item_name_price(item, img_bytes)
            items[i] = item  # Update the item in the list
        
        verifier_end = time.perf_counter()
        print(f"[API] Time taken for verifier analysis: {verifier_end - verifier_start:.2f} seconds.")
        code_to_image = {str(i): pil_image_to_base64(crop_pils[i]) for i in range(len(crop_pils))}
        
        # Generate crop images for scene-based items
        for item in items:
            if item.get('imageAttachment') == 'scene':
                bbox = item.get('bbox', [])
                if len(bbox) == 4:
                    x1, y1, x2, y2 = bbox
                    # Crop the scene image using the bounding box
                    scene_crop = scene_pil.crop((x1, y1, x2, y2))
                    # Resize the crop to match other crops
                    scene_crop_resized = resize_image_maintain_aspect_ratio(scene_crop, 384)
                    # Add to code_to_image with the scene code
                    scene_code = item.get('code', 'scene')
                    code_to_image[scene_code] = pil_image_to_base64(scene_crop_resized)
                    print(f"[API] Added scene-based image for code: {scene_code}")
        
        print(f"[API] Final code_to_image keys: {list(code_to_image.keys())}")
        print(f"[API] Returning response with {len(items)} items.")
        total_time = time.perf_counter() - start_time
        print(f"[API] Total endpoint time: {total_time:.2f} seconds.")
        
        # Show the final image with bounding boxes as a pop-up (if enabled)
        if SHOW_IMAGE_POPUP:
            result_img = draw_detections(cv_image, detected_boxes)
            show_image_popup(result_img, window_name="Final Bounding Boxes")
        
        return jsonify(items=items, total_items=len(items), images=code_to_image)
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
        all_items = []
        all_objects = []
        total_value = 0.0
        print(f"[API] /api/analyze-multiple-images called with {len(images)} images.")
        num_workers = min(mp.cpu_count(), 4)  # Limit to 4 or number of CPUs
        print(f"[API] Using {num_workers} worker processes for batch analysis.")
        with Pool(processes=num_workers) as pool:
            results = pool.map(analyze_single_image, images)
        print(f"[API] Batch processing complete.")
        all_images = {}
        for result in results:
            items = result.get('items', []) if isinstance(result, dict) else result
            objects = result.get('objects', []) if isinstance(result, dict) else []
            images = result.get('images', {}) if isinstance(result, dict) else {}
            
            for item in items:
                item['price_usd'] = safe_price(item.get('price_usd', item.get('price', 0)))
            all_items.extend(items)
            
            # Merge images from this result into all_images
            for code, image in images.items():
                all_images[code] = image
            
            # Convert NumPy objects to native Python types for JSON serialization
            for obj in objects:
                if isinstance(obj, np.ndarray):
                    all_objects.append(obj.tolist())
                else:
                    all_objects.append(obj)
            total_value += sum(float(item.get('price_usd', 0)) for item in items)
        
        return jsonify({
            'status': 'success',
            'items': to_python_type(all_items),
            'objects': to_python_type(all_objects),
            'images': all_images,
            'total_items': len(all_items),
            'total_value': float(total_value)
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
    import time
    print("=" * 50)
    print("🏥 [HEALTH] Health check endpoint called")
    print(f"🕐 Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Request method: {request.method}")
    print(f"🔗 Request URL: {request.url}")
    print(f"📋 Request headers: {dict(request.headers)}")
    print("✅ [HEALTH] Returning OK status")
    print("=" * 50)
    return jsonify({'status': 'ok'}), 200

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return response

def show_image_popup(image, window_name="Detection Results"):
    """Show an image in a pop-up window. Only for local testing, not in API server mode."""
    cv2.imshow(window_name, image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def to_python_type(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, list):
        return [to_python_type(x) for x in obj]
    elif isinstance(obj, tuple):
        return tuple(to_python_type(x) for x in obj)
    elif isinstance(obj, dict):
        return {k: to_python_type(v) for k, v in obj.items()}
    else:
        return obj

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True) 
    # At the end of the file, add a test block for local testing.
    if __name__ == "__main__":
        # Example usage for local testing
        import sys
        if len(sys.argv) > 1:
            img_path = sys.argv[1]
            img = cv2.imread(img_path)
            if img is None:
                print(f"Failed to load image: {img_path}")
            else:
                print(f"Loaded image: {img_path}, shape: {img.shape}")
                boxes = detect_fast(img, YOLO_MODEL)
                result_img = draw_detections(img, boxes)
                show_image_popup(result_img, window_name="Final Bounding Boxes")
        else:
            print("Usage: python geminiserver.py <image_path>")