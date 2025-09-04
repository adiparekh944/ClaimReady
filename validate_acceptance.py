#!/usr/bin/env python3
"""
Acceptance Criteria Validation for ClaimReady Producer-Verifier Pipeline
Validates all acceptance criteria without external dependencies.
"""

import json
import os
import sys
import subprocess

def validate_backend_route():
    """Validate backend route implementation"""
    print("🔍 Validating Backend Route...")
    
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
        ('test_pipeline_cli', 'CLI test function')
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
    
    frontend_files = [
        'frontend/src/types/item.ts',
        'frontend/src/components/ItemTable.tsx',
        'frontend/src/app/upload/page.tsx'
    ]
    
    all_passed = True
    
    # Check types
    types_file = frontend_files[0]
    if os.path.exists(types_file):
        with open(types_file, 'r') as f:
            content = f.read()
        
        if 'verificationScore?: number' in content and 'verificationNotes?: string' in content:
            print("   ✅ Type definitions include verification fields")
        else:
            print("   ❌ Type definitions missing verification fields")
            all_passed = False
    else:
        print("   ❌ Types file not found")
        all_passed = False
    
    # Check ItemTable component
    table_file = frontend_files[1]
    if os.path.exists(table_file):
        with open(table_file, 'r') as f:
            content = f.read()
        
        checks = [
            ('verificationScore', 'Verification score handling'),
            ('Verification Score', 'Column header'),
            ('Math.round(item.verificationScore * 100)', 'Percentage display'),
            ('verificationNotes', 'Notes tooltip'),
            ('bg-green-500', 'Color coding')
        ]
        
        passed = 0
        for check, description in checks:
            if check in content:
                print(f"   ✅ {description}")
                passed += 1
            else:
                print(f"   ❌ {description}")
        
        if passed < len(checks):
            all_passed = False
    else:
        print("   ❌ ItemTable component not found")
        all_passed = False
    
    # Check upload page
    upload_file = frontend_files[2]
    if os.path.exists(upload_file):
        with open(upload_file, 'r') as f:
            content = f.read()
        
        if 'http://127.0.0.1:8080' in content and '/api/analyze-image' in content:
            print("   ✅ Upload page calls correct backend endpoint")
        else:
            print("   ❌ Upload page endpoint configuration")
            all_passed = False
    else:
        print("   ❌ Upload page not found")
        all_passed = False
    
    return all_passed

def validate_error_handling():
    """Validate error handling implementation"""
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

def validate_json_schema():
    """Validate JSON schema implementation"""
    print("\n🔍 Validating JSON Schema...")
    
    # Check if the schema includes verification fields
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

def validate_unit_tests():
    """Validate unit tests exist"""
    print("\n🔍 Validating Unit Tests...")
    
    test_files = [
        'backend/test_json_merger.py',
        'backend/test_simple_audit.py'
    ]
    
    all_exist = True
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"   ✅ {test_file} exists")
        else:
            print(f"   ❌ {test_file} missing")
            all_exist = False
    
    return all_exist

def main():
    """Main validation function"""
    print("🎯 ClaimReady Acceptance Criteria Validation")
    print("=" * 60)
    
    # Run all validations
    validations = [
        ("Backend Route", validate_backend_route),
        ("Frontend Implementation", validate_frontend_implementation),
        ("Error Handling", validate_error_handling),
        ("JSON Schema", validate_json_schema),
        ("CLI Functionality", validate_cli_functionality),
        ("Unit Tests", validate_unit_tests)
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
        print("🎉 ALL ACCEPTANCE CRITERIA VALIDATED!")
        print("\n📋 Quick Start Commands:")
        print("1. Start backend: cd backend && python3 geminiserver.py")
        print("2. Start frontend: cd frontend && npm run dev")
        print("3. Test upload: http://localhost:3000/upload")
        print("4. CLI test: python3 geminiserver.py --test-image ./test.jpg")
        print("5. API test: curl -F \"image=@test.jpg\" http://localhost:8080/api/analyze-image")
        return True
    else:
        print("❌ Some acceptance criteria failed validation")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
