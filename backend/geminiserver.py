from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import base64
import io
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Configure Gemini
GEMINI_API_KEY = "AIzaSyA1nXtCYlnurEOWNirhMSXF4NImEVS_IhY"
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-lite')

class ItemProcessor:
    def __init__(self):
        self.model = model
    
    def analyze_image(self, image_data):
        """
        Analyze an image and extract item information using Gemini.
        
        Args:
            image_data: Base64 encoded image or PIL Image object
            
        Returns:
            dict: Item information including name, price, description, category
        """
        try:
            # Convert image data to PIL Image
            if isinstance(image_data, str):
                # Handle base64 encoded image
                if ',' in image_data:
                    image_data = image_data.split(',', 1)[1]
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
            elif isinstance(image_data, bytes):
                image = Image.open(io.BytesIO(image_data))
            else:
                image = image_data  # Assume it's already a PIL Image
            
            # Create prompt for Gemini
            prompt = """
            Analyze this image and provide detailed information about any items visible.
            
            For each item detected, provide the following information in JSON format:
            {
                "items": [
                    {
                        "name": "Item name (3-7 words)",
                        "price": 100,
                        "category": "Category (furniture, electronics, clothing, etc.)",
                        "description": "Brief description (1-2 sentences)",
                        "condition": "Condition (new, good, fair, poor)",
                        "brand": "Brand name if identifiable, otherwise 'Unknown'"
                    }
                ]
            }
            
            Important guidelines:
            - Be conservative with price estimates
            - If image quality is poor, estimate lower prices
            - Focus on household items and common objects
            - Return only valid JSON format with price as a number, not a string
            - If no items are clearly visible, return empty items array
            """
            
            # Get response from Gemini
            response = self.model.generate_content([prompt, image])
            
            # Parse the response
            try:
                import json
                # Extract JSON from response
                response_text = response.text
                
                # Find JSON in the response (in case there's extra text)
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    result = json.loads(json_str)
                    
                    # Ensure all prices are numbers
                    if 'items' in result:
                        for item in result['items']:
                            if 'price' in item:
                                try:
                                    item['price'] = float(item['price'])
                                except (ValueError, TypeError):
                                    item['price'] = 0
                    
                    return result
                else:
                    logger.error("No valid JSON found in Gemini response")
                    return {"items": []}
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Gemini response: {e}")
                logger.error(f"Raw response: {response.text}")
                return {"items": []}
                
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return {"items": []}

# Initialize item processor
item_processor = ItemProcessor()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'gemini-server'}), 200

@app.route('/api/analyze-image', methods=['POST'])
def analyze_image():
    """
    Analyze an image and return item information.
    
    Expected request format:
    {
        "image": "base64_encoded_image_data"
    }
    
    Returns:
    {
        "status": "success",
        "items": [
            {
                "name": "Item name",
                "price": 100,
                "category": "furniture",
                "description": "Description",
                "condition": "good",
                "brand": "Brand name"
            }
        ]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'image' not in data:
            return jsonify({
                'error': 'Missing image data',
                'status': 'error'
            }), 400
        
        image_data = data['image']
        
        # Analyze the image
        result = item_processor.analyze_image(image_data)
        
        # Add status to response
        result['status'] = 'success'
        
        logger.info(f"Successfully analyzed image, found {len(result.get('items', []))} items")
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error',
            'items': []
        }), 500

@app.route('/api/analyze-multiple-images', methods=['POST'])
def analyze_multiple_images():
    """
    Analyze multiple images and return combined item information.
    
    Expected request format:
    {
        "images": ["base64_image_1", "base64_image_2", ...]
    }
    
    Returns:
    {
        "status": "success",
        "items": [
            {
                "name": "Item name",
                "price": 100,
                "category": "furniture",
                "description": "Description",
                "condition": "good",
                "brand": "Brand name",
                "source_image": 0  // Index of the image this item came from
            }
        ]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'images' not in data:
            return jsonify({
                'error': 'Missing images data',
                'status': 'error'
            }), 400
        
        images = data['images']
        
        if not isinstance(images, list):
            return jsonify({
                'error': 'Images must be a list',
                'status': 'error'
            }), 400
        
        all_items = []
        
        # Process each image
        for i, image_data in enumerate(images):
            logger.info(f"Processing image {i + 1}/{len(images)}")
            
            result = item_processor.analyze_image(image_data)
            items = result.get('items', [])
            
            # Add source image index to each item
            for item in items:
                item['source_image'] = i
            
            all_items.extend(items)
        
        # Calculate total value - ensure price is a number
        total_value = sum(float(item.get('price', 0)) for item in all_items)
        
        response = {
            'status': 'success',
            'items': all_items,
            'total_items': len(all_items),
            'total_value': total_value,
            'images_processed': len(images)
        }
        
        logger.info(f"Successfully processed {len(images)} images, found {len(all_items)} total items")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error processing multiple images: {str(e)}")
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