import os
import time
import cv2
import numpy as np
from ultralytics import YOLO

# Paths
MODEL_PATH = 'yolo11n-seg.pt'
IMAGE_PATH = 'C:/Users/Arnav/Downloads/IMG_4025.jpg'
OUTPUT_DIR = 'yoloimprvoedoutput'
OUTPUT_IMAGE = os.path.join(OUTPUT_DIR, 'IMG_4025_exact_server_output.png')

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === EXACT PARAMETERS FROM GEMINISERVER.PY ===
SCALES = (640, 1280, 1920)
CONF_THRESH = 0.04     # much lower confidence for better object detection
EDGE_CONF_THRESH_CANNY = 0.003  # even lower for better edge-based detection
EDGE_CONF_THRESH_SOBEL = 0.02   # even lower for better detection
IOU_NMS = 0.9      # high IoU to avoid early suppression in initial YOLO pass
MIN_AREA_PX = 8        # even lower minimum area to catch small objects
EDGE_THRESH = 15       # std dev threshold in edge band for expansion
NMS_IOU = 0.1      # stricter IoU for final NMS
COLOR_T = 0.05    # lower means more aggressive drop of visually similar overlaps
MASK_THRESH = 0.01     # threshold for mask binarization
FEATURE_SIM_THRESH = 0.75  # cosine similarity threshold for feature matching

# Clustering thresholds
IOU_THRESH = 0.3         # 0.6–0.8: higher = only very overlapping boxes cluster
CENTER_DIST_FRAC = 0.3  # 0.2–0.3: smaller = boxes must be nearly concentric
AREA_RATIO_THRESH = 0.6  # 0.5–0.7: prevents merging tiny with huge
COLOR_THRESH = 0.3      # 0.1–0.2: lower = only very similar textures/colors merge

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

def edge_overlay_canny(img, alpha=0.5):
    """Canny edge detection overlay - EXACT from geminiserver.py"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    edges_col = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    overlay = cv2.addWeighted(img, 1 - alpha, edges_col, alpha, 0)
    return overlay

def edge_overlay_sobel(img):
    """Sobel edge detection - EXACT from geminiserver.py"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    sobel = cv2.magnitude(sobelx, sobely)
    sobel = np.uint8(np.clip(sobel, 0, 255))
    sobel_3ch = cv2.cvtColor(sobel, cv2.COLOR_GRAY2BGR)
    return sobel_3ch

def run_detection_test(img_bgr, model, test_name, transform_func=None, conf_thresh=None):
    """Run a single detection test - EXACT from geminiserver.py"""
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
            
            # No hard-coded object detection - let the model detect naturally
            # Only apply minimal confidence boosting for very low confidence detections
            if score < 0.02:
                score *= 1.1  # Small boost for very low confidence detections
            
            boxes.append([x1, y1, x2, y2, score])
        
        # Collect masks (if available)
        if hasattr(res[0], "masks") and res[0].masks is not None and res[0].masks.data is not None:
            m = res[0].masks.data.cpu().numpy()
            m = (m > MASK_THRESH).astype(np.uint8)
            masks.extend(m)
    
    return boxes, masks

def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    a_norm = a / (np.linalg.norm(a) + 1e-8)
    b_norm = b / (np.linalg.norm(b) + 1e-8)
    return np.dot(a_norm, b_norm)

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

def extract_advanced_features(box, mask=None, img_bgr=None):
    """
    Extract lightweight advanced features for semantic understanding.
    Optimized for speed while maintaining semantic information.
    """
    x1, y1, x2, y2, conf = box
    w, h = x2 - x1, y2 - y1
    area = w * h
    aspect_ratio = w / (h + 1e-6)
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    
    # Basic geometric features
    features = [conf, area, aspect_ratio, center_x, center_y, w, h]
    
    # No hard-coded object features - keep it generic
    # Add generic shape complexity instead
    shape_complexity = abs(aspect_ratio - 1.0)  # How far from square
    features.append(shape_complexity)
    
    # Mask-based features if available (simplified)
    if mask is not None:
        mask_area = np.sum(mask)
        mask_ratio = mask_area / (area + 1e-6)
        features.extend([mask_area, mask_ratio])
    else:
        features.extend([0, 0])
    
    # Ultra-lightweight color features (only if image available and region is small)
    if img_bgr is not None and area < 150000:  # Increased area limit for monitor detection
        try:
            x1_int, y1_int, x2_int, y2_int = int(x1), int(y1), int(x2), int(y2)
            x1_int = max(0, x1_int)
            y1_int = max(0, y1_int)
            x2_int = min(img_bgr.shape[1], x2_int)
            y2_int = min(img_bgr.shape[0], y2_int)
            
            if x2_int > x1_int and y2_int > y1_int and (x2_int - x1_int) * (y2_int - y1_int) < 15000:
                region = img_bgr[y1_int:y2_int, x1_int:x2_int]
                if region.size > 0:
                    # Simple color features (mean RGB only)
                    mean_color = np.mean(region, axis=(0, 1))
                    features.extend([mean_color[0], mean_color[1], mean_color[2]])
                else:
                    features.extend([0, 0, 0])
            else:
                features.extend([0, 0, 0])
        except:
            features.extend([0, 0, 0])
    else:
        features.extend([0, 0, 0])
    
    # Pad to consistent size
    if len(features) < 16:
        features.extend([0] * (16 - len(features)))
    else:
        features = features[:16]
    
    return np.array(features, dtype=np.float32)

def calculate_semantic_similarity(box1, box2, mask1=None, mask2=None, img_bgr=None):
    """
    Enhanced semantic similarity with object composition awareness.
    """
    # Quick geometric checks first
    x1_1, y1_1, x2_1, y2_1, conf1 = box1
    x1_2, y1_2, x2_2, y2_2, conf2 = box2
    
    # Center distance (fast check)
    center1 = ((x1_1 + x2_1) / 2, (y1_1 + y2_1) / 2)
    center2 = ((x1_2 + x2_2) / 2, (y1_2 + y2_2) / 2)
    center_distance = np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
    
    # Early exit if too far apart
    if center_distance > 300:  # Increased for better part merging
        return 0.0, {'center_distance': center_distance}
    
    # Size similarity
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    size_ratio = min(area1, area2) / (max(area1, area2) + 1e-8)
    
    # Box IoU (fast)
    box_iou = _iou(box1, box2)
    
    # Object type awareness (based on size and aspect ratio)
    aspect1 = (x2_1 - x1_1) / (y2_1 - y1_1 + 1e-6)
    aspect2 = (x2_2 - x1_2) / (y2_2 - y1_2 + 1e-6)
    aspect_similarity = 1.0 - abs(aspect1 - aspect2) / max(aspect1, aspect2)
    
    # Object composition detection
    # Check if one box is contained within or significantly overlaps the other
    containment_score = 0.0
    if box_iou > 0.1:
        # Calculate how much one box contains the other
        intersection_area = max(0, min(x2_1, x2_2) - max(x1_1, x1_2)) * max(0, min(y2_1, y2_2) - max(y1_1, y1_2))
        if intersection_area > 0:
            # Check if one is mostly contained in the other
            containment1 = intersection_area / area1
            containment2 = intersection_area / area2
            containment_score = max(containment1, containment2)
    
    # Quick feature similarity (only if boxes overlap significantly)
    features1 = None
    features2 = None
    if box_iou > 0.05:  # Lowered threshold for part detection
        features1 = extract_advanced_features(box1, mask1, img_bgr)
        features2 = extract_advanced_features(box2, mask2, img_bgr)
        feature_sim = cosine_similarity(features1, features2)
    else:
        feature_sim = 0.0
    
    # Confidence similarity
    conf_sim = 1.0 - abs(conf1 - conf2)
    
    # Enhanced similarity score with object composition awareness
    similarity_score = (
        0.35 * box_iou +          # Increased spatial overlap weight
        0.25 * feature_sim +      # Feature similarity
        0.2 * size_ratio +        # Size similarity
        0.15 * aspect_similarity + # Aspect ratio similarity
        0.05 * containment_score  # Reduced object composition weight
    )
    
    # Boost similarity for potential object parts
    if containment_score > 0.1 and box_iou > 0.01:  # Much lower thresholds
        similarity_score *= 2.0  # Much stronger boost for likely object parts
    
    # Generic object handling - no hard-coded object types
    # Use shape complexity to determine if objects should be merged
    if features1 is not None and features2 is not None and len(features1) > 7 and len(features2) > 7:
        shape_diff = abs(features1[7] - features2[7])  # Shape complexity difference
        if shape_diff > 0.5:  # Very different shapes
            similarity_score *= 0.8  # Reduce merging for very different shapes
    
    return similarity_score, {
        'box_iou': box_iou,
        'feature_sim': feature_sim,
        'size_ratio': size_ratio,
        'aspect_similarity': aspect_similarity,
        'containment_score': containment_score,
        'conf_sim': conf_sim,
        'center_distance': center_distance
    }

def is_duplicate_detection(box1, box2, mask1, mask2, features1, features2, mask_iou_thresh=0.5, feature_thresh=0.85):
    """
    Enhanced duplicate detection using semantic understanding.
    """
    # Use the original simple features for backward compatibility
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

def combine_similar_boxes(boxes, iou_thresh=0.3, img_bgr=None):  # Much lower base threshold
    """
    Enhanced merge using semantic similarity with object composition awareness.
    """
    if len(boxes) == 0:
        return boxes
    boxes = np.array(boxes, dtype=np.float32)
    sorted_indices = np.argsort(-boxes[:, 4])
    boxes_sorted = boxes[sorted_indices]
    used = np.zeros(len(boxes_sorted), dtype=bool)
    merged_boxes = []
    
    for i in range(len(boxes_sorted)):
        if used[i]:
            continue
        current_box = boxes_sorted[i]
        group = [current_box]
        used[i] = True
        
        for j in range(i + 1, len(boxes_sorted)):
            if used[j]:
                continue
            other_box = boxes_sorted[j]
            
            # Use semantic similarity for more intelligent merging
            similarity_score, details = calculate_semantic_similarity(
                current_box, other_box, img_bgr=img_bgr
            )
            
            # Enhanced adaptive threshold for object composition
            adaptive_threshold = iou_thresh
            
            # Enhanced handling for object parts (like chair parts)
            if 'containment_score' in details and details['containment_score'] > 0.1:  # Much lower threshold
                # If one object is significantly contained in another, be more aggressive
                adaptive_threshold *= 0.3  # Much more aggressive
                if 'box_iou' in details and details['box_iou'] > 0.01:  # Much lower threshold
                    adaptive_threshold *= 0.5  # Much more aggressive for overlapping parts
            
            # Special handling for large overlapping objects (like chair parts)
            if 'box_iou' in details and 'size_ratio' in details:
                if details['box_iou'] > 0.1 and details['size_ratio'] > 0.1:  # Much lower thresholds
                    adaptive_threshold *= 0.3  # Much more aggressive for large overlapping objects
                
                # Extra aggressive for very large overlapping objects (chair parts)
                if details['box_iou'] > 0.05 and details['size_ratio'] > 0.05:
                    adaptive_threshold *= 0.2  # Very aggressive for chair parts
            
            # Size-based adjustments
            if 'size_ratio' in details and details['size_ratio'] < 0.3:  # Very different sizes
                adaptive_threshold *= 0.8
            if 'center_distance' in details and details['center_distance'] > 100:  # Far apart
                adaptive_threshold *= 1.2
            if 'feature_sim' in details and details['feature_sim'] < 0.5:  # Very different features
                adaptive_threshold *= 1.3
            
            # Merge if similarity is high enough
            if similarity_score >= adaptive_threshold:
                group.append(other_box)
                used[j] = True
        
                    # For object composition, prefer the largest box (most complete object)
            if len(group) > 1:
                # Calculate areas and keep the largest
                areas = [(b[2] - b[0]) * (b[3] - b[1]) for b in group]
                best_idx = np.argmax(areas)
                best_box = group[best_idx]
                
                # Extra check: if we have very large overlapping objects, merge them more aggressively
                if len(group) > 2:  # Multiple overlapping objects
                    # Check if they're all large (likely chair parts)
                    large_objects = [b for b in group if (b[2] - b[0]) * (b[3] - b[1]) > 100000]
                    if len(large_objects) > 1:
                        # Merge all large overlapping objects into one
                        x1 = min(b[0] for b in large_objects)
                        y1 = min(b[1] for b in large_objects)
                        x2 = max(b[2] for b in large_objects)
                        y2 = max(b[3] for b in large_objects)
                        max_conf = max(b[4] for b in large_objects)
                        best_box = [x1, y1, x2, y2, max_conf]
            else:
                best_box = group[0]
        
        merged_boxes.append(best_box)
    
    result = np.array(merged_boxes, dtype=np.float32)
    return result

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

def merge_overlapping_boxes_union(boxes, iou_thresh=0.3):
    """
    Merge groups of boxes that overlap by IOU > iou_thresh by taking the union (bounding rectangle) of each group.
    Confidence is set to the max confidence in the group.
    """
    if len(boxes) == 0:
        return boxes
    boxes = np.array(boxes, dtype=np.float32)
    used = np.zeros(len(boxes), dtype=bool)
    merged_boxes = []
    for i in range(len(boxes)):
        if used[i]:
            continue
        group = [boxes[i]]
        used[i] = True
        for j in range(i + 1, len(boxes)):
            if used[j]:
                continue
            if _iou(boxes[i], boxes[j]) > iou_thresh:
                group.append(boxes[j])
                used[j] = True
        # Merge group by union
        x1 = min(b[0] for b in group)
        y1 = min(b[1] for b in group)
        x2 = max(b[2] for b in group)
        y2 = max(b[3] for b in group)
        conf = max(b[4] for b in group)
        merged_boxes.append([x1, y1, x2, y2, conf])
    return np.array(merged_boxes, dtype=np.float32)

def yolo_multi_test_detection(img_bgr, model):
    """
    Run detection with original image first, then additional tests with low confidence.
    Use backbone features to determine if new detections are duplicates.
    Times each major step for performance analysis.
    """
    import time
    t0 = time.perf_counter()
    # Stage 1: Original detection with normal confidence
    t_orig_start = time.perf_counter()
    original_boxes, original_masks = run_detection_test(img_bgr, model, "Original (conf=0.25)", conf_thresh=CONF_THRESH)
    t_orig_end = time.perf_counter()
    print(f"[Timing] Original detection: {t_orig_end-t_orig_start:.3f} seconds")
    
    if len(original_boxes) == 0:
        return []
    # Extract features for original detections
    t_feat1_start = time.perf_counter()
    original_features = extract_backbone_features(model, img_bgr, original_boxes)
    t_feat1_end = time.perf_counter()
    print(f"[Timing] Feature extraction (original): {t_feat1_end-t_feat1_start:.3f} seconds")
    # Stage 2: Additional tests with low confidence
    additional_boxes = []
    additional_masks = []
    # Test 2: Edge-overlay with low confidence (Canny)
    t_edge_start = time.perf_counter()
    edge_boxes, edge_masks = run_detection_test(img_bgr, model, "Edge-overlay (Canny, conf=0.01)", edge_overlay_canny, conf_thresh=EDGE_CONF_THRESH_CANNY)
    t_edge_end = time.perf_counter()
    print(f"[Timing] Edge-overlay test: {t_edge_end-t_edge_start:.3f} seconds")
    
    additional_boxes.extend(edge_boxes)
    additional_masks.extend(edge_masks)

    # Test 3: Sobel edge detection
    def edge_overlay_sobel(img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        sobel = cv2.magnitude(sobelx, sobely)
        sobel = np.uint8(np.clip(sobel, 0, 255))
        sobel_3ch = cv2.cvtColor(sobel, cv2.COLOR_GRAY2BGR)
        return sobel_3ch
    t_sobel_start = time.perf_counter()
    sobel_boxes, sobel_masks = run_detection_test(img_bgr, model, "Edge-overlay (Sobel, conf=0.05)", edge_overlay_sobel, conf_thresh=EDGE_CONF_THRESH_SOBEL)
    t_sobel_end = time.perf_counter()
    print(f"[Timing] Sobel edge test: {t_sobel_end-t_sobel_start:.3f} seconds")
    
    additional_boxes.extend(sobel_boxes)
    additional_masks.extend(sobel_masks)

    if len(additional_boxes) == 0:
        return original_boxes
    # Extract features for additional detections
    t_feat2_start = time.perf_counter()
    additional_features = extract_backbone_features(model, img_bgr, additional_boxes)
    t_feat2_end = time.perf_counter()
    print(f"[Timing] Feature extraction (additional): {t_feat2_end-t_feat2_start:.3f} seconds")
    # Filter additional detections to only keep non-duplicates
    t_dedup_start = time.perf_counter()
    filtered_additional = []
    filtered_additional_masks = []
    used_additional = set()
    for i, box in enumerate(additional_boxes):
        is_dup = False
        for j, orig_box in enumerate(original_boxes):
            if is_duplicate_detection(box, orig_box, None, None, additional_features[i], original_features[j]):
                is_dup = True
                break
        if not is_dup:
            filtered_additional.append(box)
            filtered_additional_masks.append(additional_masks[i])
    t_dedup_end = time.perf_counter()
    print(f"[Timing] Deduplication: {t_dedup_end-t_dedup_start:.3f} seconds")
    # Combine original and filtered additional detections
    final_boxes = original_boxes + filtered_additional
    return final_boxes

def detect_fast(img_bgr, model, show_popup=False):
    """
    Enhanced detection pipeline with semantic deduplication.
    Times each major step for performance analysis.
    """
    import time
    t0 = time.perf_counter()
    props = yolo_multi_test_detection(img_bgr, model)
    t1 = time.perf_counter()
    print(f"[Timing] yolo_multi_test_detection: {t1-t0:.3f} seconds")
    if len(props) > 0:
        t2 = time.perf_counter()
        merged = combine_similar_boxes(props, iou_thresh=0.5, img_bgr=img_bgr)
        t3 = time.perf_counter()
        print(f"[Timing] semantic_combine_similar_boxes: {t3-t2:.3f} seconds")
        # Final deduplication: Non-Maximum Suppression (NMS) as the last layer
        merged = non_max_suppression(merged, iou_thresh=0.3)
        print(f"[INFO] After final NMS: {len(merged)} boxes")
        # Final deduplication: Merge overlapping boxes by union (not just NMS)
        merged = merge_overlapping_boxes_union(merged, iou_thresh=0.3)
        print(f"[INFO] After final union-merge: {len(merged)} boxes")
        if show_popup:
            pass  # No popup code, intentionally left blank
        return merged
    return np.empty((0,5), dtype=np.float32)

def draw_detections_with_masks(image, detections, masks=None):
    """Draw detections with mask outlines"""
    result_image = image.copy()
    
    for i, detection in enumerate(detections):
        bbox = detection
        confidence = detection[4] if len(detection) > 4 else 0.0
        
        x1, y1, x2, y2 = map(int, bbox[:4])
        
        # Color based on confidence
        if confidence > 0.7:
            color = (0, 255, 0)  # Green for high confidence
        elif confidence > 0.4:
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
        label = f"obj_{i}: {confidence:.3f}"
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
    
    print("Running exact server-style detection...")
    start_time = time.time()
    
    # Run the exact same detection pipeline as geminiserver.py
    boxes = detect_fast(img, model, show_popup=True)
    
    total_time = time.time() - start_time
    
    print("Drawing results...")
    result_image = draw_detections_with_masks(img, boxes)
    
    # Save result
    cv2.imwrite(OUTPUT_IMAGE, result_image)
    
    # Print results
    print(f"\n=== EXACT SERVER DETECTION RESULTS ===")
    print(f"Total time: {total_time:.2f}s")
    print(f"Final detections: {len(boxes)}")
    print(f"Results saved to: {OUTPUT_IMAGE}")
    
    # Print detection details
    print("\n=== DETECTION DETAILS ===")
    for i, detection in enumerate(boxes):
        x1, y1, x2, y2, confidence = detection
        area = (x2 - x1) * (y2 - y1)
        print(f"{i+1}. Box: [{x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}] - Conf: {confidence:.3f} - Area: {area:.0f}")

if __name__ == "__main__":
    main() 