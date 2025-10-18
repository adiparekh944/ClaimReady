#!/usr/bin/env python3
"""
Test script for the new CLIP-based architecture
Run this to test the newarchitecture.py server
"""

import requests
import json
import sys
import os

def test_clip_endpoint():
    """Test the new CLIP endpoint with a sample image"""
    
    # Check if server is running
    try:
        response = requests.get('http://localhost:8081/health', timeout=5)
        if response.status_code == 200:
            print("✅ New architecture server is running!")
            print(f"   Response: {response.json()}")
        else:
            print("❌ Server responded with error:", response.status_code)
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Server not running! Please start with: python newarchitecture.py")
        return False
    
    # Test with a sample image (you can replace this with any image path)
    test_image_path = "test_image.jpg"  # Replace with actual image path
    
    if not os.path.exists(test_image_path):
        print(f"⚠️  Test image not found: {test_image_path}")
        print("   Please place a test image in the backend directory")
        return False
    
    print(f"\n🧪 Testing with image: {test_image_path}")
    
    try:
        with open(test_image_path, 'rb') as f:
            files = {'image': f}
            response = requests.post('http://localhost:8081/api/analyze-image-clip', files=files)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ CLIP analysis successful!")
            print(f"   Objects detected: {len(result.get('objects', []))}")
            print(f"   Embeddings generated: {len(result.get('embeddings', []))}")
            print(f"   Processing time: {result.get('processing_time', 0):.2f}s")
            print(f"   Embedding dimension: {result.get('embedding_dimension', 0)}")
            
            # Show first embedding preview
            embeddings = result.get('embeddings', [])
            if embeddings:
                first_embedding = embeddings[0]['embedding']
                print(f"   First embedding preview: {first_embedding[:5]}...")
            
            return True
        else:
            print(f"❌ Analysis failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing New Architecture (CLIP-based)")
    print("="*50)
    
    success = test_clip_endpoint()
    
    if success:
        print("\n🎉 All tests passed!")
        print("   The new architecture is working correctly.")
    else:
        print("\n💥 Tests failed!")
        print("   Check the server logs for more details.")
        sys.exit(1)
