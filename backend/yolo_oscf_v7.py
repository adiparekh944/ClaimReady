"""
YOLO-Only Fast Class-Agnostic Room Objectness Detector
======================================================

Detects "anything that looks like an object" in a room image without SAM.
Runs YOLOv11 at multiple scales in low-conf objectness mode,
merges proposals via Weighted Box Fusion, expands boxes to visual edges,
filters junk, applies strict non-max suppression and color-based deduplication to remove overlaps,
and outputs an annotated image.

Configure INPUT_IMAGE and OUTPUT_IMAGE below, then:
    python yolo_fast_room_objectness.py

Requirements:
  pip install ultralytics opencv-python numpy torch

"""

import cv2
import numpy as np
from ultralytics import YOLO
import torch
import open_clip
from PIL import Image
import torchvision.transforms as T

# ---------------- USER CONFIG ----------------
INPUT_IMAGE  = r"C:\Users\Arnav\Downloads\Room3.jpg"
OUTPUT_IMAGE = r"C:\Users\Arnav\Downloads\Room_out.jpg"
MODEL_PATH   = r"yolo11x-seg.pt"

# ---------------- PARAMETERS ----------------
SCALES       = (640, 1280, 1920)
CONF_THRESH  = 0.25     # confidence for original detection
CONF_THRESH_LOW = 0.01  # ultra-low confidence for additional tests
IOU_NMS      = 0.9      # high IoU to avoid early suppression in initial YOLO pass
MIN_AREA_PX  = 64       # drop tiny boxes
EDGE_THRESH  = 15       # std dev threshold in edge band for expansion
# Lower final NMS IoU to be more strict about overlaps
NMS_IOU      = 0.1      # stricter IoU for final NMS
# Color divergence threshold for nested dedup
COLOR_T      = 0.05    # lower means more aggressive drop of visually similar overlaps
MASK_THRESH  = 0.01     # threshold for mask binarization (default 0.5)
# Feature similarity threshold for duplicate detection
FEATURE_SIM_THRESH = 0.75  # cosine similarity threshold for feature matching (more strict)

# --- TILE/ZOOM PARAMETERS ---
# Fraction of the image for the zoom window (e.g., 0.5 = 50% of image)
TILE_SIZE_FRAC = 1
# Fraction of the window size to move each step (e.g., 0.2 = 20% of window size)
TILE_STRIDE_FRAC = 0

# ---------------- CLUSTERING THRESHOLDS (tune here) ----------------
IOU_THRESH = 0.5         # 0.6–0.8: higher = only very overlapping boxes cluster
CENTER_DIST_FRAC = 0.3  # 0.2–0.3: smaller = boxes must be nearly concentric
AREA_RATIO_THRESH = 0.6  # 0.5–0.7: prevents merging tiny with huge
COLOR_THRESH = 0.3      # 0.1–0.2: lower = only very similar textures/colors merge

# ----------------- HELPERS -----------------

def load_image(path):
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    return img


def yolo_multiscale(img_bgr, model):
    all_boxes = []
    for sz in SCALES:
        res = model.predict(img_bgr, imgsz=sz, conf=CONF_THRESH, iou=IOU_NMS,
                            agnostic_nms=True, verbose=False)
        for b in res[0].boxes:
            x1, y1, x2, y2 = b.xyxy[0].cpu().numpy()
            score = float(b.conf[0])
            all_boxes.append([x1, y1, x2, y2, score])
    return np.array(all_boxes, dtype=np.float32)


def detect_busy_areas(img_bgr, patch_size=128, threshold=0.1, max_patches=10):
    """
    Detect busy/high-detail areas in the image and return patch coordinates.
    Uses edge density and variance to identify regions with lots of detail.
    """
    H, W = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # Compute edge density map
    edges = cv2.Canny(gray, 50, 150)
    kernel_size = max(1, patch_size//4)
    if kernel_size % 2 == 0:
        kernel_size += 1  # Ensure odd kernel size
    edge_density = cv2.GaussianBlur(edges.astype(np.float32), (kernel_size, kernel_size), 0)
    
    # Compute variance map (local texture)
    var_kernel_size = max(1, patch_size//8)
    if var_kernel_size % 2 == 0:
        var_kernel_size += 1  # Ensure odd kernel size
    kernel = np.ones((var_kernel_size, var_kernel_size), np.float32) / (var_kernel_size)**2
    mean = cv2.filter2D(gray.astype(np.float32), -1, kernel)
    variance = cv2.filter2D((gray.astype(np.float32) - mean)**2, -1, kernel)
    
    # Combine edge density and variance
    busy_map = (edge_density / 255.0 + variance / 1000.0) / 2.0
    
    # Find local maxima in busy areas
    patches = []
    step = patch_size // 2  # Overlap patches
    
    for y in range(0, H - patch_size + 1, step):
        for x in range(0, W - patch_size + 1, step):
            patch_busy = np.mean(busy_map[y:y+patch_size, x:x+patch_size])
            if patch_busy > threshold:
                patches.append((x, y, patch_busy))
    
    # Sort by busyness and take top patches
    patches.sort(key=lambda p: p[2], reverse=True)
    return patches[:max_patches]


def yolo_multiscale_and_tiles(img_bgr, model):
    all_boxes = []
    H, W = img_bgr.shape[:2]
    # 1. Full image at all scales
    print(f"[INFO] Running YOLO on full image at {SCALES} scales...")
    for sz in SCALES:
        res = model.predict(img_bgr, imgsz=sz, conf=CONF_THRESH, iou=IOU_NMS,
                            agnostic_nms=True, verbose=False)
        for b in res[0].boxes:
            x1, y1, x2, y2 = b.xyxy[0].cpu().numpy()
            score = float(b.conf[0])
            all_boxes.append([x1, y1, x2, y2, score])
    
    # 2. Brightened image (CLAHE) at all scales
    print(f"[INFO] Running YOLO on brightened image (CLAHE) at {SCALES} scales...")
    # Convert to LAB color space for CLAHE
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    lab[:,:,0] = clahe.apply(lab[:,:,0])  # Apply CLAHE to L channel
    img_brightened = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
    for sz in SCALES:
        res = model.predict(img_brightened, imgsz=sz, conf=CONF_THRESH, iou=IOU_NMS,
                            agnostic_nms=True, verbose=False)
        for b in res[0].boxes:
            x1, y1, x2, y2 = b.xyxy[0].cpu().numpy()
            score = float(b.conf[0])
            all_boxes.append([x1, y1, x2, y2, score])
    
    # 3. Busy areas detection and YOLO
    print(f"[INFO] Detecting busy areas and running YOLO...")
    busy_patches = detect_busy_areas(img_bgr, patch_size=256, threshold=0.15, max_patches=8)
    print(f"[INFO] Found {len(busy_patches)} busy patches")
    
    for i, (x0, y0, busy_score) in enumerate(busy_patches):
        print(f"[INFO] Busy patch {i+1}/{len(busy_patches)} at (x={x0}, y={y0}, busy={busy_score:.3f})...")
        patch = img_bgr[y0:y0+256, x0:x0+256]
        for sz in SCALES:
            res = model.predict(patch, imgsz=sz, conf=CONF_THRESH, iou=IOU_NMS,
                                agnostic_nms=True, verbose=False)
            for b in res[0].boxes:
                x1, y1, x2, y2 = b.xyxy[0].cpu().numpy()
                score = float(b.conf[0])
                # Map back to full image coordinates
                all_boxes.append([x1 + x0, y1 + y0, x2 + x0, y2 + y0, score])
    
    # 4. Overlapping tiles with new logic
    tile_h = int(round(H * TILE_SIZE_FRAC))
    tile_w = int(round(W * TILE_SIZE_FRAC))
    stride_h = int(round(tile_h * TILE_STRIDE_FRAC))
    stride_w = int(round(tile_w * TILE_STRIDE_FRAC))
    if stride_h < 1: stride_h = 1
    if stride_w < 1: stride_w = 1
    # Ensure last tile covers the edge exactly
    y_starts = list(range(0, H - tile_h + 1, stride_h))
    if y_starts[-1] != H - tile_h:
        y_starts.append(H - tile_h)
    x_starts = list(range(0, W - tile_w + 1, stride_w))
    if x_starts[-1] != W - tile_w:
        x_starts.append(W - tile_w)
    total_tiles = len(y_starts) * len(x_starts)
    tile_count = 0
    print(f"[INFO] Running YOLO on {total_tiles} tiles (tile size: {tile_w}x{tile_h}, stride: {stride_w}x{stride_h})...")
    for y0 in y_starts:
        for x0 in x_starts:
            tile_count += 1
            print(f"[INFO] Tile {tile_count}/{total_tiles} at (x={x0}, y={y0})...")
            tile = img_bgr[y0:y0+tile_h, x0:x0+tile_w]
            for sz in SCALES:
                res = model.predict(tile, imgsz=sz, conf=CONF_THRESH, iou=IOU_NMS,
                                    agnostic_nms=True, verbose=False)
                for b in res[0].boxes:
                    x1, y1, x2, y2 = b.xyxy[0].cpu().numpy()
                    score = float(b.conf[0])
                    # Map back to full image coordinates
                    all_boxes.append([x1 + x0, y1 + y0, x2 + x0, y2 + y0, score])
    print(f"[INFO] Finished YOLO on all tiles.")
    return np.array(all_boxes, dtype=np.float32)


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


def weighted_box_fusion(boxes, iou_thresh=0.55):
    if len(boxes) == 0:
        return boxes
    idxs = np.argsort(-boxes[:,4])
    used = np.zeros(len(boxes), dtype=bool)
    fused = []
    for i in idxs:
        if used[i]: continue
        group = [i]
        for j in idxs:
            if used[j] or j == i: continue
            if _iou(boxes[i], boxes[j]) >= iou_thresh:
                group.append(j)
        used[group] = True
        grp = boxes[group]
        w = grp[:,4] / (grp[:,4].sum() + 1e-6)
        x1 = (grp[:,0] * w).sum()
        y1 = (grp[:,1] * w).sum()
        x2 = (grp[:,2] * w).sum()
        y2 = (grp[:,3] * w).sum()
        score = grp[:,4].max()
        fused.append([x1, y1, x2, y2, score])
    return np.array(fused, dtype=np.float32)


def bhattacharyya_dist(img, a, b, bins=16):
    xa1, ya1, xa2, ya2, _ = map(int, a)
    xb1, yb1, xb2, yb2, _ = map(int, b)
    roi_a = img[ya1:ya2+1, xa1:xa2+1]
    roi_b = img[yb1:yb2+1, xb1:xb2+1]
    if roi_a.size == 0 or roi_b.size == 0:
        return 1.0
    dists = []
    for c in range(3):
        ha = cv2.calcHist([roi_a], [c], None, [bins], [0,256]).flatten()
        hb = cv2.calcHist([roi_b], [c], None, [bins], [0,256]).flatten()
        ha /= (ha.sum() + 1e-6); hb /= (hb.sum() + 1e-6)
        bc = np.sum(np.sqrt(ha * hb))
        dists.append(np.sqrt(max(0.0, 1.0 - bc)))
    return float(np.mean(dists))


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

# --- Deduplication helpers ---
def iou(a, b):
    x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
    x2 = min(a[2], b[2]); y2 = min(a[3], b[3])
    inter = max(0, x2-x1+1) * max(0, y2-y1+1)
    areaA = (a[2]-a[0]+1)*(a[3]-a[1]+1)
    areaB = (b[2]-b[0]+1)*(b[3]-b[1]+1)
    return inter / float(areaA + areaB - inter + 1e-6)

def color_dist(img, boxA, boxB, bins=16):
    xa,ya,xa2,ya2,_ = map(int, boxA); xb,yb,xb2,yb2,_ = map(int, boxB)
    roiA = img[ya:ya2, xa:xa2]; roiB = img[yb:yb2, xb:xb2]
    if roiA.size==0 or roiB.size==0: return 1.0
    dists=[]
    for ch in range(3):
        hA = cv2.calcHist([roiA],[ch],None,[bins],[0,256]).flatten()
        hB = cv2.calcHist([roiB],[ch],None,[bins],[0,256]).flatten()
        hA/= (hA.sum()+1e-6); hB/= (hB.sum()+1e-6)
        bc = np.sum(np.sqrt(hA*hB))
        dists.append(np.sqrt(max(0,1-bc)))
    return float(np.mean(dists))

def is_same_object(a, b, img,
                   iou_thresh=IOU_THRESH,
                   center_dist_frac=CENTER_DIST_FRAC,
                   area_ratio_thresh=AREA_RATIO_THRESH,
                   color_thresh=COLOR_THRESH):
    if iou(a,b) < iou_thresh:
        return False
    ca = np.array([(a[0]+a[2])*.5, (a[1]+a[3])*.5])
    cb = np.array([(b[0]+b[2])*.5, (b[1]+b[3])*.5])
    diag = np.linalg.norm([a[2]-a[0], a[3]-a[1]])
    if np.linalg.norm(ca-cb) / (diag+1e-6) > center_dist_frac:
        return False
    areaA = (a[2]-a[0])*(a[3]-a[1]); areaB = (b[2]-b[0])*(b[3]-b[1])
    if min(areaA,areaB)/max(areaA,areaB) < area_ratio_thresh:
        return False
    if color_dist(img, a, b) > color_thresh:
        return False
    return True

def cluster_and_union(boxes, img,
                      iou_thresh=IOU_THRESH,
                      center_dist_frac=CENTER_DIST_FRAC,
                      area_ratio_thresh=AREA_RATIO_THRESH,
                      color_thresh=COLOR_THRESH):
    clusters = []
    for box in boxes:
        placed = False
        for cl in clusters:
            if any(is_same_object(box, member, img,
                                 iou_thresh=iou_thresh,
                                 center_dist_frac=center_dist_frac,
                                 area_ratio_thresh=area_ratio_thresh,
                                 color_thresh=color_thresh) for member in cl):
                cl.append(box)
                placed = True
                break
        if not placed:
            clusters.append([box])
    out = []
    for cl in clusters:
        xs1 = min(b[0] for b in cl)
        ys1 = min(b[1] for b in cl)
        xs2 = max(b[2] for b in cl)
        ys2 = max(b[3] for b in cl)
        score = max(b[4] for b in cl)
        out.append([xs1, ys1, xs2, ys2, score])
    return np.array(out, dtype=np.float32)

# ---------------- PEG-DEDUP (CLIP) HELPERS ----------------
_CLIP_MODEL = None
_CLIP_PRE = None
_CLIP_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

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

def run_detection_test(img_bgr, model, test_name, transform_func=None, conf_thresh=None):
    """
    Run a single detection test with optional image transformation.
    Returns list of boxes and masks in original image coordinates.
    Also displays the image with boxes and masks for this test.
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
    
    # Show the image with boxes for this test
    # COMMENTED OUT - Intermediate popups
    """
    img_show = test_img.copy()
    for x1, y1, x2, y2, _ in boxes:
        cv2.rectangle(img_show, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 255), 2)
    cv2.imshow(f"{test_name} - Boxes", img_show)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    # Show the image with masks for this test
    if masks:
        img_with_masks = draw_masks_on_image(test_img, masks)
        cv2.imshow(f"{test_name} - Masks", img_with_masks)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    """
    
    return boxes, masks

def boxes_match(box1, box2, iou_thresh=0.5):
    """Check if two boxes represent the same object using IoU."""
    x1_1, y1_1, x2_1, y2_1, _ = box1
    x1_2, y1_2, x2_2, y2_2, _ = box2
    
    # Calculate IoU
    ix1 = max(x1_1, x1_2)
    iy1 = max(y1_1, y1_2)
    ix2 = min(x2_1, x2_2)
    iy2 = min(y2_1, y2_2)
    
    if ix2 <= ix1 or iy2 <= iy1:
        return False
    
    inter = (ix2 - ix1) * (iy2 - iy1)
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - inter
    
    return inter / union >= iou_thresh

def vote_on_boxes(all_test_boxes, min_votes=2):
    """
    Vote on boxes across all tests. Keep only boxes that appear in >= min_votes tests.
    """
    print(f"[INFO] Voting on boxes across {len(all_test_boxes)} tests (min_votes={min_votes})...")
    
    if not all_test_boxes:
        return []
    
    # Flatten all boxes and assign test IDs
    all_boxes_with_tests = []
    for test_idx, test_boxes in enumerate(all_test_boxes):
        for box in test_boxes:
            all_boxes_with_tests.append((box, test_idx))
    
    # Group boxes that represent the same object
    voted_boxes = []
    used_boxes = set()  # Track used boxes by their coordinates and test
    
    for i, (box1, test1) in enumerate(all_boxes_with_tests):
        # Create a unique identifier for this box
        box_id = (tuple(box1[:4]), test1)  # Use coordinates and test index
        if box_id in used_boxes:
            continue
            
        # Find all boxes (including from other tests) that match this one
        matching_boxes = [(box1, test1)]
        matching_tests = {test1}
        
        for j, (box2, test2) in enumerate(all_boxes_with_tests):
            if i == j:
                continue
            box2_id = (tuple(box2[:4]), test2)
            if box2_id in used_boxes:
                continue
            if boxes_match(box1, box2):
                matching_boxes.append((box2, test2))
                matching_tests.add(test2)
        
        # Only keep if enough tests voted for this object
        if len(matching_tests) >= min_votes:
            # Use the box with highest score
            best_box = max(matching_boxes, key=lambda x: x[0][4])
            voted_boxes.append(best_box[0])
            # Mark all matching boxes as used
            for box, test in matching_boxes:
                used_boxes.add((tuple(box[:4]), test))
    
    print(f"[INFO] Voting complete: {len(voted_boxes)} objects with >= {min_votes} votes")
    return voted_boxes

def unsharp_mask(img):
    # Sharpen using unsharp mask
    blur = cv2.GaussianBlur(img, (0,0), 3)
    return cv2.addWeighted(img, 1.5, blur, -0.5, 0)

def gamma_correction(img, gamma):
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(256)]).astype("uint8")
    return cv2.LUT(img, table)

def gray_world_white_balance(img):
    # Simple gray-world white balance
    result = img.copy().astype(np.float32)
    avgB = np.mean(result[:,:,0])
    avgG = np.mean(result[:,:,1])
    avgR = np.mean(result[:,:,2])
    avgGray = (avgB + avgG + avgR) / 3
    result[:,:,0] *= avgGray / avgB
    result[:,:,1] *= avgGray / avgG
    result[:,:,2] *= avgGray / avgR
    result = np.clip(result, 0, 255).astype(np.uint8)
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

def find_overlapping_boxes(boxes, iou_thresh=0.5):
    """
    Find groups of boxes that overlap by more than iou_thresh OR where one box contains another.
    Returns list of groups, where each group is a list of overlapping/contained boxes.
    """
    if len(boxes) == 0:
        return []
    
    # Convert to list of boxes with indices
    boxes_with_indices = [(i, box) for i, box in enumerate(boxes)]
    used = set()
    overlapping_groups = []
    
    for i, (idx1, box1) in enumerate(boxes_with_indices):
        if idx1 in used:
            continue
        
        # Start a new group
        group = [box1]
        used.add(idx1)
        
        # Find all boxes that overlap with or contain this one
        for j, (idx2, box2) in enumerate(boxes_with_indices):
            if idx2 in used or idx1 == idx2:
                continue
            
            # Calculate IoU and containment
            x1_1, y1_1, x2_1, y2_1, _ = box1
            x1_2, y1_2, x2_2, y2_2, _ = box2
            
            ix1 = max(x1_1, x1_2)
            iy1 = max(y1_1, y1_2)
            ix2 = min(x2_1, x2_2)
            iy2 = min(y2_1, y2_2)
            
            if ix2 <= ix1 or iy2 <= iy1:
                iou = 0.0
            else:
                inter = (ix2 - ix1) * (iy2 - iy1)
                area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
                area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
                union = area1 + area2 - inter
                iou = inter / (union + 1e-8)
            
            # Check if one box contains the other
            box1_contains_box2 = (x1_1 <= x1_2 and y1_1 <= y1_2 and x2_1 >= x2_2 and y2_1 >= y2_2)
            box2_contains_box1 = (x1_2 <= x1_1 and y1_2 <= y1_1 and x2_2 >= x2_1 and y2_2 >= y2_1)
            
            # Group if IoU threshold met OR if one contains the other
            if iou > iou_thresh or box1_contains_box2 or box2_contains_box1:
                group.append(box2)
                used.add(idx2)
                if iou > iou_thresh:
                    print(f"[INFO] Box {idx1} overlaps with box {idx2} (IoU={iou:.3f})")
                elif box1_contains_box2:
                    print(f"[INFO] Box {idx1} contains box {idx2}")
                elif box2_contains_box1:
                    print(f"[INFO] Box {idx2} contains box {idx1}")
        
        # Only keep groups with 2 or more boxes
        if len(group) >= 2:
            overlapping_groups.append(group)
            print(f"[INFO] Created overlapping/containment group with {len(group)} boxes")
    
    return overlapping_groups

def create_parent_box(boxes):
    """
    Create a parent box that encompasses all boxes in the group.
    Uses the farthest corners to make it as big as possible.
    """
    if len(boxes) == 0:
        return None
    
    # Find the minimum and maximum coordinates
    x1s = [box[0] for box in boxes]
    y1s = [box[1] for box in boxes]
    x2s = [box[2] for box in boxes]
    y2s = [box[3] for box in boxes]
    
    parent_x1 = min(x1s)
    parent_y1 = min(y1s)
    parent_x2 = max(x2s)
    parent_y2 = max(y2s)
    
    # Use the highest confidence score from the group
    max_conf = max(box[4] for box in boxes)
    
    parent_box = [parent_x1, parent_y1, parent_x2, parent_y2, max_conf]
    print(f"[INFO] Created parent box: ({parent_x1}, {parent_y1}, {parent_x2}, {parent_y2}) with conf={max_conf:.3f}")
    
    return parent_box

def run_masking_on_parent_box(img_bgr, parent_box, model):
    """
    Run YOLO masking on a parent box region.
    Returns list of masks found in that region.
    """
    x1, y1, x2, y2, _ = map(int, parent_box)
    H, W = img_bgr.shape[:2]
    
    # Ensure coordinates are within image bounds
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(W - 1, x2)
    y2 = min(H - 1, y2)
    
    # Crop the parent box region
    crop = img_bgr[y1:y2+1, x1:x2+1]
    
    if crop.size == 0:
        print(f"[WARNING] Parent box crop is empty")
        return []
    
    # Run YOLO on the cropped region
    results = model(crop, verbose=False)
    result = results[0]
    
    masks = []
    if hasattr(result, "masks") and result.masks is not None and result.masks.data is not None:
        crop_masks = result.masks.data.cpu().numpy()
        crop_masks = (crop_masks > MASK_THRESH).astype(np.uint8)
        
        # Convert masks back to full image coordinates
        for mask in crop_masks:
            full_mask = np.zeros((H, W), dtype=np.uint8)
            mask_resized = cv2.resize(mask.astype(np.uint8), (x2-x1+1, y2-y1+1), interpolation=cv2.INTER_NEAREST)
            full_mask[y1:y2+1, x1:x2+1] = mask_resized
            masks.append(full_mask)
    
    print(f"[INFO] Found {len(masks)} masks in parent box region")
    return masks

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
    
    # Show final image before merging
    # COMMENTED OUT - Intermediate popup
    """
    print("[INFO] Showing final image before merging...")
    final_img = img_bgr.copy()
    
    # Draw original detections in green
    for i, box in enumerate(original_boxes):
        x1, y1, x2, y2, _ = map(int, box)
        cv2.rectangle(final_img, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Green for original
        cv2.putText(final_img, f"Orig{i}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    # Draw additional detections in blue
    for i, box in enumerate(filtered_additional):
        x1, y1, x2, y2, _ = map(int, box)
        cv2.rectangle(final_img, (x1, y1), (x2, y2), (255, 0, 0), 2)  # Blue for additional
        cv2.putText(final_img, f"Add{i}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
    
    cv2.imshow("Final Image Before Merging", final_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    """
    
    # Combine original and filtered additional detections
    final_boxes = original_boxes + filtered_additional
    final_masks = original_masks + filtered_additional_masks
    print(f"[INFO] Combined detections: {len(original_boxes)} original + {len(filtered_additional)} additional = {len(final_boxes)} total")
    
    # Step 4: Combine boxes that are 95% the same size and location
    if len(final_boxes) > 0:
        final_boxes = combine_similar_boxes(final_boxes, size_location_thresh=0.95)
        print(f"[INFO] After size/location combination: {len(final_boxes)} boxes")
    
    # Show the image after 95% box merging
    # COMMENTED OUT - Intermediate popup
    """
    print("[INFO] Showing image after 95% box merging...")
    merged_img = img_bgr.copy()
    
    # Draw all remaining boxes after merging
    for i, box in enumerate(final_boxes):
        x1, y1, x2, y2, conf = map(int, box)
        cv2.rectangle(merged_img, (x1, y1), (x2, y2), (0, 255, 255), 2)  # Yellow for merged boxes
        cv2.putText(merged_img, f"Merged{i} ({conf:.2f})", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    cv2.imshow("After 95% Box Merging", merged_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    """
    
    # Step 5: Find overlapping boxes and create parent boxes for masking
    # COMMENTED OUT - Blue box parent logic
    """
    print("[INFO] Finding overlapping boxes and creating parent boxes...")
    overlapping_groups = find_overlapping_boxes(final_boxes, iou_thresh=IOU_THRESH)
    
    if overlapping_groups:
        print(f"[INFO] Found {len(overlapping_groups)} groups of overlapping boxes")
        
        # Create parent boxes and run masking
        parent_boxes = []
        parent_masks = []
        
        for i, group in enumerate(overlapping_groups):
            print(f"[INFO] Processing overlapping group {i+1}/{len(overlapping_groups)} with {len(group)} boxes...")
            
            # Create parent box (farthest corners)
            parent_box = create_parent_box(group)
            parent_boxes.append(parent_box)
            
            # Run YOLO masking on parent box
            masks = run_masking_on_parent_box(img_bgr, parent_box, model)
            parent_masks.extend(masks)
            
            print(f"[INFO] Group {i+1}: Parent box created, found {len(masks)} masks")
        
        # Show image with cleaned up object boxes
        print("[INFO] Showing cleaned up object detection...")
        cleaned_img = img_bgr.copy()
        
        # Create a set of boxes that are part of overlapping groups (to exclude them)
        overlapping_box_indices = set()
        for group in overlapping_groups:
            for box in group:
                # Find the index of this box in final_boxes
                for i, final_box in enumerate(final_boxes):
                    if np.array_equal(box, final_box):
                        overlapping_box_indices.add(i)
                        break
        
        # Draw non-overlapping yellow boxes (keep original style)
        for i, box in enumerate(final_boxes):
            if i not in overlapping_box_indices:
                x1, y1, x2, y2, conf = map(int, box)
                cv2.rectangle(cleaned_img, (x1, y1), (x2, y2), (0, 255, 255), 2)  # Yellow
                cv2.putText(cleaned_img, f"Box{i}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # Draw blue boxes around distinct objects found in parent regions (same style as others)
        for i, mask in enumerate(parent_masks):
            # Find mask bounding box
            ys, xs = np.where(mask > 0)
            if len(xs) > 0 and len(ys) > 0:
                mask_x1, mask_y1, mask_x2, mask_y2 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
                cv2.rectangle(cleaned_img, (mask_x1, mask_y1), (mask_x2, mask_y2), (255, 0, 0), 2)  # Blue, same thickness
                cv2.putText(cleaned_img, f"Object{i}", (mask_x1, mask_y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        
        cv2.imshow("Cleaned Object Detection", cleaned_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("[INFO] No overlapping boxes found")
    """
    
    return final_boxes, final_masks

def detect_fast(path):
    model = YOLO(MODEL_PATH)
    img_bgr = load_image(path)

    print("[INFO] Starting multi-test detection pipeline...")
    
    # Run multi-test detection
    props, props_masks = yolo_multi_test_detection(img_bgr, model)
    
    print(f"[INFO] Filtering {len(props)} voted proposals...")
    # Filter invalid / tiny (adaptive)
    H,W = img_bgr.shape[:2]
    min_area_px = max(16, int(0.00002 * H * W))
    filt = []
    for b in props:
        x1,y1,x2,y2,sc = b
        if x2<=x1 or y2<=y1: continue
        area = (x2-x1+1)*(y2-y1+1)
        if area < min_area_px: continue
        filt.append(b)
    if not filt:
        print("[INFO] No valid proposals after filtering.")
        return np.empty((0,5), dtype=np.float32), img_bgr
    filt = np.array(filt, dtype=np.float32)

    print(f"[INFO] Running PEG-Dedup on {len(filt)} proposals...")
    # Final deduplication
    dedup = peg_dedup(
        filt,
        img_bgr,
        contain_t=0.7,
        iou_t=0.6,
        center_t=0.5,
        cos_t=0.8,
        child_keep_ratio=0.4,
        union_similar=True
    )
    print(f"[INFO] Deduplication complete. {len(dedup)} objects remain.")

    # (optional) expand boxes to edges if you still want
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    exp = np.array([expand_box(img_gray, b) for b in dedup], dtype=np.float32)

    print("[INFO] Multi-test detection pipeline complete.")
    return exp, img_bgr

def mask_iou(mask1, mask2):
    intersection = np.logical_and(mask1, mask2).sum()
    union = np.logical_or(mask1, mask2).sum()
    return intersection / (union + 1e-6)

def merge_masks(masks, iou_thresh=0.5):
    used = np.zeros(len(masks), dtype=bool)
    merged = []
    for i in range(len(masks)):
        if used[i]:
            continue
        m = masks[i].copy()
        for j in range(i+1, len(masks)):
            if used[j]:
                continue
            if mask_iou(m, masks[j]) > iou_thresh:
                m = np.logical_or(m, masks[j])
                used[j] = True
        merged.append(m)
    return merged

def draw_masks_on_image(img, masks, alpha=0.6):
    """
    Draws segmentation masks on the image with different colors for each object.
    """
    if masks is None or len(masks) == 0:
        return img
    overlay = img.copy()
    H_img, W_img = img.shape[:2]
    for i, mask in enumerate(masks):
        # Use a seeded random color for each object for consistency
        np.random.seed(i)
        color = np.random.randint(0, 255, (3,), dtype=np.uint8)
        # Resize mask to image size if needed
        if mask.shape != (H_img, W_img):
            mask = cv2.resize(mask.astype(np.uint8), (W_img, H_img), interpolation=cv2.INTER_NEAREST)
        mask = mask.astype(bool)
        overlay[mask] = (overlay[mask] * (1 - alpha) + color * alpha).astype(np.uint8)
    return overlay

def expand_box_with_padding(box, img_shape, pad_frac):
    H, W = img_shape[:2]
    x1, y1, x2, y2, _ = box
    w = x2 - x1
    h = y2 - y1
    pad_w = int(w * pad_frac)
    pad_h = int(h * pad_frac)
    nx1 = max(0, int(x1 - pad_w))
    ny1 = max(0, int(y1 - pad_h))
    nx2 = min(W - 1, int(x2 + pad_w))
    ny2 = min(H - 1, int(y2 + pad_h))
    return nx1, ny1, nx2, ny2

def crop_and_refeed_for_mask(img_bgr, box, model, mask_thresh, pad_fracs=[0.1,0.2,0.3,0.4,0.5], area_growth_thresh=0.05, filter_func=None):
    H, W = img_bgr.shape[:2]
    best_mask = None
    best_area = 0
    best_coords = None
    prev_area = 0
    for pad_frac in pad_fracs:
        nx1, ny1, nx2, ny2 = expand_box_with_padding(box, img_bgr.shape, pad_frac)
        crop = img_bgr[ny1:ny2+1, nx1:nx2+1]
        if filter_func is not None:
            crop = filter_func(crop)
        results = model(crop)
        result = results[0]
        if hasattr(result, "masks") and result.masks is not None and result.masks.data is not None:
            masks = result.masks.data.cpu().numpy()
            masks = (masks > mask_thresh).astype(np.uint8)
            # Find the mask with the largest area
            for mask in masks:
                area = mask.sum()
                if area > best_area:
                    best_mask = mask
                    best_area = area
                    best_coords = (nx1, ny1, nx2, ny2)
            # Check if area increased significantly
            if prev_area > 0 and (best_area - prev_area) / (prev_area + 1e-6) < area_growth_thresh:
                break
            prev_area = best_area
    if best_mask is not None and best_coords is not None:
        # Resize mask to crop size, then place in full image
        nx1, ny1, nx2, ny2 = best_coords
        mask_resized = cv2.resize(best_mask.astype(np.uint8), (nx2-nx1+1, ny2-ny1+1), interpolation=cv2.INTER_NEAREST)
        full_mask = np.zeros((H, W), dtype=np.uint8)
        full_mask[ny1:ny2+1, nx1:nx2+1] = mask_resized
        return full_mask
    return None

def canny_filter(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    edges_col = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    # Overlay edges on original image for context
    return cv2.addWeighted(img, 0.7, edges_col, 0.3, 0)

def phash_from_mask(img, mask):
    # img: original image (H, W, 3)
    # mask: binary mask (H, W)
    if mask.shape != img.shape[:2]:
        mask = cv2.resize(mask.astype(np.uint8), (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
    masked = cv2.bitwise_and(img, img, mask=mask.astype(np.uint8))
    gray = cv2.cvtColor(masked, cv2.COLOR_BGR2GRAY)
    ys, xs = np.where(mask)
    if len(xs) == 0 or len(ys) == 0:
        return None
    x1, y1, x2, y2 = xs.min(), ys.min(), xs.max(), ys.max()
    crop = gray[y1:y2+1, x1:x2+1]
    crop = cv2.resize(crop, (32, 32), interpolation=cv2.INTER_AREA)
    dct = cv2.dct(np.float32(crop))
    dct_low = dct[:8, :8].flatten()[1:]
    median = np.median(dct_low)
    bits = (dct_low > median).astype(np.uint8)
    hash64 = 0
    for b in bits:
        hash64 = (hash64 << 1) | int(b)
    return hash64

def hamming(a, b):
    return bin(a ^ b).count('1')

def mask_containment(maskA, maskB):
    # Fraction of maskA inside maskB
    inter = np.logical_and(maskA, maskB).sum()
    areaA = maskA.sum()
    if areaA == 0:
        return 0.0
    return inter / areaA

def phash_from_mask_intersection(img, maskA, maskB):
    # Compute p-hash for the intersection region of two masks
    intersection = np.logical_and(maskA, maskB)
    if intersection.sum() == 0:
        return None
    if intersection.shape != img.shape[:2]:
        intersection = cv2.resize(intersection.astype(np.uint8), (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
    masked = cv2.bitwise_and(img, img, mask=intersection.astype(np.uint8))
    gray = cv2.cvtColor(masked, cv2.COLOR_BGR2GRAY)
    ys, xs = np.where(intersection)
    if len(xs) == 0 or len(ys) == 0:
        return None
    x1, y1, x2, y2 = xs.min(), ys.min(), xs.max(), ys.max()
    crop = gray[y1:y2+1, x1:x2+1]
    crop = cv2.resize(crop, (32, 32), interpolation=cv2.INTER_AREA)
    dct = cv2.dct(np.float32(crop))
    dct_low = dct[:8, :8].flatten()[1:]
    median = np.median(dct_low)
    bits = (dct_low > median).astype(np.uint8)
    hash64 = 0
    for b in bits:
        hash64 = (hash64 << 1) | int(b)
    return hash64

def merge_masks_iou_phash(masks, img_bgr, iou_thresh=0.5, hamming_thresh=16):
    masks = [m.copy() for m in masks]
    changed = True
    while changed:
        changed = False
        N = len(masks)
        used = [False] * N
        new_masks = []
        for i in range(N):
            if used[i]: continue
            mA = masks[i]
            merged = False
            for j in range(i+1, N):
                if used[j]: continue
                mB = masks[j]
                inter = np.logical_and(mA, mB).sum()
                union = np.logical_or(mA, mB).sum()
                iou = inter / (union + 1e-6)
                if iou > iou_thresh:
                    phashA = phash_from_mask_intersection(img_bgr, mA, mB)
                    phashB = phash_from_mask_intersection(img_bgr, mB, mA)
                    if phashA is not None and phashB is not None and hamming(phashA, phashB) <= hamming_thresh:
                        mA = np.logical_or(mA, mB).astype(np.uint8)
                        used[j] = True
                        changed = True
                        merged = True
            new_masks.append(mA)
            used[i] = True
        masks = new_masks
    return masks

def draw_and_save():
    # COMMENTED OUT - Old merge logic with mask recovery
    """
    boxes, img_bgr = detect_fast(INPUT_IMAGE)
    model = YOLO(MODEL_PATH)
    
    print("[INFO] Running new merge logic...")
    
    # Step 1: Run YOLO on whole image to get masks for all detections
    print("[INFO] Step 1: Running YOLO on whole image to get initial masks...")
    results = model(img_bgr)
    result = results[0]
    
    # Get masks from the whole image detection
    whole_image_masks = []
    if hasattr(result, "masks") and result.masks is not None and result.masks.data is not None:
        whole_image_masks = result.masks.data.cpu().numpy()
        whole_image_masks = (whole_image_masks > MASK_THRESH).astype(np.uint8)
    
    # Associate boxes with masks from whole image
    associations = associate_boxes_with_masks(boxes, whole_image_masks, iou_thresh=0.3)
    
    # Step 2: Process boxes without masks
    print("[INFO] Step 2: Processing boxes without masks...")
    boxes_without_masks = []
    boxes_with_masks = []
    
    for i, box in enumerate(boxes):
        if associations[i] is None:
            boxes_without_masks.append((i, box))
        else:
            boxes_with_masks.append((i, box))
    
    print(f"[INFO] Found {len(boxes_with_masks)} boxes with masks, {len(boxes_without_masks)} without masks")
    
    # Step 3: For boxes without masks, zoom in and try to get masks
    recovered_masks = []
    recovered_associations = []
    
    for idx, (i, box) in enumerate(boxes_without_masks):
        print(f"[INFO] Processing box {i} without mask ({idx+1}/{len(boxes_without_masks)})...")
        
        # Zoom in on the box with padding
        x1, y1, x2, y2, _ = box
        w, h = x2 - x1, y2 - y1
        pad_w = int(w * 0.2)  # 20% padding
        pad_h = int(h * 0.2)
        
        # Ensure we don't go outside image bounds
        crop_x1 = max(0, int(x1 - pad_w))
        crop_y1 = max(0, int(y1 - pad_h))
        crop_x2 = min(img_bgr.shape[1] - 1, int(x2 + pad_w))
        crop_y2 = min(img_bgr.shape[0] - 1, int(y2 + pad_h))
        
        # Crop the region
        cropped_img = img_bgr[crop_y1:crop_y2+1, crop_x1:crop_x2+1]
        
        # Run YOLO on the cropped region
        cropped_results = model(cropped_img)
        cropped_result = cropped_results[0]
        
        # Check if we got any masks
        if hasattr(cropped_result, "masks") and cropped_result.masks is not None and cropped_result.masks.data is not None:
            cropped_masks = cropped_result.masks.data.cpu().numpy()
            cropped_masks = (cropped_masks > MASK_THRESH).astype(np.uint8)
            
            if len(cropped_masks) > 0:
                # Take the largest mask
                largest_mask_idx = np.argmax([mask.sum() for mask in cropped_masks])
                mask = cropped_masks[largest_mask_idx]
                
                # Resize mask back to original image coordinates
                full_mask = np.zeros((img_bgr.shape[0], img_bgr.shape[1]), dtype=np.uint8)
                mask_resized = cv2.resize(mask.astype(np.uint8), (crop_x2-crop_x1+1, crop_y2-crop_y1+1), interpolation=cv2.INTER_NEAREST)
                full_mask[crop_y1:crop_y2+1, crop_x1:crop_x2+1] = mask_resized
                
                recovered_masks.append(full_mask)
                recovered_associations.append(i)
                print(f"[INFO] Successfully recovered mask for box {i}")
            else:
                print(f"[INFO] No masks found for box {i}")
        else:
            print(f"[INFO] No masks found for box {i}")
    
    # Step 4: Create final image with proper coloring
    print("[INFO] Step 4: Creating final image...")
    final_img = img_bgr.copy()
    
    # Draw masks from whole image detection
    if len(whole_image_masks) > 0:
        final_img = draw_masks_on_image(final_img, whole_image_masks)
    
    # Draw recovered masks
    if len(recovered_masks) > 0:
        final_img = draw_masks_on_image(final_img, recovered_masks)
    
    # Draw boxes with appropriate colors
    for i, box in enumerate(boxes):
        x1, y1, x2, y2, _ = map(int, box)
        
        if associations[i] is not None:
            # Box has mask from whole image - color green
            cv2.rectangle(final_img, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Green
            cv2.putText(final_img, f"Mask{i}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        elif i in recovered_associations:
            # Box got mask from zoom - color orange
            cv2.rectangle(final_img, (x1, y1), (x2, y2), (0, 140, 255), 2)  # Orange
            cv2.putText(final_img, f"Recovered{i}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 140, 255), 1)
        else:
            # Box has no mask - color red
            cv2.rectangle(final_img, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Red
            cv2.putText(final_img, f"NoMask{i}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    
    # Draw yellow boxes around all masks (both whole image and recovered)
    yellow_boxes = []
    
    # Add boxes for whole image masks
    for i, box in enumerate(boxes):
        if associations[i] is not None:
            mask_idx = associations[i]
            if mask_idx < len(whole_image_masks):
                mask = whole_image_masks[mask_idx]
                # Find mask bounding box
                ys, xs = np.where(mask > 0)
                if len(xs) > 0 and len(ys) > 0:
                    mask_x1, mask_y1, mask_x2, mask_y2 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
                    yellow_boxes.append((mask_x1, mask_y1, mask_x2, mask_y2))
    
    # Add boxes for recovered masks
    for i, mask in enumerate(recovered_masks):
        ys, xs = np.where(mask > 0)
        if len(xs) > 0 and len(ys) > 0:
            mask_x1, mask_y1, mask_x2, mask_y2 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
            yellow_boxes.append((mask_x1, mask_y1, mask_x2, mask_y2))
    
    # Draw yellow boxes
    for x1, y1, x2, y2 in yellow_boxes:
        cv2.rectangle(final_img, (x1, y1), (x2, y2), (0, 255, 255), 2)  # Yellow in BGR
    
    # Show the final image
    cv2.imshow("YOLO Segmentation Results - New Logic", final_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    print(f"[INFO] Final result: {len(boxes)} total boxes")
    print(f"  - {len(boxes_with_masks)} with masks (green)")
    print(f"  - {len(recovered_associations)} recovered masks (orange)")
    print(f"  - {len(boxes_without_masks) - len(recovered_associations)} without masks (red)")
    """
    
    # NEW: Simple pipeline that stops at 95% box merging
    print("[INFO] Running simplified pipeline that stops at 95% box merging...")
    boxes, img_bgr = detect_fast(INPUT_IMAGE)
    
    # Show final result with yellow boxes after 95% merging
    final_img = img_bgr.copy()
    for i, box in enumerate(boxes):
        x1, y1, x2, y2, conf = map(int, box)
        cv2.rectangle(final_img, (x1, y1), (x2, y2), (0, 255, 255), 2)  # Yellow
        cv2.putText(final_img, f"Final{i} ({conf:.2f})", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    cv2.imshow("Final Detection Results (95% Merged)", final_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    print(f"[INFO] Final result: {len(boxes)} boxes after 95% similarity merging")
    
    # Post-processing: Crop, normalize, assign IDs, and encode
    print("[INFO] Starting post-processing pipeline...")
    
    # 1. Crop & normalize each detected segment
    cropped_segments = []
    for i, box in enumerate(boxes):
        x1, y1, x2, y2, conf = map(int, box)
        
        # Ensure coordinates are within image bounds
        H, W = img_bgr.shape[:2]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(W - 1, x2)
        y2 = min(H - 1, y2)
        
        # Crop the segment
        segment = img_bgr[y1:y2+1, x1:x2+1]
        
        if segment.size == 0:
            print(f"[WARNING] Empty segment for box {i}")
            continue
        
        # Normalize to 256px longest side while maintaining aspect ratio
        h, w = segment.shape[:2]
        longest_side = max(h, w)
        scale = 256.0 / longest_side
        
        new_h = int(h * scale)
        new_w = int(w * scale)
        
        # Resize maintaining aspect ratio
        normalized_segment = cv2.resize(segment, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        cropped_segments.append({
            'index': i,
            'box': [x1, y1, x2, y2],
            'confidence': conf,
            'segment': normalized_segment,
            'original_size': (h, w),
            'normalized_size': (new_h, new_w)
        })
        
        print(f"[INFO] Segment {i}: {h}x{w} -> {new_h}x{new_w} (scale={scale:.3f})")
    
    # 2. Assign unique 5-digit IDs
    import random
    import base64
    import json
    
    # Generate unique 5-digit IDs
    used_ids = set()
    for segment_data in cropped_segments:
        while True:
            # Generate 5-digit ID
            segment_id = str(random.randint(10000, 99999))
            if segment_id not in used_ids:
                used_ids.add(segment_id)
                segment_data['id'] = segment_id
                break
    
    # 3. Encode & package
    encoded_segments = []
    for segment_data in cropped_segments:
        # Convert segment to base64
        success, buffer = cv2.imencode('.jpg', segment_data['segment'])
        if success:
            base64_encoded = base64.b64encode(buffer).decode('utf-8')
            
            # Create package
            package = {
                'index': segment_data['index'],
                'original_box': segment_data['box'],
                'original_size': segment_data['original_size'],
                'normalized_size': segment_data['normalized_size'],
                'image': base64_encoded
            }
            
            encoded_segments.append(package)
            print(f"[INFO] Encoded segment {segment_data['index']} with ID {segment_data['id']}")
        else:
            print(f"[ERROR] Failed to encode segment {segment_data['index']}")
    
    # 4. Print JSON output
    print("\n" + "="*50)
    print("FINAL JSON OUTPUT:")
    print("="*50)
    
    output_json = {
        'total_segments': len(encoded_segments),
        'segments': encoded_segments
    }
    
    print(json.dumps(output_json, indent=2))
    print("="*50)
    
    print(f"[INFO] Post-processing complete: {len(encoded_segments)} segments processed")

def associate_boxes_with_masks(boxes, masks, iou_thresh=0.3):
    # For each box, find if it overlaps with any mask
    associations = []
    mask_boxes = []
    for mask in masks:
        ys, xs = np.where(mask)
        if len(xs) == 0 or len(ys) == 0:
            mask_boxes.append(None)
        else:
            x1, y1, x2, y2 = xs.min(), ys.min(), xs.max(), ys.max()
            mask_boxes.append((x1, y1, x2, y2))
    for box in boxes:
        x1, y1, x2, y2, _ = map(int, box)
        found = False
        for i, mbox in enumerate(mask_boxes):
            if mbox is None:
                continue
            mx1, my1, mx2, my2 = mbox
            # Compute IoU
            ix1 = max(x1, mx1)
            iy1 = max(y1, my1)
            ix2 = min(x2, mx2)
            iy2 = min(y2, my2)
            iw = max(0, ix2-ix1+1)
            ih = max(0, iy2-iy1+1)
            inter = iw * ih
            areaA = (x2-x1+1)*(y2-y1+1)
            areaB = (mx2-mx1+1)*(my2-my1+1)
            iou = inter / float(areaA + areaB - inter + 1e-6)
            if iou > iou_thresh:
                associations.append(i)
                found = True
                break
        if not found:
            associations.append(None)
    return associations

# ------------------ MAIN ------------------
if __name__ == "__main__":
    draw_and_save()
