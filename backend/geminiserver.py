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
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
import google.generativeai as genai
from ultralytics import YOLO

# Import required libraries for the full complex YOLO detection pipeline
import torch
# import open_clip  # Unused, remove
# from PIL import Image  # Duplicate, remove
# import torchvision.transforms as T  # Unused, remove
# import requests  # Unused, remove
import uuid
from threading import Lock

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

# Advanced YOLO detection parameters (from yolo_oscf_v7.py)
SCALES = (640, 1280)
CONF_THRESH = 0.25     # confidence for original detection
CONF_THRESH_LOW = 0.01  # ultra-low confidence for additional tests
IOU_NMS = 0.9      # high IoU to avoid early suppression in initial YOLO pass
MIN_AREA_PX = 64       # drop tiny boxes
EDGE_THRESH = 15       # std dev threshold in edge band for expansion
NMS_IOU = 0.1      # stricter IoU for final NMS
COLOR_T = 0.05    # lower means more aggressive drop of visually similar overlaps
MASK_THRESH = 0.01     # threshold for mask binarization
FEATURE_SIM_THRESH = 0.75  # cosine similarity threshold for feature matching

# Clustering thresholds
IOU_THRESH = 0.5         # 0.6–0.8: higher = only very overlapping boxes cluster
CENTER_DIST_FRAC = 0.3  # 0.2–0.3: smaller = boxes must be nearly concentric
AREA_RATIO_THRESH = 0.6  # 0.5–0.7: prevents merging tiny with huge
COLOR_THRESH = 0.3      # 0.1–0.2: lower = only very similar textures/colors merge

# --- TILE/ZOOM PARAMETERS ---
TILE_SIZE_FRAC = 1
TILE_STRIDE_FRAC = 0

# ---------------- PEG-DEDUP (CLIP) HELPERS ----------------
_CLIP_MODEL = None
_CLIP_PRE = None
_CLIP_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Load YOLO model once
YOLO_MODEL = YOLO(YOLO_MODEL_PATH)

# Gemini config from env
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyDVIppKcsZwVa3vkZWazztC9XY_-oZUufU")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")  # Use gemini-2.5-flash
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
    ax1, ay1, ax2, ay2, _ = a
    bx1, by1, bx2, by2, _ = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2-ix1+1), max(0, iy2-iy1+1)
    inter = iw * ih
    ua = (ax2-ax1+1)*(ay2-ay1+1)
    ub = (bx2-bx1+1)*(by2-by1+1)
    return inter / float(ua + ub - inter + 1e-6)

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

def non_max_suppression(boxes, iou_thresh=NMS_IOU):
    if len(boxes) == 0:
        return boxes
    idxs = np.argsort(-boxes[:,4])
    keep = []
    for i in idxs:
        b = boxes[i]
        if all(_iou(b, boxes[j]) < iou_thresh for j in keep):
            keep.append(i)
    return boxes[keep]

def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    a_norm = a / (np.linalg.norm(a) + 1e-8)
    b_norm = b / (np.linalg.norm(b) + 1e-8)
    return np.dot(a_norm, b_norm)

def center_dist_frac(a, b):
    ax1,ay1,ax2,ay2,_ = a; bx1,by1,bx2,by2,_ = b
    ca = np.array([(ax1+ax2)/2, (ay1+ay2)/2])
    cb = np.array([(bx1+bx2)/2, (by1+by2)/2])
    diag = max(np.hypot(ax2-ax1, ay2-ay1), np.hypot(bx2-bx1, by2-by1), 1e-6)
    return float(np.linalg.norm(ca-cb) / diag)

def size_ratio(a,b):
    ax1,ay1,ax2,ay2,_ = a; bx1,by1,bx2,by2,_ = b
    areaA = (ax2-ax1+1)*(ay2-ay1+1)
    areaB = (bx2-bx1+1)*(by2-by1+1)
    return min(areaA,areaB) / float(max(areaA,areaB)+1e-6)

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

def detect_fast(img_bgr, model):
    """
    Detection pipeline that stops at 95% box merging.
    """
    props = yolo_multi_test_detection(img_bgr, model)
    if len(props) > 0:
        merged = combine_similar_boxes(props, size_location_thresh=0.95)
        # (Popup code removed)
        return merged
    return np.empty((0,5), dtype=np.float32)

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
    return f"data:image/jpeg;base64,{base64.b64encode(buffer.read()).decode('utf-8')}"

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

def create_segment_canvases(segment_images, codes, max_canvas_size=1280, segment_size=256, padding=16, bboxes=None):
    """
    Arrange segment images (PIL) into one or more canvases, each at most max_canvas_size x max_canvas_size.
    Each segment is resized to segment_size on its longest side, with a number drawn on it, a lime green bounding box, and the bounding box coordinates drawn just outside (below) the segment, not overlapping the segment content.
    Returns: list of (canvas_image, [segment_code list])
    """
    if bboxes is None:
        bboxes = [None] * len(segment_images)
    # Resize all segments
    resized_segments = []
    for img, code, bbox in zip(segment_images, codes, bboxes):
        w, h = img.size
        if w > h:
            new_w, new_h = segment_size, int(h * segment_size / w)
        else:
            new_h, new_w = segment_size, int(w * segment_size / h)
        seg_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        # Draw the code number on the segment (top-left)
        draw = ImageDraw.Draw(seg_img)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except:
            font = ImageFont.load_default()
        text = str(code)
        # Use font.getsize or draw.textbbox for text size
        try:
            text_w, text_h = font.getsize(text)
        except AttributeError:
            bbox_text = draw.textbbox((0, 0), text, font=font)
            text_w, text_h = bbox_text[2] - bbox_text[0], bbox_text[3] - bbox_text[1]
        draw.rectangle([0, 0, text_w+8, text_h+8], fill=(255,255,0,200))
        draw.text((4, 4), text, fill=(0,0,0), font=font)
        resized_segments.append(seg_img)
    # Arrange into canvases
    canvases = []
    current_canvas = Image.new("RGB", (max_canvas_size, max_canvas_size), (240,240,240))
    codes_in_canvas = []
    x, y, row_height = padding, padding, 0
    for seg_img, code, bbox in zip(resized_segments, codes, bboxes):
        w, h = seg_img.size
        if x + w + padding > max_canvas_size:
            x = padding
            y += row_height + padding
            row_height = 0
        if y + h + padding > max_canvas_size:
            canvases.append((current_canvas, codes_in_canvas))
            current_canvas.show()  # <-- Remove or comment out for production
            current_canvas = Image.new("RGB", (max_canvas_size, max_canvas_size), (240,240,240))
            codes_in_canvas = []
            x, y, row_height = padding, padding, 0
        current_canvas.paste(seg_img, (x, y))
        # Draw lime green bounding box around the segment
        canvas_draw = ImageDraw.Draw(current_canvas)
        box_coords = [x, y, x + w - 1, y + h - 1]
        for offset in range(4):  # width=4
            canvas_draw.rectangle([
                box_coords[0] - offset,
                box_coords[1] - offset,
                box_coords[2] + offset,
                box_coords[3] + offset
            ], outline=(50, 255, 50))
        # Draw bounding box coordinates just below the segment
        if bbox is not None:
            bbox_str = f"({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]})"
            try:
                font_small = ImageFont.truetype("arial.ttf", 20)
            except:
                font_small = ImageFont.load_default()
            try:
                bbox_w, bbox_h = font_small.getsize(bbox_str)
            except AttributeError:
                bbox_box = canvas_draw.textbbox((0, 0), bbox_str, font=font_small)
                bbox_w, bbox_h = bbox_box[2] - bbox_box[0], bbox_box[3] - bbox_box[1]
            x_br = x + w - bbox_w - 6
            y_br = y + h + 4  # Just below the segment
            # If not enough space below, place above
            if y_br + bbox_h + 4 > max_canvas_size:
                y_br = y - bbox_h - 4
            canvas_draw.rectangle([x_br-2, y_br-2, x_br+bbox_w+2, y_br+bbox_h+2], fill=(0,0,0,220))
            canvas_draw.text((x_br, y_br), bbox_str, fill=(255,255,255), font=font_small)
        codes_in_canvas.append(code)
        x += w + padding
        row_height = max(row_height, h)
    if codes_in_canvas:
        canvases.append((current_canvas, codes_in_canvas))
        current_canvas.show()  # <-- Remove or comment out for production
    return canvases

def analyze_scene_with_gemini(scene_pil, crop_pils, codes, bboxes, instructions_override=None, temperature_override=None):
    import google.generativeai as genai
    # Create canvases with numbered segments and bounding box coordinates
    canvases = create_segment_canvases(crop_pils, codes, bboxes=bboxes)
    # Prepare Gemini prompt
    if instructions_override is not None:
        instructions = instructions_override
    else:
        instructions = r"""
You are an expert insurance-claims assistant. You will be given:
- The full-room image titled 'scene'.
- One or more canvas images, each containing a grid of numbered segments. Each segment is a cropped object from the scene, outlined with a green bounding box, and clearly labeled with a unique number in the top-left corner. The bounding box coordinates (x1, y1, x2, y2) for each segment are shown in the bottom-right corner of the segment image, in white text on a black rectangle.

Your task is to identify and value every unique object in the room, using both the full scene and the context of each segment. Follow these steps for maximum accuracy and thoroughness:

1. **Segment Review:** For each segment number visible in the canvases, examine the segment and its context in the full scene. Use the bounding box coordinates and appearance to infer what the object is, even if the segment is blurry or ambiguous. The number in the top-left corner is the unique identifier for that segment—always use this number for mapping. Use the bounding box coordinates to help map the segment to the full scene and distinguish between similar objects.
2. **Object Identification:** For each segment, list all plausible objects it could represent. Use spatial reasoning and context from the full scene to make your best, most plausible guess. If uncertain, state your reasoning and still provide your best guess.
3. **Strict Mapping:** For every output entry, double-check that the number you use matches the number actually shown on the segment in the canvas, and that the bounding box coordinates match the segment. Never guess or copy a number—only use the number and coordinates that are visually present on the segment. The mapping between number, coordinates, and segment must be exact and justified by the image content and position.
4. **Deduplication:** Only merge objects if you are certain they are the same physical item in the same location. If the image contains multiple similar objects (e.g., two identical chairs), each must have its own entry with its own number and spatial justification. Do not merge or deduplicate based on class or appearance alone—use spatial and contextual clues, including the bounding box coordinates.
5. **Classification-Image Match:** For each output entry, double-check that the classification (name, category, description) accurately matches the actual segment image and its context. If you are unsure, explain your reasoning and make your best justified guess. Do not assign a label to a segment unless the image content supports it.
6. **Fact-Checking:** After your initial list, review your output. For each object, verify:
    - Is the mapping between segment number, bounding box coordinates, and object correct and justified by the image content?
    - Is the object unique (not a duplicate unless truly the same physical item)?
    - Is the description, category, and price plausible given the image context?
    - If you are uncertain, add a comment in your reasoning and still provide your best guess.
7. **Final Verification:** Ensure every number and bounding box visible in the canvas is present in the output, and that no number or bounding box is used for more than one object unless it truly covers multiple objects in the same segment. Be strict about mapping and deduplication, and explain your reasoning for each mapping and deduplication decision.
8. **Output:**
    - Output a JSON array, where each entry is:
        {{
            "code": "<segment number>",
            "canvasIndex": <canvas index>,
            "bbox": [x1, y1, x2, y2],
            "name": "<object name>",
            "category": "<e.g. Furniture>",
            "price_usd": <number>,
            "description": "<brief>"
        }}
    - Ensure every segment number and bounding box visible in the canvases is represented in the output, even if you are not sure what the object is.
    - Return only the JSON array, nothing else.

**Be thorough, reason step by step, and self-verify your output before returning.**
"""
    # Resize full image to 768px longest edge
    scene_pil_resized = resize_image_maintain_aspect_ratio(scene_pil, 768)
    contents = [instructions, "scene", scene_pil_resized]
    for idx, (canvas_img, canvas_codes) in enumerate(canvases):
        contents.append(f"CANVAS:{idx} NUMBERS:{','.join(map(str, canvas_codes))}")
        contents.append(canvas_img)
    # Call Gemini
    try:
        response = GEMINI_GEN_MODEL.generate_content(
            contents,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=1.0 if temperature_override is None else temperature_override
            )
        )
        raw = response.text
        # Remove Markdown code block if present
        if raw.strip().startswith('```'):
            lines = raw.strip().splitlines()
            if lines[0].startswith('```') and lines[-1].startswith('```'):
                raw = '\n'.join(lines[1:-1])
        import json
        import ast
        try:
            parsed = json.loads(raw)
            items = parsed.get('items', []) if isinstance(parsed, dict) else parsed
        except json.JSONDecodeError:
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
        # Map Gemini results back to segment codes
        mapped_items = []
        for item in items:
            code = str(item.get('code', ''))
            canvas_idx = item.get('canvasIndex', 0)
            if code in codes:
                item['code'] = code
                item['canvasIndex'] = canvas_idx
                mapped_items.append(item)
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

# In-memory progress tracking (for demo; not for production)
# progress_dict = {}
# progress_lock = Lock()

@app.route("/api/analyze-image", methods=["POST"])
def analyze_image():
    import time
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
        print(f"[API] Passing {len(crop_pils)} crops to Gemini analysis (batched on canvases).")
        gemini_start = time.perf_counter()
        items = analyze_scene_with_gemini(scene_pil, crop_pils, codes, bboxes)
        gemini_end = time.perf_counter()
        print(f"[API] Time taken for Gemini analysis: {gemini_end - gemini_start:.2f} seconds.")
        # Map code to base64 crop for frontend
        code_to_image = {str(codes[i]): pil_image_to_base64(crop_pils[i]) for i in range(len(crop_pils))}
        print(f"[API] Returning response with {len(items)} items.")
        total_time = time.perf_counter() - start_time
        print(f"[API] Total endpoint time: {total_time:.2f} seconds.")
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
        num_workers = min(cpu_count(), 4)  # Limit to 4 or number of CPUs
        print(f"[API] Using {num_workers} worker processes for batch analysis.")
        with Pool(processes=num_workers) as pool:
            results = pool.map(analyze_single_image, images)
        print(f"[API] Batch processing complete.")
        for result in results:
            for item in result.get('items', []):
                item['price_usd'] = safe_price(item.get('price_usd', item.get('price', 0)))
            all_items.extend(result.get('items', []))
            all_objects.extend(result.get('objects', []))
            total_value += sum(float(item.get('price_usd', 0)) for item in result.get('items', []))
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