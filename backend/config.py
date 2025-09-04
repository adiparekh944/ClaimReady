"""
Configuration and constants for ClaimReady backend
"""

import os

# Gemini config - hardcoded for local testing
GEMINI_API_KEY = "AIzaSyDVIppKcsZwVa3vkZWazztC9XY_-oZUufU"
GEMINI_MODEL = "gemini-2.5-flash"

# Set environment variables for LangChain
os.environ['GOOGLE_API_KEY'] = GEMINI_API_KEY
os.environ['GEMINI_API_KEY'] = GEMINI_API_KEY

# YOLO config
YOLO_MODEL_PATH = "yolo11l.pt"

# === ULTRA-OPTIMIZED DETECTION PARAMETERS ===
CONF_THRESH_HIGH = 0.25
CONF_THRESH_MED = 0.05
CONF_THRESH_LOW = 0.01
FEATURE_SIM_THRESH = 0.85
EDGE_THRESH = 50

# Multiprocessing settings - use all available CPU cores
MAX_WORKERS = min(8, os.cpu_count() or 4)

# Performance optimization flags
USE_PARALLEL_PROCESSING = True
USE_GPU_ACCELERATION = True
ENABLE_DIAGNOSTIC_MODE = False

# Display settings
SHOW_DETECTION_IMAGES = False
SAVE_DETECTION_IMAGES = False

# Gemini response schema
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
                    "bbox": {"type": "array", "items": {"type": "number"}},
                    "name": {"type": "string"},
                    "category": {"type": "string"},
                    "price_usd": {"type": "number"},
                    "description": {"type": "string"},
                    "namePriceScore": {"type": ["number", "null"]},
                    "namePriceNotes": {"type": "string"}
                },
                "required": ["code", "imageAttachment", "bbox", "name", "category", "price_usd", "description"]
            }
        }
    },
    "required": ["items"]
}
