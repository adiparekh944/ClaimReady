#!/usr/bin/env python3
"""
Test script for the CLI functionality
Demonstrates how to use the --test-image flag
"""

import subprocess
import sys
import os
import json

def test_cli_with_sample_image():
    """Test the CLI with a sample image"""
    
    # Check if we have a sample image
    sample_images = [
        './samples/laptop.jpg',
        './samples/chair.png', 
        './samples/room.jpg',
        './test_image.jpg'
    ]
    
    sample_image = None
    for img_path in sample_images:
        if os.path.exists(img_path):
            sample_image = img_path
            break
    
    if not sample_image:
        print("❌ No sample images found. Please create a test image or add one to the samples/ directory.")
        print("Available paths checked:", sample_images)
        return False
    
    print(f"🧪 Testing CLI with sample image: {sample_image}")
    
    try:
        # Run the CLI test
        cmd = [sys.executable, 'geminiserver.py', '--test-image', sample_image]
        print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode == 0:
            print("✅ CLI test successful!")
            print("📊 Output:")
            
            # Parse and pretty print the JSON output
            try:
                output_json = json.loads(result.stdout)
                print(json.dumps(output_json, indent=2))
                
                # Check if verification scores are present
                items = output_json.get('items', [])
                items_with_verification = [item for item in items if 'verificationScore' in item]
                
                print(f"\n📈 Summary:")
                print(f"  - Total items: {len(items)}")
                print(f"  - Items with verification: {len(items_with_verification)}")
                
                if items_with_verification:
                    avg_score = sum(item['verificationScore'] for item in items_with_verification) / len(items_with_verification)
                    print(f"  - Average verification score: {avg_score:.2f}")
                
            except json.JSONDecodeError as e:
                print(f"⚠️ Could not parse JSON output: {e}")
                print("Raw output:", result.stdout)
            
            return True
        else:
            print("❌ CLI test failed!")
            print("Error output:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ CLI test timed out (10 minutes)")
        return False
    except Exception as e:
        print(f"❌ CLI test error: {e}")
        return False

def create_test_image():
    """Create a simple test image if none exists"""
    try:
        from PIL import Image, ImageDraw
        import os
        
        # Create samples directory if it doesn't exist
        os.makedirs('samples', exist_ok=True)
        
        # Create a simple test image
        img = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw a simple rectangle (representing a laptop)
        draw.rectangle([50, 50, 350, 250], outline='black', width=3)
        draw.rectangle([60, 60, 340, 200], fill='lightgray')
        draw.rectangle([70, 70, 330, 190], fill='darkgray')
        
        # Add some text
        draw.text((150, 130), "Test Laptop", fill='black')
        
        test_image_path = 'samples/test_laptop.jpg'
        img.save(test_image_path, 'JPEG')
        print(f"✅ Created test image: {test_image_path}")
        return test_image_path
        
    except ImportError:
        print("❌ PIL not available. Please install Pillow or add a test image manually.")
        return None
    except Exception as e:
        print(f"❌ Failed to create test image: {e}")
        return None

if __name__ == "__main__":
    print("🧪 ClaimReady CLI Test")
    print("=" * 50)
    
    # Try to find or create a test image
    sample_images = [
        './samples/laptop.jpg',
        './samples/chair.png', 
        './samples/room.jpg',
        './test_image.jpg'
    ]
    
    test_image = None
    for img_path in sample_images:
        if os.path.exists(img_path):
            test_image = img_path
            break
    
    if not test_image:
        print("No test images found. Creating one...")
        test_image = create_test_image()
    
    if test_image:
        success = test_cli_with_sample_image()
        if success:
            print("\n🎉 CLI test completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ CLI test failed!")
            sys.exit(1)
    else:
        print("❌ No test image available")
        sys.exit(1)
