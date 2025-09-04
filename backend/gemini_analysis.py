"""
Gemini AI analysis functions for ClaimReady backend
"""

import google.generativeai as genai
from PIL import Image
import json
import re
from image_utils import resize_image_maintain_aspect_ratio, safe_price, format_category
from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_RESPONSE_SCHEMA

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
GEMINI_GEN_MODEL = genai.GenerativeModel(GEMINI_MODEL)

def build_gemini_contents(scene_pil, crops, codes, instructions):
    """Build contents for Gemini API call"""
    contents = [instructions, "scene", scene_pil]
    
    for i, (crop, code) in enumerate(zip(crops, codes)):
        contents.extend([f"CODE:{code}", crop])
    
    return contents

def _resp_text(resp):
    """Extract text from Gemini response"""
    try:
        if hasattr(resp, 'text'):
            return resp.text
        elif hasattr(resp, 'candidates') and resp.candidates:
            return resp.candidates[0].content.parts[0].text
        else:
            return str(resp)
    except Exception as e:
        print(f"Error extracting text from response: {e}")
        return str(resp)

def analyze_scene_with_gemini(scene_pil, crop_pils, codes, bboxes, instructions_override=None, temperature_override=None):
    """Analyze scene using Gemini AI"""
    # Resize full image to 768px longest edge
    scene_pil_resized = resize_image_maintain_aspect_ratio(scene_pil, 768)
    
    # Resize all segments to 384px longest edge
    crop_pils_resized = [resize_image_maintain_aspect_ratio(crop, 384) for crop in crop_pils]
    
    instructions = instructions_override or """
You are an insurance-claims assistant analyzing room images. You receive:
- A full-room image titled 'scene'
- Segmented images (crop0, crop1, etc.) with CODE:<id> and BBOX:[x1,y1,x2,y2]

CRITICAL REQUIREMENTS:
- You MUST use the provided crop codes (crop0, crop1, etc.) and their corresponding CODE values for segmented items.
- Each segment may contain multiple individual items. Identify and separate each unique item.
- If a segment contains multiple items, create separate JSON entries for each item using the same segment code but with different bounding box coordinates.
- Use context from the full scene to identify items, even if segments are unclear.
- Include every unique item found - make best guesses if uncertain.
- DO NOT add duplicate items - base of spatial reasoning.
- For each item, either choose the segment that shows the item most centered and fills up the most of the frame.
- If you detect an item in the full scene that is not represented by any segment, create a JSON entry with "imageAttachment": "scene" and provide bounding box coordinates for that item.
- When estimating price, make sure to esitmate from an insurance perspective and factor emotional value into the price.

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
    
    contents = build_gemini_contents(scene_pil_resized, crop_pils_resized, codes, instructions)
    
    try:
        # Generate content using Gemini
        generation_config = {
            "temperature": temperature_override or 0.1,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
        
        response = GEMINI_GEN_MODEL.generate_content(
            contents,
            generation_config=generation_config
        )
        
        # Extract and parse response
        response_text = _resp_text(response)
        print(f"DEBUG: Raw Gemini response: {response_text[:500]}...")
        
        # Try to extract JSON from response
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group()
        else:
            # Fallback: try to find JSON array in the response
            lines = response_text.split('\n')
            json_lines = []
            in_json = False
            for line in lines:
                if line.strip().startswith('['):
                    in_json = True
                if in_json:
                    json_lines.append(line)
                if line.strip().endswith(']') and in_json:
                    break
            json_str = '\n'.join(json_lines)
        
        # Parse JSON
        try:
            items = json.loads(json_str)
            print(f"DEBUG: Parsed items: {items}")
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON parse error: {e}")
            print(f"DEBUG: Attempting to parse as individual items...")
            
            # Try to parse individual items
            items = []
            item_pattern = r'\{[^}]*"code"[^}]*\}'
            matches = re.findall(item_pattern, response_text, re.DOTALL)
            
            for match in matches:
                try:
                    item = json.loads(match)
                    items.append(item)
                except json.JSONDecodeError:
                    continue
        
        # Process and validate items
        processed_items = []
        for item in items:
            if not isinstance(item, dict):
                continue
                
            # Ensure required fields
            processed_item = {
                'code': item.get('code', 'unknown'),
                'imageAttachment': item.get('imageAttachment', 'unknown'),
                'bbox': item.get('bbox', [0, 0, 0, 0]),
                'name': item.get('name', 'Unknown Item'),
                'category': format_category(item.get('category', 'Unknown')),
                'price_usd': safe_price(item.get('price_usd', 0)),
                'description': item.get('description', 'No description available')
            }
            
            processed_items.append(processed_item)
        
        print(f"DEBUG: Final processed items: {len(processed_items)}")
        return processed_items
        
    except Exception as e:
        print(f"Error in Gemini analysis: {e}")
        return []

def analyze_single_image(image_data):
    """Analyze a single image and return results"""
    try:
        # This is a placeholder - implement based on your needs
        return {
            "items": [],
            "objects": [],
            "total_items": 0,
            "total_value": 0
        }
    except Exception as e:
        print(f"Error in single image analysis: {e}")
        return {
            "error": f"Analysis failed: {str(e)}",
            "items": [],
            "objects": []
        }
