"""
LangChain Verifier Module for Name/Price Verification

This module provides a LangChain-based verifier that scores the plausibility
of item names and prices based on visual cues in images.
"""

import os
import json
import re
from typing import Dict, Any, Optional

# Set up environment variables for LangChain
GEMINI_API_KEY = "AIzaSyDVIppKcsZwVa3vkZWazztC9XY_-oZUufU"
os.environ['GOOGLE_API_KEY'] = GEMINI_API_KEY
os.environ['GEMINI_API_KEY'] = GEMINI_API_KEY

# LangChain imports with graceful degradation
LANGCHAIN_AVAILABLE = True
VERIFIER_LLM = None
VERIFIER_CHAIN = None

try:
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError as e:
    print(f"Warning: LangChain not available: {e}")
    LANGCHAIN_AVAILABLE = False

def initialize_verifier(gemini_model: str = "gemini-2.5-flash") -> bool:
    """
    Initialize the LangChain verifier.
    
    Args:
        gemini_model: The Gemini model to use
        
    Returns:
        bool: True if initialization successful, False otherwise
    """
    global VERIFIER_LLM, VERIFIER_CHAIN
    
    if not LANGCHAIN_AVAILABLE:
        print("❌ LangChain not available, verifier disabled")
        return False
    
    try:
        VERIFIER_LLM = ChatGoogleGenerativeAI(
            model=gemini_model,
            temperature=0.1,  # Low temperature for consistent scoring
            max_output_tokens=1024,
            convert_system_message_to_human=True
        )
        
        # Verifier prompt template
        verifier_prompt = PromptTemplate(
            input_variables=["title", "brand", "model", "price_usd", "image_bytes"],
            template="""You are a strict, JSON-only evaluator. Given an image and a product prediction {{title/name, brand, model, price_usd}}, return ONLY JSON: {{ "namePriceScore": <0.0-1.0>, "namePriceNotes": "<short rationale>" }}. Judge **only** the plausibility of the name and price, based on visible cues (silhouette, materials, logos/text) and typical price ranges (new/used). No browsing.

PRODUCER PREDICTION
Title/Name: {title}
Brand: {brand}
Model: {model}
Price (USD): {price_usd}

TASK
Look at the provided image and score the plausibility of the NAME and PRICE only.
Output STRICT JSON:
{{ "namePriceScore": <0.0-1.0>, "namePriceNotes": "<short rationale>" }}"""
        )
        
        VERIFIER_CHAIN = LLMChain(
            llm=VERIFIER_LLM,
            prompt=verifier_prompt,
            verbose=True
        )
        print("✅ LangChain verifier initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize LangChain verifier: {e}")
        return False

def verify_item_name_price(item: Dict[str, Any], image_bytes: bytes) -> Dict[str, Any]:
    """
    Verify the name and price plausibility of a single item using LangChain verifier.
    
    Args:
        item: Dictionary containing item details (name, brand, model, price_usd)
        image_bytes: Raw image bytes
        
    Returns:
        Dict: The item with added namePriceScore and namePriceNotes fields
    """
    if not LANGCHAIN_AVAILABLE or VERIFIER_CHAIN is None:
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
        
        # Convert image bytes to PIL Image for LangChain
        from PIL import Image
        import io
        image_pil = Image.open(io.BytesIO(image_bytes))
        
        # Run verifier chain
        result = VERIFIER_CHAIN.run(
            title=title,
            brand=brand,
            model=model,
            price_usd=price_usd,
            image_bytes=image_pil
        )
        
        # Parse JSON response
        clean_result = result.strip()
        if clean_result.startswith('```json'):
            clean_result = clean_result[7:]
        if clean_result.startswith('```'):
            clean_result = clean_result[3:]
        if clean_result.endswith('```'):
            clean_result = clean_result[:-3]
        clean_result = clean_result.strip()
        
        # Try to parse as JSON
        try:
            parsed = json.loads(clean_result)
        except json.JSONDecodeError:
            # Try to extract JSON from the response using regex
            json_match = re.search(r'\{[^}]*"namePriceScore"[^}]*\}', clean_result)
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

def is_verifier_available() -> bool:
    """
    Check if the verifier is available and initialized.
    
    Returns:
        bool: True if verifier is available, False otherwise
    """
    return LANGCHAIN_AVAILABLE and VERIFIER_CHAIN is not None

# Initialize verifier on module import
initialize_verifier()
