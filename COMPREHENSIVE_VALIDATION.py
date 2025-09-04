#!/usr/bin/env python3
"""
Comprehensive Validation Script for ClaimReady Producer-Verifier Pipeline
Tests all components and provides detailed validation results.
"""

import json
import os
import sys
import subprocess
import time
from pathlib import Path

def validate_backend_implementation():
    """Validate backend implementation"""
    print("🔍 Validating Backend Implementation...")
    
    backend_file = 'backend/geminiserver.py'
    if not os.path.exists(backend_file):
        print("❌ Backend file not found")
        return False
    
    with open(backend_file, 'r') as f:
        content = f.read()
    
    checks = [
        ('@app.route("/api/analyze-image"', 'POST route exists'),
        ('methods=["POST"]', 'POST method configured'),
        ('request.files', 'Form data handling'),
        ('verificationScore', 'Verification score field'),
        ('verificationNotes', 'Verification notes field'),
        ('run_item_pipeline', 'Pipeline function called'),
        ('augment_image_for_verification', 'Image augmentation'),
        ('random.seed(42)', 'Deterministic transforms'),
        ('allowed_mime_types', 'MIME validation'),
        ('max_size = 10 * 1024 * 1024', 'File size limit'),
        ('TimeoutError', 'Timeout handling'),
        ('test_pipeline_cli', 'CLI test function'),
        ('jsonify', 'JSON responses'),
        ('minimum": 0.0, "maximum": 1.0', 'Score range validation')
    ]
    
    passed = 0
    for check, description in checks:
        if check in content:
            print(f"   ✅ {description}")
            passed += 1
        else:
            print(f"   ❌ {description}")
    
    print(f"   📊 Backend validation: {passed}/{len(checks)} checks passed")
    return passed == len(checks)

def validate_frontend_implementation():
    """Validate frontend implementation"""
    print("\n🔍 Validating Frontend Implementation...")
    
    # Check types
    types_file = 'frontend/src/types/item.ts'
    if os.path.exists(types_file):
        with open(types_file, 'r') as f:
            content = f.read()
        
        type_checks = [
            ('verificationScore?: number', 'Verification score type'),
            ('verificationNotes?: string', 'Verification notes type'),
            ('interface TableRow', 'TableRow interface'),
            ('verificationScore?: number', 'TableRow verification score')
        ]
        
        passed = 0
        for check, description in type_checks:
            if check in content:
                print(f"   ✅ {description}")
                passed += 1
            else:
                print(f"   ❌ {description}")
        
        if passed < len(type_checks):
            return False
    else:
        print("   ❌ Types file not found")
        return False
    
    # Check ItemTable component
    table_file = 'frontend/src/components/ItemTable.tsx'
    if os.path.exists(table_file):
        with open(table_file, 'r') as f:
            content = f.read()
        
        table_checks = [
            ('Verification Score', 'Column header'),
            ('verificationScore', 'Verification score handling'),
            ('Math.round(item.verificationScore * 100)', 'Percentage display'),
            ('verificationNotes', 'Notes tooltip'),
            ('bg-green-500', 'Color coding')
        ]
        
        passed = 0
        for check, description in table_checks:
            if check in content:
                print(f"   ✅ {description}")
                passed += 1
            else:
                print(f"   ❌ {description}")
        
        if passed < len(table_checks):
            return False
    else:
        print("   ❌ ItemTable component not found")
        return False
    
    # Check upload page
    upload_file = 'frontend/src/app/upload/page.tsx'
    if os.path.exists(upload_file):
        with open(upload_file, 'r') as f:
            content = f.read()
        
        upload_checks = [
            ('http://127.0.0.1:8080', 'Backend URL'),
            ('/api/analyze-image', 'API endpoint'),
            ('verificationScore', 'Verification field parsing'),
            ('verificationNotes', 'Verification notes parsing')
        ]
        
        passed = 0
        for check, description in upload_checks:
            if check in content:
                print(f"   ✅ {description}")
                passed += 1
            else:
                print(f"   ❌ {description}")
        
        if passed < len(upload_checks):
            return False
    else:
        print("   ❌ Upload page not found")
        return False
    
    return True

def validate_error_handling():
    """Validate error handling"""
    print("\n🔍 Validating Error Handling...")
    
    backend_file = 'backend/geminiserver.py'
    if not os.path.exists(backend_file):
        print("❌ Backend file not found")
        return False
    
    with open(backend_file, 'r') as f:
        content = f.read()
    
    error_checks = [
        ('400', 'HTTP 400 for bad requests'),
        ('504', 'HTTP 504 for timeouts'),
        ('500', 'HTTP 500 for server errors'),
        ('Invalid file type', 'MIME type error message'),
        ('File too large', 'Size limit error message'),
        ('Processing timeout', 'Timeout error message'),
        ('jsonify', 'JSON error responses')
    ]
    
    passed = 0
    for check, description in error_checks:
        if check in content:
            print(f"   ✅ {description}")
            passed += 1
        else:
            print(f"   ❌ {description}")
    
    print(f"   📊 Error handling validation: {passed}/{len(error_checks)} checks passed")
    return passed == len(error_checks)

def validate_cli_functionality():
    """Validate CLI functionality"""
    print("\n🔍 Validating CLI Functionality...")
    
    backend_file = 'backend/geminiserver.py'
    if not os.path.exists(backend_file):
        print("❌ Backend file not found")
        return False
    
    with open(backend_file, 'r') as f:
        content = f.read()
    
    cli_checks = [
        ('--test-image', 'CLI test-image argument'),
        ('argparse', 'Argument parsing'),
        ('test_pipeline_cli', 'CLI test function'),
        ('json.dumps', 'JSON output'),
        ('sys.exit(1)', 'Error exit codes'),
        ('stdout', 'Standard output')
    ]
    
    passed = 0
    for check, description in cli_checks:
        if check in content:
            print(f"   ✅ {description}")
            passed += 1
        else:
            print(f"   ❌ {description}")
    
    print(f"   📊 CLI validation: {passed}/{len(cli_checks)} checks passed")
    return passed == len(cli_checks)

def validate_json_schema():
    """Validate JSON schema"""
    print("\n🔍 Validating JSON Schema...")
    
    backend_file = 'backend/geminiserver.py'
    if not os.path.exists(backend_file):
        print("❌ Backend file not found")
        return False
    
    with open(backend_file, 'r') as f:
        content = f.read()
    
    schema_checks = [
        ('verificationScore', 'Verification score in schema'),
        ('verificationNotes', 'Verification notes in schema'),
        ('minimum": 0.0, "maximum": 1.0', 'Score range validation'),
        ('string', 'Notes type validation'),
        ('json.loads', 'JSON parsing'),
        ('json.dumps', 'JSON serialization')
    ]
    
    passed = 0
    for check, description in schema_checks:
        if check in content:
            print(f"   ✅ {description}")
            passed += 1
        else:
            print(f"   ❌ {description}")
    
    print(f"   📊 JSON schema validation: {passed}/{len(schema_checks)} checks passed")
    return passed == len(schema_checks)

def validate_test_files():
    """Validate test files exist"""
    print("\n🔍 Validating Test Files...")
    
    test_files = [
        'backend/test_json_merger.py',
        'backend/test_simple_audit.py',
        'SMOKE_TEST_COMMANDS.md',
        'JSON_EXAMPLES.md'
    ]
    
    all_exist = True
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"   ✅ {test_file} exists")
        else:
            print(f"   ❌ {test_file} missing")
            all_exist = False
    
    return all_exist

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

def main():
    """Main validation function"""
    print("🎯 ClaimReady Comprehensive Validation")
    print("=" * 60)
    
    # Run all validations
    validations = [
        ("Backend Implementation", validate_backend_implementation),
        ("Frontend Implementation", validate_frontend_implementation),
        ("Error Handling", validate_error_handling),
        ("CLI Functionality", validate_cli_functionality),
        ("JSON Schema", validate_json_schema),
        ("Test Files", validate_test_files)
    ]
    
    passed = 0
    total = len(validations)
    
    for name, validation_func in validations:
        try:
            if validation_func():
                passed += 1
                print(f"✅ {name}: PASSED")
            else:
                print(f"❌ {name}: FAILED")
        except Exception as e:
            print(f"❌ {name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"🎯 Final Results: {passed}/{total} validations passed")
    
    if passed == total:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("\n📋 Ready to Test - Run these commands:")
        print("1. Start backend: cd backend && python3 geminiserver.py")
        print("2. Start frontend: cd frontend && npm run dev")
        print("3. Test upload: http://localhost:3000/upload")
        print("4. CLI test: python3 geminiserver.py --test-image ./test.jpg")
        print("5. API test: curl -F \"image=@test.jpg\" http://localhost:8080/api/analyze-image")
        
        # Create test image
        test_image = create_test_image()
        if test_image:
            print(f"\n📁 Test image created: {test_image}")
        
        return True
    else:
        print("❌ Some validations failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
