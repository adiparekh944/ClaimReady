"""
ClaimReady Backend Server - Modular Version
Advanced YOLO + Gemini AI Insurance Claim Analysis
"""

import os
import logging
from flask import Flask, request
from flask_cors import CORS
from ultralytics import YOLO

# Import our modular components
from config import YOLO_MODEL_PATH, GEMINI_API_KEY, GEMINI_MODEL
from api_routes import (
    analyze_image_route, 
    analyze_multiple_images_route, 
    health_check_route, 
    add_cors_headers
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Configure CORS with specific origins
CORS(app, 
     origins=[
         "http://localhost:3000",
         "http://127.0.0.1:3000", 
         "https://useclaimready.ai",
         "https://www.useclaimready.ai",
         "https://claim-ready.com",
         "https://www.claim-ready.com"
     ],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     supports_credentials=True)

# Load YOLO model
print("🔄 Loading YOLO model...")
YOLO_MODEL = YOLO(YOLO_MODEL_PATH)
print("✅ YOLO model loaded successfully")

# Configure Gemini
import google.generativeai as genai
genai.configure(api_key=GEMINI_API_KEY)
print("✅ Gemini configured successfully")

# Import LangChain verifier to initialize it
from langchain_verifier import is_verifier_available
print(f"✅ LangChain verifier available: {is_verifier_available()}")

# API Routes
@app.route("/api/analyze-image", methods=["POST", "OPTIONS"])
def analyze_image():
    if request.method == "OPTIONS":
        return "", 200
    return analyze_image_route(YOLO_MODEL)

@app.route('/api/analyze-multiple-images', methods=['POST', 'OPTIONS'])
def analyze_multiple_images():
    if request.method == "OPTIONS":
        return "", 200
    return analyze_multiple_images_route()

@app.route('/health', methods=['GET', 'OPTIONS'])
def health_check():
    if request.method == "OPTIONS":
        return "", 200
    return health_check_route()

@app.after_request
def after_request(response):
    return add_cors_headers(response)

if __name__ == "__main__":
    print("🚀 Starting ClaimReady Backend Server...")
    print(f"📊 YOLO Model: {YOLO_MODEL_PATH}")
    print(f"🤖 Gemini Model: {GEMINI_MODEL}")
    print(f"🔗 LangChain Verifier: {'Available' if is_verifier_available() else 'Unavailable'}")
    print("🌐 Server starting on http://127.0.0.1:8080")
    
    app.run(host="0.0.0.0", port=8080, debug=True)
