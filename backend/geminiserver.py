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
from ultralytics import YOLO

# Import required libraries for the full complex YOLO detection pipeline
import torch
import open_clip
from PIL import Image
import torchvision.transforms as T
import requests

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# YOLO config from env
YOLO_MODEL_PATH = os.environ.get("YOLO_MODEL_PATH", "yolo11l-seg.pt")
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
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite-preview-06-17")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")
genai.configure(api_key=GEMINI_API_KEY)
GEMINI_GEN_MODEL = genai.GenerativeModel(GEMINI_MODEL)

# Gemini response schema (only require code, name, price_usd)
GEMINI_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "name": {"type": "string"},
                    "category": {"type": "string"},
                    "brand": {"type": "string"},
                    "condition": {"type": "string"},
                    "price_usd": {"type": "number"},
                    "description": {"type": "string"},
                    "nullify": {"type": "boolean"}
                },
                "required": ["code", "name", "price_usd", "nullify"]
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

def combine_similar_boxes(boxes, size_location_thresh=0.95):
    """
    Combine boxes that are 95% the same size and location.
    Returns merged boxes with highest confidence score.
    """
    if len(boxes) == 0:
        return boxes
    
    print(f"[INFO] Combining similar boxes (threshold={size_location_thresh})...")
    
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
        current_group = [current_box]
        used[i] = True
        
        # Check against all other boxes
        for j in range(i + 1, len(boxes_sorted)):
            if used[j]:
                continue
            
            other_box = boxes_sorted[j]
            
            # Calculate size and location similarity
            x1_1, y1_1, x2_1, y2_1, conf1 = current_box
            x1_2, y1_2, x2_2, y2_2, conf2 = other_box
            
            # Size similarity (area ratio)
            area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
            area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
            size_similarity = min(area1, area2) / max(area1, area2)
            
            # Location similarity (center distance relative to box size)
            center1_x, center1_y = (x1_1 + x2_1) / 2, (y1_1 + y2_1) / 2
            center2_x, center2_y = (x1_2 + x2_2) / 2, (y1_2 + y2_2) / 2
            
            box1_size = max(x2_1 - x1_1, y2_1 - y1_1)
            center_distance = np.sqrt((center1_x - center2_x)**2 + (center1_y - center2_y)**2)
            location_similarity = 1.0 - (center_distance / (box1_size + 1e-8))
            
            # Combined similarity (geometric mean)
            combined_similarity = np.sqrt(size_similarity * location_similarity)
            
            if combined_similarity >= size_location_thresh:
                current_group.append(other_box)
                used[j] = True
                print(f"[INFO] Combining boxes {i} and {j} (similarity={combined_similarity:.3f})")
        
        # Keep the box with highest confidence from the group
        best_box = max(current_group, key=lambda x: x[4])
        merged_boxes.append(best_box)
    
    result = np.array(merged_boxes, dtype=np.float32)
    print(f"[INFO] Combined {len(boxes)} boxes into {len(result)} unique boxes")
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
    
    print(f"[INFO] Running test: {test_name} (conf_thresh={conf_thresh})")
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
    print(f"[INFO] Test {test_name}: {len(boxes)} proposals")
    
    # Show popup with detection results for this test
    # if len(boxes) > 0:
    #     img_show = test_img.copy()
    #     for i, (x1, y1, x2, y2, conf) in enumerate(boxes):
    #         cv2.rectangle(img_show, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
    #         cv2.putText(img_show, f"{i}: {conf:.2f}", (int(x1), int(y1)-10), 
    #                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Resize image if too large for display
        # h, w = img_show.shape[:2]
        # if h > 800 or w > 1200:
        #     scale = min(800/h, 1200/w)
        #     new_h, new_w = int(h * scale), int(w * scale)
        #     img_show = cv2.resize(img_show, (new_w, new_h))
        
        # cv2.imshow(f"{test_name} - {len(boxes)} detections", img_show)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
    
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
    print("[INFO] Starting two-stage detection pipeline...")
    
    # Stage 1: Original detection with normal confidence
    print("[INFO] Stage 1: Running original detection with conf_thresh=0.25")
    original_boxes, original_masks = run_detection_test(img_bgr, model, "Original (conf=0.25)", conf_thresh=CONF_THRESH)
    
    if len(original_boxes) == 0:
        print("[INFO] No original detections found.")
        return []
    
    # Extract features for original detections
    print("[INFO] Extracting features for original detections...")
    original_features = extract_backbone_features(model, img_bgr, original_boxes)
    
    # Stage 2: Additional tests with low confidence
    additional_boxes = []
    additional_masks = []
    
    # Test 1: Grayscale 3-channel with low confidence
    print("[INFO] Stage 2: Running grayscale test with conf_thresh=0.05")
    grayscale_boxes, grayscale_masks = run_detection_test(img_bgr, model, "Grayscale (conf=0.05)", 
                                                         to_grayscale_3ch, conf_thresh=0.05)
    additional_boxes.extend(grayscale_boxes)
    additional_masks.extend(grayscale_masks)
    
    # Test 2: Edge-overlay with low confidence
    print("[INFO] Stage 2: Running edge-overlay test with conf_thresh=0.01")
    edge_boxes, edge_masks = run_detection_test(img_bgr, model, "Edge-overlay (conf=0.01)", 
                                               edge_overlay_canny, conf_thresh=CONF_THRESH_LOW)
    additional_boxes.extend(edge_boxes)
    additional_masks.extend(edge_masks)
    
    if len(additional_boxes) == 0:
        print("[INFO] No additional detections found.")
        return original_boxes
    
    # Extract features for additional detections
    print("[INFO] Extracting features for additional detections...")
    additional_features = extract_backbone_features(model, img_bgr, additional_boxes)
    
    # Filter additional detections to only keep non-duplicates
    print("[INFO] Filtering additional detections for duplicates using masks...")
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
                print(f"[INFO] Additional detection {i} is duplicate of original detection {j}")
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
                    print(f"[INFO] Additional detection {i} is duplicate of additional detection {j}")
                    is_duplicate = True
                    used_additional.add(j)  # Mark the duplicate as used
                    break
        
        if not is_duplicate:
            filtered_additional.append(add_box)
            if i < len(additional_masks):
                filtered_additional_masks.append(additional_masks[i])
            print(f"[INFO] Additional detection {i} is unique - keeping it")
        used_additional.add(i)
    
    # Combine original and filtered additional detections
    final_boxes = original_boxes + filtered_additional
    final_masks = original_masks + filtered_additional_masks
    print(f"[INFO] Combined detections: {len(original_boxes)} original + {len(filtered_additional)} additional = {len(final_boxes)} total")
    
    # Show combined results before 95% merging (removed popup)
    # if len(final_boxes) > 0:
    #     img_combined = img_bgr.copy()
    #     for i, (x1, y1, x2, y2, conf) in enumerate(final_boxes):
    #         color = (0, 255, 0) if i < len(original_boxes) else (255, 0, 0)  # Green for original, Blue for additional
    #         cv2.rectangle(img_combined, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
    #         cv2.putText(img_combined, f"{i}: {conf:.2f}", (int(x1), int(y1)-10), 
    #                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Resize image if too large for display
        # h, w = img_combined.shape[:2]
        # if h > 800 or w > 1200:
        #     scale = min(800/h, 1200/w)
        #     new_h, new_w = int(h * scale), int(w * scale)
        #     img_combined = cv2.resize(img_combined, (new_w, new_h))
        
        # cv2.imshow(f"Combined Results - {len(final_boxes)} boxes (Green=Original, Blue=Additional)", img_combined)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
    
    # Step 4: Combine boxes that are 95% the same size and location
    if len(final_boxes) > 0:
        final_boxes = combine_similar_boxes(final_boxes, size_location_thresh=0.95)
        print(f"[INFO] After size/location combination: {len(final_boxes)} boxes")
    
    return final_boxes

def detect_fast(img_bgr, model):
    """
    Detection pipeline that stops at 95% box merging.
    """
    print("[INFO] Starting multi-test detection pipeline (stopping at 95% box merging)...")
    props = yolo_multi_test_detection(img_bgr, model)
    print(f"[INFO] {len(props)} proposals before 95% merging")
    if len(props) > 0:
        merged = combine_similar_boxes(props, size_location_thresh=0.95)
        print(f"[INFO] After 95% box merging: {len(merged)} boxes")
        # --- Show popup of image with merged boxes ---
        # img_with_boxes = img_bgr.copy()
        # for i, box in enumerate(merged):
        #     x1, y1, x2, y2, conf = map(int, box)
        #     cv2.rectangle(img_with_boxes, (x1, y1), (x2, y2), (0, 255, 255), 2)  # Yellow for merged boxes
        #     cv2.putText(img_with_boxes, f"Merged{i} ({conf:.2f})", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        # cv2.imshow("After 95% Box Merging", img_with_boxes)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        # --- End popup ---
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
            return {"error": "Failed to decode image"}
        
        print(f"[INFO] Image loaded: {img_bgr.shape}")
        
        # Use the ACTUAL FULL COMPLEX YOLO detection pipeline from yolo_oscf_v7.py
        print("[INFO] Starting ACTUAL FULL COMPLEX YOLO detection pipeline from yolo_oscf_v7.py...")
        print("[INFO] This includes:")
        print("  - Two-stage detection pipeline (original + additional tests)")
        print("  - Feature-based duplicate detection")
        print("  - Mask-based similarity checking")
        print("  - Advanced confidence thresholds (0.25, 0.05, 0.01)")
        print("  - Box merging with 95% similarity threshold")
        print("  - Voting on boxes across tests")
        print("  - Multi-scale detection (640, 1280, 1920)")
        print("  - CLAHE brightening for better detection")
        print("  - Busy area detection and focused detection")
        print("  - Tile-based detection with overlapping windows")
        print("  - Weighted Box Fusion for merging proposals")
        print("  - PEG-Dedup with CLIP features for deduplication")
        print("  - Box expansion to visual edges")
        print("  - Advanced color-based deduplication")
        
        # Run detection using the full complex pipeline from yolo_oscf_v7.py
        boxes = detect_fast(img_bgr, YOLO_MODEL)
        
        print(f"[INFO] Detection complete: {len(boxes)} objects found")
        
        if not boxes:
            return {"error": "No objects detected"}
        
        # Process detected objects
        results = []
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
            existing_codes = [r['code'] for r in results]
            code = generate_unique_code(existing_codes)
            
            results.append({
                'code': code,
                'box': [x1, y1, x2, y2],
                'confidence': float(confidence),
                'image': crop_pil
            })
        
        print(f"[INFO] Processed {len(results)} objects for analysis")
        
        # Analyze with Gemini
        if results:
            analysis_result = analyze_scene_with_gemini(image_data, results)
            return analysis_result
        else:
            return {"error": "No valid objects to analyze"}
            
    except Exception as e:
        print(f"[ERROR] Error in analyze_single_image: {str(e)}")
        return {"error": f"Analysis failed: {str(e)}"}

    # === COMMENTED OUT: SIMPLIFIED BASIC YOLO DETECTION ===
    # print("[INFO] Using simplified basic YOLO detection...")
    # 
    # # Run basic YOLO detection with standard parameters
    # # This replaces the complex multi-test pipeline with a simple single-pass detection
    # # Uses YOLOv11-seg model with confidence threshold and IoU filtering
    # results = YOLO_MODEL(cv_image, conf=YOLO_CONF, iou=0.5, verbose=False)
    # result = results[0]
    # 
    # # Extract boxes and masks
    # detected_boxes = []
    # detected_masks = []
    # 
    # if hasattr(result, 'boxes') and result.boxes is not None:
    #     for box in result.boxes:
    #         x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
    #         conf = float(box.conf[0])
    #         detected_boxes.append([x1, y1, x2, y2, conf])
    # 
    # if hasattr(result, 'masks') and result.masks is not None:
    #     masks = result.masks.data.cpu().numpy()
    #     masks = (masks > 0.5).astype(np.uint8)
    #     detected_masks = list(masks)
    # 
    # print(f"[INFO] Basic YOLO detected {len(detected_boxes)} objects")
    # 
    # # Convert to tuple format for compatibility
    # detected = []
    # for box in detected_boxes:
    #     x1, y1, x2, y2, conf = box
    #     detected.append((int(x1), int(y1), int(x2), int(y2)))
    # 
    # # If no boxes, return early
    # if not detected:
    #     return {
    #         'status': 'success',
    #         'items': [],
    #         'objects': [],
    #         'total_items': 0,
    #         'total_value': 0
    #     }
    # 
    # # Unified Gemini call with duplicate detection
    # items = analyze_scene_with_gemini(image_data, detected)
    # 
    # # Calculate total value (only for valid items)
    # total_value = sum(safe_price(item.get('price_usd', 0)) for item in items)
    # 
    # return {
    #     'status': 'success',
    #     'items': items,
    #     'objects': detected,
    #     'total_items': len(items),
    #     'total_value': total_value
    # }

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

def analyze_scene_with_gemini(scene_pil, crop_pils, codes):
    import google.generativeai as genai
    
    # Resize full image to 768px longest edge
    scene_pil_resized = resize_image_maintain_aspect_ratio(scene_pil, 768)
    
    # Resize all segments to 384px longest edge
    crop_pils_resized = [resize_image_maintain_aspect_ratio(crop, 384) for crop in crop_pils]
    
    instructions = """You are an insurance‑claims assistant. You receive:
    - The full‑room image (for context)
    - A series of CODE:<id> segmented images
    NOTES: Be extremly thorough and detailed when scanning so you include every object in your output and be conservative in pricing.

    Tasks:
    1. Study the full image to understand scene context to better help you classify names and prices.
    2. For each CODE:<id> segment:
        a. Determine the object(s) it contains.
        b. If an object is not yet represented, find the segment that shows the object most centered and set nullify=false.
        c. Set nullify=true ONLY if a segment has no unique objects. Even if an object is blurry, if it is unique, keep nullify=true
        d. If you find an object in the full image but cannot find a segement that contains any part of the object, do not include the object in your listings
    3. Even if a segment is nullified for one object, scan it for any *other* objects not yet represent. Aim to include EVERY segment at least once in the JSON
    4. For each segment output exactly:
    {
        "code": "<id>",
        "name": "<object name>",
        "category": "<e.g. Furniture>",
        "brand": "<or unknown>",
        "condition": "<e.g. good>",
        "price_usd": <number>,
        "description": "<brief>",
        "nullify": <true|false>
    }
    Return only a JSON array of these objects."""
    
    schema = GEMINI_RESPONSE_SCHEMA
    # Build the content list for the SDK
    content = [instructions, scene_pil_resized]
    for i, crop in enumerate(crop_pils_resized):
        content.append(f"CODE:{codes[i]}")
        content.append(crop)
    try:
        response = GEMINI_GEN_MODEL.generate_content(content)
        raw = response.text
        print("[Gemini raw response]", raw)
        print("Gemini response type:", type(raw))
        print("Gemini response repr:", repr(raw))
        # Remove Markdown code block if present
        if raw.strip().startswith('```'):
            lines = raw.strip().splitlines()
            if lines[0].startswith('```') and lines[-1].startswith('```'):
                raw = '\n'.join(lines[1:-1])
        import json
        import ast
        # Try to parse as JSON
        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            # If it's a quoted string, strip quotes and try again
            if raw.startswith('"') and raw.endswith('"'):
                try:
                    items = json.loads(raw[1:-1])
                except Exception:
                    items = []
            else:
                try:
                    items = ast.literal_eval(raw)
                except Exception as e:
                    logger.error(f"Failed to parse Gemini response: {e}")
                    items = []
        return items
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise

@app.route("/api/analyze-image", methods=["POST"])
def analyze_image():
    try:
        file = request.files["image"]
        file_bytes = file.read()
        np_arr = np.frombuffer(file_bytes, np.uint8)
        cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if cv_image is None:
            return jsonify({'status': 'error', 'error': 'Invalid image data', 'items': [], 'objects': [], 'total_items': 0, 'total_value': 0}), 400
        scene_pil = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
        detected_boxes = detect_fast(cv_image, YOLO_MODEL)
        crop_pils, codes = [], []
        for i, box in enumerate(detected_boxes):
            x1, y1, x2, y2, conf = map(int, box)
            crop = cv_image[y1:y2+1, x1:x2+1]
            crop_pil = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            crop_pils.append(crop_pil)
            codes.append(str(i))
        items = analyze_scene_with_gemini(scene_pil, crop_pils, codes)
        # Filter out items with nullify=true
        filtered_items = [item for item in items if not item.get('nullify', False)]
        # Build code->image mapping for frontend
        code_to_image = {str(i): pil_image_to_base64(crop_pils[i]) for i in range(len(crop_pils))}
        for k, v in code_to_image.items():
            print(f"Image for code {k}: length={len(v)}, preview={v[:100]}")
        return jsonify(items=filtered_items, total_items=len(filtered_items), images=code_to_image)
    except Exception as e:
        logger.error(f"Error processing image: {e}")
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
        for image_data in images:
            result = analyze_single_image(image_data)
            # Coerce all price_usd to float for total_value
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
        logger.error(f"Error processing multiple images: {e}")
        return jsonify({
            'error': str(e),
            'status': 'error',
            'items': []
        }), 500

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True) 