"""
Detection and deduplication utilities for ClaimReady backend
"""

import numpy as np
import cv2
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp
from functools import partial

# Detection utility functions
def _iou(a, b):
    """Calculate Intersection over Union of two boxes"""
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    
    if x2 <= x1 or y2 <= y1:
        return 0.0
    
    intersection = (x2 - x1) * (y2 - y1)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - intersection
    
    return intersection / union if union > 0 else 0.0

def size_ratio(a, b):
    """Calculate size ratio between two boxes"""
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return min(area_a, area_b) / max(area_a, area_b) if max(area_a, area_b) > 0 else 0.0

def center_dist_frac(a, b):
    """Calculate center distance as fraction of image diagonal"""
    center_a = ((a[0] + a[2]) / 2, (a[1] + a[3]) / 2)
    center_b = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    
    dist = np.sqrt((center_a[0] - center_b[0])**2 + (center_a[1] - center_b[1])**2)
    img_diag = np.sqrt(1920**2 + 1080**2)  # Assume standard image size
    return dist / img_diag

def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors"""
    if len(a) != len(b):
        return 0.0
    
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)

def calculate_mask_overlap(mask1, mask2):
    """Calculate overlap between two masks"""
    if mask1 is None or mask2 is None:
        return 0.0
    
    intersection = np.logical_and(mask1, mask2).sum()
    union = np.logical_or(mask1, mask2).sum()
    
    return intersection / union if union > 0 else 0.0

def calculate_mask_overlap_parallel(mask_pairs):
    """Calculate mask overlap for multiple pairs in parallel"""
    results = []
    for mask1, mask2 in mask_pairs:
        results.append(calculate_mask_overlap(mask1, mask2))
    return results

def expand_box(img_gray, box):
    """Expand bounding box to include more context"""
    h, w = img_gray.shape[:2]
    x1, y1, x2, y2 = box
    
    # Calculate expansion factor based on box size
    box_w = x2 - x1
    box_h = y2 - y1
    expansion = min(0.2, max(0.05, min(box_w, box_h) * 0.1))
    
    # Apply expansion
    pad_x = int(box_w * expansion)
    pad_y = int(box_h * expansion)
    
    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(w, x2 + pad_x)
    y2 = min(h, y2 + pad_y)
    
    return (x1, y1, x2, y2)

def contain_frac_smaller(a, b):
    """Calculate how much of smaller box is contained in larger box"""
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    
    if x2 <= x1 or y2 <= y1:
        return 0.0
    
    intersection = (x2 - x1) * (y2 - y1)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    smaller_area = min(area_a, area_b)
    
    return intersection / smaller_area if smaller_area > 0 else 0.0

def iou_boxes(a, b):
    """Calculate IoU between two bounding boxes"""
    return _iou(a, b)

def generate_unique_code(existing):
    """Generate unique code for items"""
    import uuid
    while True:
        code = str(uuid.uuid4())[:8]
        if code not in existing:
            return code
