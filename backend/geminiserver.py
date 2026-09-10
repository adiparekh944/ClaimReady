# === CLAIMREADY BACKEND SERVER ===
#
# Flask transport layer over the perception pipeline and Gemini identification.
#
# Endpoints:
#   POST /api/analyze-image            multipart, field "image"
#   POST /api/analyze-multiple-images  JSON {"images": [base64, ...]}
#   GET  /health
#
# Pipeline: a class-agnostic YOLO11 segmentation model proposes object regions,
# those proposals are fused and deduplicated using geometry, segmentation masks
# and CLIP appearance embeddings, and the surviving crops go to Gemini for
# naming, categorization and valuation. YOLO's own class labels are discarded
# on this path; see docs/computer_vision_pipeline.md for why.
#
# All CV parameters come from vision/config.py and can be overridden with
# CR_VISION_* environment variables. CR_VISION_MODE selects FAST, BALANCED or
# ACCURATE.
import time
import os
import base64
import io
import json
import logging
import math

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from PIL import Image
import cv2
import numpy as np
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Gemini config from env. No default key: a hardcoded credential in source is
# a leak, and failing loudly at startup is better than silently running on
# someone's personal quota.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY not set. Export it or add it to backend/.env before starting the server."
    )
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

# === PERCEPTION PIPELINE ===
#
# All computer-vision work lives in the `vision` package. This module is a
# transport layer: it decodes the request, calls the pipeline, hands crops to
# Gemini, and serializes the response.
#
# The proposal generation, multi-scale inference, weighted box fusion,
# segmentation-mask handling, CLIP embedding deduplication and tiled detection
# that used to be inlined here (much of it unreachable) now live in
# vision/detector.py, vision/fusion.py, vision/segmentation.py,
# vision/embeddings.py and vision/deduplication.py. See
# docs/computer_vision_pipeline.md for the architecture and
# docs/cv_upgrade_plan.md for what was removed and why.

from vision.config import PipelineMode, load_config
from vision.pipeline import VisionPipeline
from vision.proposals import ORIGIN_PROPOSAL, ORIGIN_SCENE_RECOVERY

# Perception configuration. Mode and every threshold can be overridden from the
# environment with a CR_VISION_ prefix (e.g. CR_VISION_MODE=FAST,
# CR_VISION_MAX_PROPOSALS=200), so production can be retuned without a code
# deploy. Defaults to BALANCED.
VISION_CONFIG = load_config(model_path=os.environ.get("YOLO_MODEL_PATH", "yolo11x-seg.pt"))

# One pipeline per process. Model weights load once and are shared across
# requests; constructing this is cheap because loading is lazy.
VISION_PIPELINE = VisionPipeline(VISION_CONFIG)

logger.info(
    "vision pipeline: mode=%s scales=%s embeddings=%s segmentation=%s tiling=%s max_proposals=%d",
    VISION_CONFIG.mode.value,
    list(VISION_CONFIG.scales),
    VISION_CONFIG.enable_embeddings,
    VISION_CONFIG.enable_segmentation,
    VISION_CONFIG.enable_tiling,
    VISION_CONFIG.max_proposals,
)


def warmup_models():
    """Load model weights at startup instead of inside the first request.

    Cold-loading YOLO and the CLIP encoder together takes tens of seconds. Without
    this the first user to upload an image absorbs all of it.
    """
    try:
        started = time.perf_counter()
        VISION_PIPELINE.warmup()
        logger.info("model warmup finished in %.1fs", time.perf_counter() - started)
    except Exception as exc:
        # A warmup failure must not prevent the server from starting; the models
        # will simply load lazily on first use.
        logger.warning("model warmup failed (models will load on first request): %s", exc)


def detect_proposals(cv_image):
    """Run the perception pipeline on a BGR image.

    Returns:
        A `vision.pipeline.PipelineResult` whose `proposals` are deduplicated
        and in original-image coordinates, with `crops` aligned to them.
    """
    return VISION_PIPELINE.process_image(cv_image)


def build_crop_payload(cv_image, result):
    """Turn pipeline proposals into the crop lists Gemini expects.

    Applies the existing size-dependent padding so crops keep the framing the
    prompt was tuned against: small objects get proportionally more context,
    large ones almost none.

    Returns:
        `(crop_pils, codes, bboxes)`, index-aligned. `codes` are the stringified
        proposal positions that Gemini echoes back in its `code` field.
    """
    crop_pils, codes, bboxes = [], [], []
    img_h, img_w = cv_image.shape[:2]

    for index, proposal in enumerate(result.proposals):
        x1, y1, x2, y2 = proposal.int_bbox()
        pad_frac = dynamic_padding(x1, y1, x2, y2, img_w, img_h)
        box_w, box_h = x2 - x1, y2 - y1
        crop_coords = get_clamped_padded_box(
            x1, y1, x2, y2, int(box_w * pad_frac), int(box_h * pad_frac), img_w, img_h
        )
        if crop_coords is None:
            continue
        nx1, ny1, nx2, ny2 = crop_coords
        crop = cv_image[ny1:ny2, nx1:nx2]
        if crop.size == 0:
            continue
        crop_pils.append(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)))
        codes.append(str(index))
        bboxes.append((x1, y1, x2, y2))

    return crop_pils, codes, bboxes


def label_item_origins(items, codes):
    """Tag each Gemini item with whether the detector proposed it.

    Gemini may return items it spotted in the full scene that no detector
    proposal covered; those arrive with `imageAttachment == "scene"`. Recording
    the distinction is what makes detector recall measurable: an item recovered
    only from the scene view is one the proposal stage missed.

    Adds an additive `source` field, so existing consumers are unaffected.
    """
    known = set(codes)
    for item in items:
        attachment = str(item.get("imageAttachment", ""))
        code = str(item.get("code", ""))
        if attachment == "scene" or code not in known:
            item["source"] = ORIGIN_SCENE_RECOVERY
        else:
            item["source"] = ORIGIN_PROPOSAL
    return items


def summarize_detection(result):
    """Compact per-request perception diagnostics for logs and API responses."""
    return {
        "mode": result.mode.value,
        "raw_proposals": result.raw_count,
        "fused_proposals": result.prefused_count,
        "final_proposals": result.final_count,
        "embedded_proposals": result.embedding_count,
        "tiled": result.tiled,
        "timings": result.timings,
        "merge_reasons": result.dedup.reason_counts() if result.dedup else {},
    }


def pil_image_to_base64(pil_img):
    buffer = io.BytesIO()
    pil_img.save(buffer, format="JPEG")
    buffer.seek(0)
    base64_str = base64.b64encode(buffer.read()).decode('utf-8')
    data_url = f"data:image/jpeg;base64,{base64_str}"
    return data_url

def analyze_single_image(image_data):
    """Analyze one base64-encoded image.

    Used by the multi-image endpoint. Returns the same shape as before —
    `items`, `objects`, `images` — with `objects` still a list of
    `[x1, y1, x2, y2, confidence]` boxes so existing consumers keep working.
    """
    try:
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_bgr is None:
            return {"error": "Failed to decode image", "items": [], "objects": []}

        result = detect_proposals(img_bgr)
        logger.info("perception: %s", summarize_detection(result))

        if not result.proposals:
            return {"error": "No objects detected", "items": [], "objects": []}

        crop_pils, codes, bboxes = build_crop_payload(img_bgr, result)
        if not crop_pils:
            return {"error": "No valid objects to analyze", "items": [], "objects": [], "images": {}}

        scene_pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
        analysis_result = analyze_scene_with_gemini(scene_pil, crop_pils, codes, bboxes)
        analysis_result = label_item_origins(analysis_result, codes)

        code_to_image = {codes[i]: pil_image_to_base64(crop) for i, crop in enumerate(crop_pils)}

        # Gemini may report items it saw only in the wide shot; render crops for
        # those from the scene so every item still has a thumbnail.
        for item in analysis_result:
            if item.get('imageAttachment') == 'scene':
                bbox = item.get('bbox', [])
                if len(bbox) == 4:
                    x1, y1, x2, y2 = bbox
                    scene_crop = scene_pil.crop((x1, y1, x2, y2))
                    scene_crop_resized = resize_image_maintain_aspect_ratio(scene_crop, 384)
                    scene_code = item.get('code', 'scene')
                    code_to_image[scene_code] = pil_image_to_base64(scene_crop_resized)

        # Preserve the legacy [x1, y1, x2, y2, conf] box format.
        objects = [list(p.bbox) + [p.confidence] for p in result.proposals]
        return {
            "items": analysis_result,
            "objects": objects,
            "images": code_to_image,
            "detection": summarize_detection(result),
        }

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
- DO NOT add duplicate items - base off ofspatial reasoning.
- For each item, either choose the segment that shows the item most centered and fills up the most of the frame.
- If you detect an item in the full scene that is not represented by any segment, create a JSON entry with "imageAttachment": "scene" and provide bounding box coordinates for that item.
- Do not classify humans or animals, discard anything that is living if it is not in a picture.

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

# In-memory progress tracking (for demo; not for production)
# progress_dict = {}
# progress_lock = Lock()

@app.route("/api/analyze-image", methods=["POST"])
def analyze_image():
    """Analyze one uploaded image.

    Response shape is unchanged: `items`, `total_items`, `images`. A `detection`
    block is added with perception diagnostics, and each item carries an
    additive `source` field of "proposal" or "scene_recovery".
    """
    try:
        start_time = time.perf_counter()
        if "image" not in request.files:
            return jsonify({
                'status': 'error', 'error': 'No image file provided',
                'items': [], 'objects': [], 'total_items': 0, 'total_value': 0,
            }), 400

        file = request.files["image"]
        file_bytes = file.read()
        logger.info("received %d bytes from %s", len(file_bytes), file.filename)

        np_arr = np.frombuffer(file_bytes, np.uint8)
        cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if cv_image is None:
            return jsonify({
                'status': 'error', 'error': 'Invalid image data',
                'items': [], 'objects': [], 'total_items': 0, 'total_value': 0,
            }), 400

        scene_pil = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))

        result = detect_proposals(cv_image)
        diagnostics = summarize_detection(result)
        logger.info("perception: %s", diagnostics)

        crop_pils, codes, bboxes = build_crop_payload(cv_image, result)
        logger.info("passing %d crops to Gemini", len(crop_pils))

        gemini_start = time.perf_counter()
        items = analyze_scene_with_gemini(scene_pil, crop_pils, codes, bboxes)
        gemini_elapsed = time.perf_counter() - gemini_start
        logger.info("Gemini analysis took %.2fs", gemini_elapsed)

        items = label_item_origins(items, codes)
        code_to_image = {codes[i]: pil_image_to_base64(crop) for i, crop in enumerate(crop_pils)}

        # Items Gemini found only in the wide shot still need a thumbnail.
        for item in items:
            if item.get('imageAttachment') == 'scene':
                bbox = item.get('bbox', [])
                if len(bbox) == 4:
                    x1, y1, x2, y2 = bbox
                    scene_crop = scene_pil.crop((x1, y1, x2, y2))
                    scene_crop_resized = resize_image_maintain_aspect_ratio(scene_crop, 384)
                    scene_code = item.get('code', 'scene')
                    code_to_image[scene_code] = pil_image_to_base64(scene_crop_resized)

        recovered = sum(1 for item in items if item.get('source') == ORIGIN_SCENE_RECOVERY)
        diagnostics['gemini_s'] = round(gemini_elapsed, 3)
        diagnostics['total_s'] = round(time.perf_counter() - start_time, 3)
        diagnostics['items_from_proposals'] = len(items) - recovered
        diagnostics['items_from_scene_recovery'] = recovered
        logger.info(
            "returning %d items (%d from proposals, %d scene-recovered) in %.2fs",
            len(items), len(items) - recovered, recovered, diagnostics['total_s'],
        )

        return jsonify(
            items=items,
            total_items=len(items),
            images=code_to_image,
            detection=diagnostics,
        )
    except Exception as e:
        logger.exception("error processing image")
        return jsonify({'error': str(e), 'status': 'error', 'items': []}), 500

@app.route('/api/analyze-multiple-images', methods=['POST'])
def analyze_multiple_images():
    try:
        data = request.get_json()
        if not data or 'images' not in data:
            return jsonify({'error': 'Missing images data', 'status': 'error', 'items': []}), 400
        images = data['images']
        filenames = data.get('filenames', [])  # Optional filenames array
        if not isinstance(images, list):
            return jsonify({'error': 'Images must be a list', 'status': 'error', 'items': []}), 400
        all_items = []
        all_objects = []
        total_value = 0.0
        print(f"[API] /api/analyze-multiple-images called with {len(images)} images.")
        
        # Process images
        results = []
        for i, image_data in enumerate(images):
            result = analyze_single_image(image_data)
            results.append(result)
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
    return jsonify({'status': 'ok'}), 200

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return response

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

@app.route('/api/vision-config', methods=['GET'])
def vision_config():
    """Report the active perception configuration.

    Useful for confirming which mode and thresholds a deployed instance is
    actually running, since every value is environment-overridable.
    """
    return jsonify({'status': 'ok', 'config': VISION_CONFIG.summary()}), 200


def main():
    """Run the development server.

    Weights are warmed up before binding the port so the first request does not
    absorb model-loading time. In production this module is the Docker
    entrypoint; see docs/computer_vision_pipeline.md for the gunicorn note.
    """
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}

    # Skip warmup under the Flask reloader's parent process, which would
    # otherwise load the models twice.
    if not debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        warmup_models()

    app.run(host='0.0.0.0', port=port, debug=debug)


if __name__ == '__main__':
    main()