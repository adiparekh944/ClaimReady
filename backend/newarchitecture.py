# === CLAIMREADY NEW ARCHITECTURE ===
# CLIP-based Visual Embedding System for Item Recognition
#
# This file implements the new architecture with:
# 1. YOLO detection for individual items
# 2. CLIP visual embeddings for each detected item
# 3. Vector output for similarity search

import time
import os
import base64
import io
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from PIL import Image
import cv2
import numpy as np
import torch
import clip
from ultralytics import YOLO
from simple_sku_database import initialize_sku_database, search_item_sku, get_database_stats

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# YOLO config
YOLO_MODEL_PATH = os.environ.get("YOLO_MODEL_PATH", "yolo11x-seg.pt")
YOLO_CONF = float(os.environ.get("YOLO_CONF", 0.25))

# CLIP config
CLIP_MODEL_NAME = "ViT-L/14"  # More accurate CLIP model (768-dim embeddings)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Load models
print(f"Loading YOLO model from {YOLO_MODEL_PATH}...")
YOLO_MODEL = YOLO(YOLO_MODEL_PATH)

print(f"Loading CLIP model {CLIP_MODEL_NAME} on {DEVICE}...")
CLIP_MODEL, CLIP_PREPROCESS = clip.load(CLIP_MODEL_NAME, device=DEVICE)
print("Models loaded successfully!")

# Initialize SKU database
print("🔄 Initializing SKU database...")
sku_db_loaded = initialize_sku_database()
if sku_db_loaded:
    stats = get_database_stats()
    print(f"✅ SKU database loaded: {stats['total_skus']} SKUs, {stats['embedding_dimension']}D embeddings")
else:
    print("❌ Failed to load SKU database")

# === COPY EXACT DETECTION PIPELINE FROM GEMINISERVER.PY ===

# Detection parameters (copied from geminiserver.py)
SCALES = [640]  # Single scale for speed - most objects detected at 640
IOU_NMS = 0.7   # Slightly lower for speed
MASK_THRESH = 0.01
CONF_THRESH = 0.01  # Lower confidence threshold to maintain accuracy
USE_FAST_MERGING = True

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

def run_detection_test(img_bgr, model, test_name, transform_func=None, conf_thresh=None):
    """Run a single detection test with optional image transformation"""
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
            boxes.append([x1, y1, x2, y2, score])
        # Collect masks (if available)
        if hasattr(res[0], "masks") and res[0].masks is not None and res[0].masks.data is not None:
            m = res[0].masks.data.cpu().numpy()
            m = (m > MASK_THRESH).astype(np.uint8)
            masks.extend(m)
    return boxes, masks

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
    EXACT COPY FROM GEMINISERVER.PY
    """
    boxes, masks = diagnostic_detection(img_bgr, model)
    return boxes

def detect_objects_yolo(image_bgr):
    """
    Detect objects using the EXACT same YOLO pipeline as geminiserver.py
    Returns list of bounding boxes: [[x1, y1, x2, y2, conf], ...]
    """
    try:
        # Use the EXACT same detection pipeline as geminiserver.py
        detected_boxes = detect_fast(image_bgr, YOLO_MODEL)
        return detected_boxes
    except Exception as e:
        logger.error(f"YOLO detection failed: {e}")
        return []

def get_clip_embedding(image_pil):
    """
    Get CLIP embedding for a PIL image
    Returns normalized 512-dim vector
    """
    try:
        # Preprocess image for CLIP
        image_tensor = CLIP_PREPROCESS(image_pil).unsqueeze(0).to(DEVICE)
        
        # Get embedding
        with torch.no_grad():
            image_features = CLIP_MODEL.encode_image(image_tensor)
            # Normalize for cosine similarity
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        
        return image_features.cpu().numpy().flatten()
    except Exception as e:
        logger.error(f"CLIP embedding failed: {e}")
        return None

def crop_item_from_bbox(image_bgr, bbox, padding=0.05):
    """
    Crop item from image using bounding box with padding
    """
    x1, y1, x2, y2, conf = bbox
    h, w = image_bgr.shape[:2]
    
    # Add padding
    pad_x = int((x2 - x1) * padding)
    pad_y = int((y2 - y1) * padding)
    
    # Clamp coordinates
    x1 = max(0, int(x1 - pad_x))
    y1 = max(0, int(y1 - pad_y))
    x2 = min(w, int(x2 + pad_x))
    y2 = min(h, int(y2 + pad_y))
    
    # Crop and convert to PIL
    crop = image_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    
    crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    return Image.fromarray(crop_rgb)

@app.route("/api/analyze-image-clip", methods=["POST"])
def analyze_image_clip():
    """
    Main endpoint: YOLO detection + CLIP embeddings
    """
    try:
        print("\n" + "="*80)
        print("🚀 NEW ARCHITECTURE: CLIP EMBEDDING ANALYSIS")
        print("="*80)
        
        start_time = time.perf_counter()
        
        # Get uploaded image
        if "image" not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files["image"]
        file_bytes = file.read()
        print(f"📁 Image received: {len(file_bytes)} bytes")
        
        # Decode image
        np_arr = np.frombuffer(file_bytes, np.uint8)
        cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if cv_image is None:
            return jsonify({'error': 'Invalid image data'}), 400
        
        print(f"🖼️  Image decoded: {cv_image.shape}")
        
        # Step 1: YOLO Detection
        print("\n" + "-"*60)
        print("🔍 STEP 1: YOLO DETECTION")
        print("-"*60)
        
        yolo_start = time.perf_counter()
        detected_boxes = detect_objects_yolo(cv_image)
        yolo_end = time.perf_counter()
        
        print(f"✅ YOLO found {len(detected_boxes)} objects in {yolo_end - yolo_start:.2f}s")
        
        if not detected_boxes:
            print("❌ No objects detected!")
            return jsonify({
                'status': 'success',
                'message': 'No objects detected',
                'embeddings': [],
                'objects': []
            })
        
        # Step 2: CLIP Embeddings for each detected item
        print("\n" + "-"*60)
        print("🧠 STEP 2: CLIP EMBEDDINGS")
        print("-"*60)
        
        embeddings = []
        objects_info = []
        images_map = {}
        
        for i, bbox in enumerate(detected_boxes):
            print(f"\n📦 PROCESSING ITEM {i+1}/{len(detected_boxes)}")
            print(f"   BBox: [{bbox[0]:.1f}, {bbox[1]:.1f}, {bbox[2]:.1f}, {bbox[3]:.1f}]")
            print(f"   Confidence: {bbox[4]:.3f}")
            
            # Crop the item
            item_crop = crop_item_from_bbox(cv_image, bbox)
            if item_crop is None:
                print("   ❌ Failed to crop item")
                continue
            
            print(f"   📐 Crop size: {item_crop.size}")
            
            # Get CLIP embedding
            clip_start = time.perf_counter()
            embedding = get_clip_embedding(item_crop)
            clip_end = time.perf_counter()
            
            if embedding is not None:
                print(f"   ✅ CLIP embedding: {len(embedding)} dimensions")
                print(f"   ⏱️  CLIP time: {clip_end - clip_start:.3f}s")
                
                # Print first 10 values of embedding
                print(f"   🔢 Embedding preview: {embedding[:10]}")
                print(f"   📊 Embedding stats: min={embedding.min():.4f}, max={embedding.max():.4f}, mean={embedding.mean():.4f}")
                
                # Search SKU database
                print(f"   🔍 Searching SKU database...")
                sku_start = time.perf_counter()
                sku_results = search_item_sku(embedding, confidence_threshold=0.1)
                sku_end = time.perf_counter()
                
                print(f"   ⏱️  SKU search time: {sku_end - sku_start:.3f}s")
                print(f"   🎯 Best match: {sku_results['best_match']['product_name'] if sku_results['best_match'] else 'None'}")
                print(f"   💰 Price: ${sku_results['best_match']['price_usd']:.2f}" if sku_results['best_match'] else "   💰 Price: N/A")
                print(f"   📊 Confidence: {sku_results['confidence']:.3f}")
                print(f"   🔄 Use Producer 2: {sku_results['use_producer_2']}")
                
                # Show top 3 matches
                print(f"   🏆 Top 3 SKU Matches:")
                for j, match in enumerate(sku_results['matches'][:3]):
                    print(f"      {j+1}. {match['product_name']} - ${match['price_usd']:.2f} (conf: {match['confidence']:.3f})")
                
                # Convert all float32 values to regular Python floats for JSON serialization
                bbox_float = [float(x) for x in bbox]
                # Generate a stable code for this item and attach base64 thumbnail
                code = f"item_{i+1}"
                try:
                    buf = io.BytesIO()
                    item_crop.save(buf, format="JPEG")
                    img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                    images_map[code] = f"data:image/jpeg;base64,{img_b64}"
                except Exception:
                    pass
                
                embeddings.append({
                    'item_id': i,
                    'code': code,
                    'bbox': bbox_float,  # Convert to regular floats
                    'embedding': embedding.tolist(),  # Convert to list for JSON
                    'embedding_dim': len(embedding),
                    'sku_matches': sku_results['matches'],
                    'best_sku_match': sku_results['best_match'],
                    'sku_confidence': float(sku_results['confidence']),  # Convert to float
                    'use_producer_2': sku_results['use_producer_2']
                })
                
                objects_info.append({
                    'item_id': i,
                    'code': code,
                    'bbox': bbox_float,  # Convert to regular floats
                    'crop_size': item_crop.size,
                    'confidence': float(bbox[4]),  # Convert confidence to float
                    'sku_matches': sku_results['matches'],
                    'best_sku_match': sku_results['best_match']
                })
            else:
                # Even if CLIP embedding fails, add basic object info
                objects_info.append({
                    'item_id': i,
                    'code': f"item_{i+1}",
                    'bbox': [float(x) for x in bbox],
                    'crop_size': item_crop.size,
                    'confidence': float(bbox[4]),
                    'sku_matches': [],
                    'best_sku_match': None
                })
        
        # Summary
        total_time = time.perf_counter() - start_time
        print("\n" + "="*80)
        print("📊 ANALYSIS COMPLETE")
        print("="*80)
        print(f"⏱️  Total time: {total_time:.2f}s")
        print(f"🔍 Objects detected: {len(detected_boxes)}")
        print(f"🧠 Embeddings generated: {len(embeddings)}")
        print(f"📐 Embedding dimension: {len(embeddings[0]['embedding']) if embeddings else 'N/A'}")
        print("="*80 + "\n")
        
        # Prepare frontend data with proper formatting
        frontend_results = []
        print(f"🔧 DEBUG: objects_info length: {len(objects_info)}")
        print(f"🔧 DEBUG: embeddings length: {len(embeddings)}")
        
        for i, obj in enumerate(objects_info):
            # Get corresponding embedding data
            embedding_data = embeddings[i] if i < len(embeddings) else {}
            
            # Use data from objects_info if embedding_data is empty
            best_match = embedding_data.get('best_sku_match', obj.get('best_sku_match', {}))
            if best_match and 'price_usd' in best_match:
                best_match['price_usd'] = float(best_match['price_usd'])
            if best_match and 'confidence' in best_match:
                best_match['confidence'] = float(best_match['confidence'])
            
            # Convert all matches to have proper float values
            top_3_matches = []
            matches = embedding_data.get('sku_matches', obj.get('sku_matches', []))
            for match in matches[:3]:
                match_copy = match.copy()
                if 'price_usd' in match_copy:
                    match_copy['price_usd'] = float(match_copy['price_usd'])
                if 'confidence' in match_copy:
                    match_copy['confidence'] = float(match_copy['confidence'])
                top_3_matches.append(match_copy)
            
            # Create frontend row
            row = {
                'item_id': i + 1,
                'code': obj.get('code', f"item_{i+1}"),
                'bbox': obj['bbox'],
                'crop_size': obj['crop_size'],
                'yolo_confidence': float(obj.get('confidence', 0.0)),
                'best_match': best_match,
                'price': float(best_match.get('price_usd', 0.0)),
                'sku_confidence': float(embedding_data.get('sku_confidence', 0.0)),
                'use_producer_2': embedding_data.get('use_producer_2', False),
                'top_3_matches': top_3_matches
            }
            frontend_results.append(row)
        
        print(f"🔧 DEBUG: frontend_results length: {len(frontend_results)}")
        if frontend_results:
            print(f"🔧 DEBUG: First item keys: {list(frontend_results[0].keys())}")
        print(f"🔧 DEBUG: images_map keys (first 5): {list(images_map.keys())[:5]}")
        
        response_payload = {
            'status': 'success',
            'message': f'Generated {len(embeddings)} CLIP embeddings',
            'results': {
                'total_objects': len(objects_info),
                'total_embeddings': len(embeddings),
                'embedding_dimension': len(embeddings[0]['embedding']) if embeddings else 0,
                'processing_time': total_time,
                'items': frontend_results,  # Frontend-friendly format
                'images': images_map
            },
            # Mirror at top-level for compatibility with existing frontend
            'items': frontend_results,
            'images': images_map
        }

        print(f"🔧 DEBUG: Response summary -> items: {len(frontend_results)}, images: {len(images_map)}")
        return jsonify(response_payload)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'architecture': 'CLIP-based'}), 200

if __name__ == '__main__':
    print("🚀 Starting ClaimReady New Architecture Server...")
    print(f"🔧 CLIP Model: {CLIP_MODEL_NAME}")
    print(f"🖥️  Device: {DEVICE}")
    print(f"🎯 YOLO Model: {YOLO_MODEL_PATH}")
    app.run(host='0.0.0.0', port=8081, debug=True)
