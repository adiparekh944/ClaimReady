"""
Gemini Verifier Module for Name/Price Verification

This module provides a Gemini-based verifier that scores the plausibility
of item names and prices based on visual cues in images.
"""

import os
import json
import re
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from PIL import Image
import io

# Set up environment variables for Gemini
GEMINI_API_KEY = "AIzaSyDVIppKcsZwVa3vkZWazztC9XY_-oZUufU"
os.environ['GOOGLE_API_KEY'] = GEMINI_API_KEY
os.environ['GEMINI_API_KEY'] = GEMINI_API_KEY

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
VERIFIER_MODEL = genai.GenerativeModel("gemini-2.5-flash")
VERIFIER_AVAILABLE = True

def initialize_verifier(gemini_model: str = "gemini-2.5-flash") -> bool:
    """
    Initialize the Gemini verifier.
    
    Args:
        gemini_model: The Gemini model to use
        
    Returns:
        bool: True if initialization successful, False otherwise
    """
    global VERIFIER_MODEL, VERIFIER_AVAILABLE
    
    try:
        VERIFIER_MODEL = genai.GenerativeModel(gemini_model)
        VERIFIER_AVAILABLE = True
        print("✅ Gemini verifier initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize Gemini verifier: {e}")
        VERIFIER_AVAILABLE = False
        return False

def verify_item_name_price(item: Dict[str, Any], image_bytes: bytes) -> Dict[str, Any]:
    """
    Verify the name and price plausibility of a single item using Gemini verifier.
    
    Args:
        item: Dictionary containing item details (name, brand, model, price_usd)
        image_bytes: Raw image bytes
        
    Returns:
        Dict: The item with added namePriceScore and namePriceNotes fields
    """
    if not VERIFIER_AVAILABLE or VERIFIER_MODEL is None:
        # Fallback: add null fields if verifier is not available
        item['namePriceScore'] = None
        item['namePriceNotes'] = "verifier_unavailable"
        return item
    
    try:
        # Extract item details
        title = item.get('name', '')
        brand = item.get('brand', '')
        model = item.get('model', '')
        price_usd = item.get('price_usd', 0)
        
        # Convert image bytes to PIL Image
        image_pil = Image.open(io.BytesIO(image_bytes))
        
        # Create the verification prompt
        prompt = f"""You are a strict, JSON-only evaluator. Given an image and a product prediction, return ONLY JSON: {{ "namePriceScore": <0.0-1.0>, "namePriceNotes": "<short rationale>" }}. Judge **only** the plausibility of the name and price, based on visible cues (silhouette, materials, logos/text) and typical price ranges (new/used). No browsing.

PRODUCER PREDICTION
Title/Name: {title}
Brand: {brand}
Model: {model}
Price (USD): {price_usd}

TASK
Look at the provided image and score the plausibility of the NAME and PRICE only.
Output STRICT JSON:
{{ "namePriceScore": <0.0-1.0>, "namePriceNotes": "<short rationale>" }}"""
        
        # Run verifier with Gemini
        response = VERIFIER_MODEL.generate_content(
            [prompt, image_pil],
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        
        # Parse JSON response
        result_text = response.text.strip()
        
        # Try to parse as JSON
        try:
            parsed = json.loads(result_text)
        except json.JSONDecodeError:
            # Try to extract JSON from the response using regex
            json_match = re.search(r'\{[^}]*"namePriceScore"[^}]*\}', result_text)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                raise ValueError("No valid JSON found in response")
        
        # Extract and validate fields
        name_price_score = parsed.get('namePriceScore')
        name_price_notes = parsed.get('namePriceNotes', '')
        
        # Clamp score to [0.0, 1.0] if present
        if name_price_score is not None:
            try:
                name_price_score = float(name_price_score)
                name_price_score = max(0.0, min(1.0, name_price_score))
            except (ValueError, TypeError):
                name_price_score = None
        
        # Add fields to item
        item['namePriceScore'] = name_price_score
        item['namePriceNotes'] = name_price_notes
        
        return item
        
    except Exception as e:
        print(f"❌ Verifier error for item {item.get('name', 'unknown')}: {e}")
        # On error, add null fields
        item['namePriceScore'] = None
        item['namePriceNotes'] = f"verifier_error: {str(e)[:50]}"
        return item

def verify_items_bulk(items: List[Dict[str, Any]], image_bytes: bytes, batch_size: int = 5) -> List[Dict[str, Any]]:
    """
    Verify multiple items in bulk to reduce API calls.
    
    Args:
        items: List of item dictionaries to verify
        image_bytes: Raw image bytes
        batch_size: Number of items to verify per API call
        
    Returns:
        List: Items with added namePriceScore and namePriceNotes fields
    """
    if not VERIFIER_AVAILABLE or VERIFIER_MODEL is None:
        # Fallback: add null fields if verifier is not available
        for item in items:
            item['namePriceScore'] = None
            item['namePriceNotes'] = "verifier_unavailable"
        return items
    
    try:
        # Convert image bytes to PIL Image
        image_pil = Image.open(io.BytesIO(image_bytes))
        
        # Process items in batches
        verified_items = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            print(f"[API] Verifying batch {i//batch_size + 1}: {len(batch)} items")
            
            # Create bulk verification prompt
            items_text = ""
            for j, item in enumerate(batch):
                title = item.get('name', '')
                brand = item.get('brand', '')
                model = item.get('model', '')
                price_usd = item.get('price_usd', 0)
                items_text += f"Item {j+1}:\n"
                items_text += f"  Title/Name: {title}\n"
                items_text += f"  Brand: {brand}\n"
                items_text += f"  Model: {model}\n"
                items_text += f"  Price (USD): {price_usd}\n\n"
            
            # Create bulk verification prompt
            bulk_prompt = f"""You are a strict, JSON-only evaluator. Given an image and multiple product predictions, return ONLY JSON with scores for each item. Judge **only** the plausibility of the name and price, based on visible cues (silhouette, materials, logos/text) and typical price ranges (new/used). No browsing.

PRODUCER PREDICTIONS
{items_text}

TASK
Look at the provided image and score the plausibility of the NAME and PRICE for each item.
Output STRICT JSON array:
[
  {{ "itemIndex": 0, "namePriceScore": <0.0-1.0>, "namePriceNotes": "<short rationale>" }},
  {{ "itemIndex": 1, "namePriceScore": <0.0-1.0>, "namePriceNotes": "<short rationale>" }},
  ...
]"""
            
            # Run bulk verification with Gemini
            response = VERIFIER_MODEL.generate_content(
                [bulk_prompt, image_pil],
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            
            # Parse JSON response
            result_text = response.text.strip()
            
            # Try to parse as JSON array
            try:
                parsed_results = json.loads(result_text)
            except json.JSONDecodeError:
                # Try to extract JSON array from the response using regex
                json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
                if json_match:
                    parsed_results = json.loads(json_match.group())
                else:
                    raise ValueError("No valid JSON array found in response")
            
            # Apply results to items
            for result_item in parsed_results:
                item_index = result_item.get('itemIndex', 0)
                if 0 <= item_index < len(batch):
                    name_price_score = result_item.get('namePriceScore')
                    name_price_notes = result_item.get('namePriceNotes', '')
                    
                    # Clamp score to [0.0, 1.0] if present
                    if name_price_score is not None:
                        try:
                            name_price_score = float(name_price_score)
                            name_price_score = max(0.0, min(1.0, name_price_score))
                        except (ValueError, TypeError):
                            name_price_score = None
                    
                    batch[item_index]['namePriceScore'] = name_price_score
                    batch[item_index]['namePriceNotes'] = name_price_notes
            
            verified_items.extend(batch)
        
        return verified_items
        
    except Exception as e:
        print(f"❌ Bulk verifier error: {e}")
        # On error, add null fields to all items
        for item in items:
            item['namePriceScore'] = None
            item['namePriceNotes'] = f"bulk_verifier_error: {str(e)[:50]}"
        return items

def is_verifier_available() -> bool:
    """
    Check if the verifier is available and initialized.
    
    Returns:
        bool: True if verifier is available, False otherwise
    """
    return VERIFIER_AVAILABLE and VERIFIER_MODEL is not None

# Initialize verifier on module import
initialize_verifier()
