"""
Image processing utilities for ClaimReady backend
"""

import base64
import io
import math
from PIL import Image
import cv2
import numpy as np

def pil_image_to_base64(pil_img):
    """Convert PIL image to base64 string"""
    buffer = io.BytesIO()
    pil_img.save(buffer, format='JPEG', quality=85)
    img_bytes = buffer.getvalue()
    return base64.b64encode(img_bytes).decode('utf-8')

def pil_to_bytes(img: Image.Image) -> bytes:
    """Convert PIL Image to bytes"""
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=85)
    return buffer.getvalue()

def resize_image_maintain_aspect_ratio(image, target_longest_edge):
    """Resize image while maintaining aspect ratio"""
    width, height = image.size
    
    if width > height:
        new_width = target_longest_edge
        new_height = int(height * target_longest_edge / width)
    else:
        new_height = target_longest_edge
        new_width = int(width * target_longest_edge / height)
    
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

def to_grayscale_3ch(img):
    """Convert image to 3-channel grayscale"""
    return cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)

def edge_overlay_canny(img, alpha=0.5):
    """Apply Canny edge detection overlay"""
    edges = cv2.Canny(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 50, 150)
    edges_3ch = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    return cv2.addWeighted(img, 1-alpha, edges_3ch, alpha, 0)

def pad_and_crop(img, box, pad_pct):
    """Pad and crop image based on bounding box"""
    h, w = img.shape[:2]
    x1, y1, x2, y2 = box
    
    # Calculate padding
    pad_x = int((x2 - x1) * pad_pct)
    pad_y = int((y2 - y1) * pad_pct)
    
    # Apply padding
    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(w, x2 + pad_x)
    y2 = min(h, y2 + pad_y)
    
    return img[y1:y2, x1:x2]

def dynamic_padding(x1, y1, x2, y2, img_w, img_h, min_pad=0.01, max_pad=1.0):
    """Calculate dynamic padding based on box size"""
    box_w = x2 - x1
    box_h = y2 - y1
    
    # Calculate padding as percentage of box size
    pad_x = max(min_pad, min(max_pad, box_w * 0.1))
    pad_y = max(min_pad, min(max_pad, box_h * 0.1))
    
    return pad_x, pad_y

def get_clamped_padded_box(x1, y1, x2, y2, pad_x, pad_y, img_w, img_h):
    """Get padded bounding box clamped to image boundaries"""
    # Apply padding
    new_x1 = max(0, x1 - pad_x)
    new_y1 = max(0, y1 - pad_y)
    new_x2 = min(img_w, x2 + pad_x)
    new_y2 = min(img_h, y2 + pad_y)
    
    return int(new_x1), int(new_y1), int(new_x2), int(new_y2)

def safe_price(val):
    """Safely convert value to float price"""
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
    """Format category string"""
    if not category:
        return "Unknown"
    return category.strip().title()

def to_python_type(obj):
    """Convert numpy types to Python types for JSON serialization"""
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
