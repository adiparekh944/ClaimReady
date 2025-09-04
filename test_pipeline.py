#!/usr/bin/env python3
"""
Test script for the Producer-Verifier Pipeline
Tests the /api/analyze-image endpoint with a sample image
"""

import requests
import json
import os
from PIL import Image
import io

def test_pipeline():
    """Test the producer-verifier pipeline"""
    
    # Test endpoints
    base_url = "http://127.0.0.1:8080"
    
    print("🧪 Testing Producer-Verifier Pipeline")
    print("=" * 50)
    
    # Test 1: Health check
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return
    
    # Test 2: Pipeline test endpoint
    print("\n2. Testing pipeline test endpoint...")
    try:
        response = requests.get(f"{base_url}/test-pipeline")
        print(f"   Status: {response.status_code}")
        result = response.json()
        print(f"   LangChain Available: {result.get('langchain_available', False)}")
        print(f"   Producer Chain: {result.get('producer_chain', 'unknown')}")
        print(f"   Verifier Chain: {result.get('verifier_chain', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Pipeline test failed: {e}")
        return
    
    # Test 3: Create a test image and upload it
    print("\n3. Testing image analysis with verification...")
    try:
        # Create a simple test image (red square)
        test_image = Image.new('RGB', (200, 200), color='red')
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        # Upload to the API
        files = {'image': ('test_image.jpg', img_bytes, 'image/jpeg')}
        response = requests.post(f"{base_url}/api/analyze-image", files=files)
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            items = result.get('items', [])
            print(f"   Items found: {len(items)}")
            
            for i, item in enumerate(items):
                name = item.get('name', 'Unknown')
                score = item.get('verificationScore', 'N/A')
                notes = item.get('verificationNotes', 'No notes')
                print(f"   Item {i+1}: {name}")
                print(f"     Verification Score: {score}")
                print(f"     Verification Notes: {notes}")
        else:
            print(f"   ❌ Analysis failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Image analysis test failed: {e}")
    
    print("\n🎉 Pipeline test completed!")

if __name__ == "__main__":
    test_pipeline()
