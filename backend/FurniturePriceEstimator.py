import os
import base64
import google.generativeai as genai
from PIL import Image
import io
import ast
import requests
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Setup API key from environment variables
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in environment variables")
genai.configure(api_key=GEMINI_API_KEY)

class FurniturePriceEstimator:
    def __init__(self):
        # Initialize Gemini model
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')

    def analyze_item_with_gemini(self, image_data):
        """
        Analyzes an image of furniture and returns a tuple of (name, price).
        
        Args:
            image_data: Either a bytes object containing image data or a PIL Image object
            
        Returns:
            tuple: (name: str, price: int)
        """
        # Convert image data to PIL Image
        if isinstance(image_data, bytes):
            image = Image.open(io.BytesIO(image_data))
        else:
            image = image_data  # Assume it's already a PIL Image
        
        '''Untested prompt
        Alt Prompt 1:
        prompt = "You are a world-class insurance appraiser specializing in household contents. Given a high-resolution image of a single item (filling at least 90% of the frame), perform the following:
        1. Identify the object as specifically as possible (e.g., '2021 Samsung 55-inch QLED TV', 'Mid-century modern walnut dining chair', 'Dyson V11 cordless vacuum').
        2. If the brand, model, or year is visible, include it in the name. If not, infer the most likely type and style based on visual cues.
        3. Assess the object's condition (new, like new, good, fair, poor) based on visible wear, damage, or age indicators. If uncertain, assume 'good'.
        4. Estimate a conservative replacement value in USD, using recent US market data for similar items in similar condition. If the image is blurry, poorly lit, or ambiguous, err on the side of a lower value.
        5. If the item is rare, custom, or not a common household object, return a price of 0 and label as 'uncommon/unknown item'.
        6. If multiple items are visible, focus only on the most prominent one.
        7. Output a JSON array: ["short, specific item name (3-7 words)", integer price]. Do not include any explanation, commentary, or extra text. Only output the array."
        
        Alt Prompt 2:
        prompt = "You are an expert AI for insurance claims and home inventory. Given a single image of a household item (object fills most of the frame):
        - Identify the item as specifically as possible, including brand/model/year if visible. If not, use the most likely generic name.
        - If the image is unclear, dark, or the object is partially obscured, state 'uncertain item' and set price to 0.
        - If the item is a set (e.g., stack of plates), estimate the value for the entire set, but note as 'set of X' in the name.
        - For electronics, consider depreciation and current resale value, not original MSRP.
        - For furniture, consider style, material, and visible condition. If the item appears antique or custom, but cannot be verified, use a conservative estimate or 0.
        - If the object is not a typical household item (e.g., pet, plant, wall art, or background clutter), return ["non-inventory object", 0].
        - Output a Python list: ["concise, specific item name", integer price]. No extra output, no comments, no formatting."
        '''
        prompt = """
        Please analyze this item, make a conservative estimate of its price and and produce a single, number value between 1 and 1000000.
        If ever questioning the quality of the image or the premiumness of the item, choose a lower quartile price for the object.
        Analyze the object, and decide a very short description name for it, 3-7 words. Note that item will fill 90% of the frame.
        Your response should be a list of two values in the format of ["name of object", price] exactly.
        Only output the list, nothing else, do not include any other text or comments.
        The object should be a common household item, if it is not, be safe and return the name, but set the price to 0.
        """
        
        # Get response from Gemini
        response = self.model.generate_content([prompt, image])
        
        try:
            # Parse the response into a tuple
            result = ast.literal_eval(response.text)
            if isinstance(result, list) and len(result) == 2:
                return (result[0], int(result[1]))
            else:
                raise ValueError("Invalid response format")
        except (ValueError, SyntaxError) as e:
            raise ValueError(f"Could not parse response: {str(e)}")

    def insert_file_uploads(self, data):
        try:
            logging.info("Attempting to insert into file_uploads table...")
            response = supabase.table('file_uploads').insert(data).execute()
            logging.info("Insert response: %s", response)
        except Exception as e:
            logging.error("Insert into file_uploads failed: %s", e)
            raise