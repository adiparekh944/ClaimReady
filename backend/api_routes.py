"""
Flask API routes for ClaimReady backend
"""

import time
import json
from flask import request, jsonify
from PIL import Image
import cv2
import numpy as np
from image_utils import pil_to_bytes, pil_image_to_base64, resize_image_maintain_aspect_ratio, to_python_type
from yolo_detection import detect_fast
from gemini_analysis import analyze_scene_with_gemini
from langchain_verifier import verify_item_name_price
from config import GEMINI_RESPONSE_SCHEMA

def analyze_image_route(YOLO_MODEL):
    """Main image analysis API route"""
    try:
        print("🔍 [API] Starting image analysis request")
        
        # Check if image file is present
        if 'image' not in request.files:
            print("❌ [API] No image file in request")
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
        
        if not detected_boxes:
            print("[API] No objects detected. Returning empty result.")
            return jsonify({
                'status': 'success',
                'items': [],
                'objects': [],
                'total_items': 0,
                'total_value': 0,
                'processing_time': yolo_end - yolo_start
            })
        
        # Prepare crops for Gemini analysis
        crop_pils = []
        codes = []
        bboxes = []
        
        for i, (x1, y1, x2, y2, conf) in enumerate(detected_boxes):
            print(f"[API] Processing detection {i}: box=({x1:.1f},{y1:.1f},{x2:.1f},{y2:.1f}), conf={conf:.3f}")
            
            # Validate box coordinates
            if x2 <= x1 or y2 <= y1 or x1 < 0 or y1 < 0 or x2 > cv_image.shape[1] or y2 > cv_image.shape[0]:
                print(f"[API] Skipping invalid box {i}: {x1}, {y1}, {x2}, {y2}")
                continue
            
            # Convert to integers
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            
            # Crop the image
            crop = cv_image[y1:y2, x1:x2]
            if crop.size == 0:
                print(f"[API] Skipping empty crop for box {i}")
                continue
            
            # Convert to PIL
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
        
        # 30-second delay between producer and verifier
        print(f"[API] Waiting 30 seconds before running verifier...")
        time.sleep(30)
        print(f"[API] 30-second delay completed. Starting verifier...")
        
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
        
        # Calculate total value
        total_value = sum(item.get('price_usd', 0) for item in items)
        
        # Convert to Python types for JSON serialization
        items_serializable = [to_python_type(item) for item in items]
        
        response_data = {
            'status': 'success',
            'items': items_serializable,
            'objects': items_serializable,  # For backward compatibility
            'total_items': len(items),
            'total_value': total_value,
            'code_to_image': code_to_image,
            'processing_time': {
                'yolo': yolo_end - yolo_start,
                'gemini': gemini_end - gemini_start,
                'verifier': verifier_end - verifier_start,
                'total': time.perf_counter() - yolo_start
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ [API] Error in analyze_image: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'error': f'Analysis failed: {str(e)}',
            'items': [],
            'objects': [],
            'total_items': 0,
            'total_value': 0
        }), 500

def analyze_multiple_images_route():
    """Multiple images analysis API route"""
    try:
        if 'images' not in request.files:
            return jsonify({'error': 'No images provided'}), 400
        
        files = request.files.getlist('images')
        results = []
        
        for i, file in enumerate(files):
            if file.filename == '':
                continue
                
            # Process each image
            file_bytes = file.read()
            np_arr = np.frombuffer(file_bytes, np.uint8)
            cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if cv_image is not None:
                # Here you would call your analysis function
                # For now, return a placeholder
                results.append({
                    'filename': file.filename,
                    'status': 'processed',
                    'items': []
                })
        
        return jsonify({
            'status': 'success',
            'results': results,
            'total_images': len(results)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def health_check_route():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})

def add_cors_headers(response):
    """Add CORS headers to response"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response
