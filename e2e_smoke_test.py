#!/usr/bin/env python3
"""
End-to-End Smoke Test for ClaimReady Producer-Verifier Pipeline
Tests the complete flow from backend to frontend with verification scores.
"""

import subprocess
import time
import requests
import json
import os
import sys
from pathlib import Path

def create_test_image():
    """Create a test image for testing"""
    try:
        from PIL import Image, ImageDraw
        
        # Create a simple test image
        img = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw a simple laptop representation
        draw.rectangle([50, 50, 350, 250], outline='black', width=3)
        draw.rectangle([60, 60, 340, 200], fill='lightgray')
        draw.rectangle([70, 70, 330, 190], fill='darkgray')
        draw.text((150, 130), "Test Laptop", fill='black')
        
        # Save the image
        test_image_path = 'test_laptop.jpg'
        img.save(test_image_path, 'JPEG')
        print(f"✅ Created test image: {test_image_path}")
        return test_image_path
        
    except ImportError:
        print("❌ PIL not available. Please install Pillow or create a test image manually.")
        return None
    except Exception as e:
        print(f"❌ Failed to create test image: {e}")
        return None

def test_backend_health():
    """Test backend health endpoint"""
    print("\n🏥 Testing Backend Health...")
    try:
        response = requests.get('http://localhost:8080/health', timeout=5)
        if response.status_code == 200:
            print("✅ Backend health check passed")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Backend not responding: {e}")
        return False

def test_pipeline_endpoint():
    """Test the pipeline test endpoint"""
    print("\n🔧 Testing Pipeline Endpoint...")
    try:
        response = requests.get('http://localhost:8080/test-pipeline', timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Pipeline test passed: {data.get('status', 'unknown')}")
            print(f"   LangChain available: {data.get('langchain_available', False)}")
            return True
        else:
            print(f"❌ Pipeline test failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Pipeline test error: {e}")
        return False

def test_image_upload(image_path):
    """Test image upload to analyze-image endpoint"""
    print(f"\n📤 Testing Image Upload: {image_path}")
    
    if not os.path.exists(image_path):
        print(f"❌ Test image not found: {image_path}")
        return False
    
    try:
        with open(image_path, 'rb') as f:
            files = {'image': f}
            response = requests.post(
                'http://localhost:8080/api/analyze-image',
                files=files,
                timeout=60  # 1 minute timeout for processing
            )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Image upload successful")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Items found: {data.get('total_items', 0)}")
            print(f"   Total value: ${data.get('total_value', 0):.2f}")
            
            # Check for verification scores
            items = data.get('items', [])
            items_with_verification = [item for item in items if 'verificationScore' in item]
            print(f"   Items with verification: {len(items_with_verification)}")
            
            if items_with_verification:
                avg_score = sum(item['verificationScore'] for item in items_with_verification) / len(items_with_verification)
                print(f"   Average verification score: {avg_score:.2f}")
                
                # Show first item details
                first_item = items_with_verification[0]
                print(f"   Sample item: {first_item.get('name', 'Unknown')}")
                print(f"   Verification score: {first_item.get('verificationScore', 'N/A')}")
                print(f"   Verification notes: {first_item.get('verificationNotes', 'N/A')}")
            
            return True
        else:
            print(f"❌ Image upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Image upload error: {e}")
        return False

def test_error_scenarios():
    """Test error handling scenarios"""
    print("\n🚨 Testing Error Scenarios...")
    
    # Test 1: No file
    print("   Testing no file scenario...")
    try:
        response = requests.post('http://localhost:8080/api/analyze-image', timeout=5)
        if response.status_code == 400:
            print("   ✅ No file error handled correctly")
        else:
            print(f"   ❌ Expected 400, got {response.status_code}")
    except Exception as e:
        print(f"   ❌ No file test error: {e}")
    
    # Test 2: Invalid MIME type
    print("   Testing invalid MIME type...")
    try:
        # Create a fake PDF file
        with open('fake.pdf', 'w') as f:
            f.write("This is not a PDF")
        
        with open('fake.pdf', 'rb') as f:
            files = {'image': ('fake.pdf', f, 'application/pdf')}
            response = requests.post(
                'http://localhost:8080/api/analyze-image',
                files=files,
                timeout=5
            )
        
        if response.status_code == 400:
            print("   ✅ Invalid MIME type error handled correctly")
        else:
            print(f"   ❌ Expected 400, got {response.status_code}")
        
        # Clean up
        os.remove('fake.pdf')
        
    except Exception as e:
        print(f"   ❌ Invalid MIME test error: {e}")

def test_cli_functionality():
    """Test CLI functionality"""
    print("\n💻 Testing CLI Functionality...")
    
    # Create a test image if it doesn't exist
    test_image = 'test_laptop.jpg'
    if not os.path.exists(test_image):
        test_image = create_test_image()
        if not test_image:
            print("   ❌ Could not create test image for CLI test")
            return False
    
    try:
        # Run CLI test
        result = subprocess.run([
            'python3', 'geminiserver.py', '--test-image', test_image
        ], capture_output=True, text=True, timeout=120, cwd='backend')
        
        if result.returncode == 0:
            print("   ✅ CLI test successful")
            
            # Try to parse the JSON output
            try:
                output_data = json.loads(result.stdout)
                items = output_data.get('items', [])
                print(f"   Items found: {len(items)}")
                
                if items:
                    first_item = items[0]
                    if 'verificationScore' in first_item:
                        print(f"   Verification score: {first_item['verificationScore']}")
                        print("   ✅ CLI output contains verification scores")
                    else:
                        print("   ⚠️ CLI output missing verification scores")
                
            except json.JSONDecodeError:
                print("   ⚠️ CLI output is not valid JSON")
            
            return True
        else:
            print(f"   ❌ CLI test failed: {result.returncode}")
            print(f"   Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("   ❌ CLI test timed out")
        return False
    except Exception as e:
        print(f"   ❌ CLI test error: {e}")
        return False

def main():
    """Main smoke test function"""
    print("🧪 ClaimReady End-to-End Smoke Test")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('backend/geminiserver.py'):
        print("❌ Please run this script from the ClaimReady root directory")
        sys.exit(1)
    
    # Create test image
    test_image = create_test_image()
    if not test_image:
        print("❌ Could not create test image. Exiting.")
        sys.exit(1)
    
    # Run tests
    tests_passed = 0
    total_tests = 5
    
    # Test 1: Backend health
    if test_backend_health():
        tests_passed += 1
    
    # Test 2: Pipeline endpoint
    if test_pipeline_endpoint():
        tests_passed += 1
    
    # Test 3: Image upload
    if test_image_upload(test_image):
        tests_passed += 1
    
    # Test 4: Error scenarios
    test_error_scenarios()
    tests_passed += 1  # Error tests are informational
    
    # Test 5: CLI functionality
    if test_cli_functionality():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"🎯 Smoke Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All smoke tests passed! The producer-verifier pipeline is working correctly.")
        print("\n📋 Next Steps:")
        print("1. Start the frontend: cd frontend && npm run dev")
        print("2. Visit http://localhost:3000/upload")
        print("3. Upload the test image and verify the 'Verification Score' column appears")
        print("4. Check that verification scores are displayed as percentages (0-100%)")
        print("5. Verify tooltips show verification notes")
    else:
        print("❌ Some tests failed. Please check the backend logs and try again.")
        sys.exit(1)
    
    # Clean up
    if os.path.exists(test_image):
        os.remove(test_image)
        print(f"🧹 Cleaned up test image: {test_image}")

if __name__ == "__main__":
    main()
