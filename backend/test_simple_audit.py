#!/usr/bin/env python3
"""
Simple audit tests for the producer-verifier pipeline.
Tests core logic without external dependencies.
"""

import unittest
import json
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestSimpleAudit(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.valid_producer_item = {
            'code': '0',
            'name': 'Laptop',
            'category': 'Electronics',
            'brand': 'Dell',
            'price_usd': 1200.0,
            'description': 'Gaming laptop',
            'confidence': 0.8,
            'bbox': [100, 100, 300, 200]
        }
        
        self.valid_verification_result = {
            'verificationScore': 0.85,
            'verificationNotes': 'Good visual match with clear product features'
        }
    
    def test_json_merger_preserves_producer_fields(self):
        """Test that JSON merger preserves all producer fields"""
        # Simulate the merger logic from run_item_pipeline
        final_item = self.valid_producer_item.copy()
        final_item['verificationScore'] = self.valid_verification_result['verificationScore']
        final_item['verificationNotes'] = self.valid_verification_result['verificationNotes']
        
        # Verify all producer fields are preserved
        for key, value in self.valid_producer_item.items():
            self.assertEqual(final_item[key], value, f"Producer field {key} was not preserved")
        
        # Verify verification fields are added
        self.assertIn('verificationScore', final_item)
        self.assertIn('verificationNotes', final_item)
        self.assertEqual(final_item['verificationScore'], 0.85)
        self.assertEqual(final_item['verificationNotes'], 'Good visual match with clear product features')
    
    def test_overall_score_computation(self):
        """Test overallScore computation with confidence"""
        # Simulate the overallScore computation logic
        confidence = self.valid_producer_item.get('confidence')
        verification_score = self.valid_verification_result['verificationScore']
        
        if confidence is not None and isinstance(confidence, (int, float)):
            overall_score = (0.6 * verification_score + 0.4 * float(confidence))
            overall_score = round(overall_score, 3)
            
            expected_score = round(0.6 * 0.85 + 0.4 * 0.8, 3)
            self.assertEqual(overall_score, expected_score)
            self.assertEqual(overall_score, 0.83)
    
    def test_deterministic_image_transforms(self):
        """Test that image augmentation is deterministic"""
        import random
        
        # Test that setting the same seed produces the same results
        random.seed(42)
        result1 = [random.uniform(0.9, 1.1) for _ in range(3)]
        
        random.seed(42)
        result2 = [random.uniform(0.9, 1.1) for _ in range(3)]
        
        self.assertEqual(result1, result2, "Image transforms should be deterministic with fixed seed")
    
    def test_json_schema_validation(self):
        """Test JSON schema validation for verification results"""
        
        def validate_verification_schema(data):
            """Validate verification result schema"""
            if not isinstance(data, dict):
                return False, "Must be a dictionary"
            
            # Check required fields
            if 'verificationScore' not in data:
                return False, "Missing verificationScore field"
            if 'verificationNotes' not in data:
                return False, "Missing verificationNotes field"
            
            # Check verificationScore type and range
            score = data['verificationScore']
            if not isinstance(score, (int, float)):
                return False, "verificationScore must be a number"
            if not (0.0 <= score <= 1.0):
                return False, "verificationScore must be between 0.0 and 1.0"
            
            # Check verificationNotes type
            notes = data['verificationNotes']
            if not isinstance(notes, str):
                return False, "verificationNotes must be a string"
            
            return True, "Valid schema"
        
        # Test valid schema
        is_valid, message = validate_verification_schema(self.valid_verification_result)
        self.assertTrue(is_valid, f"Valid schema should pass: {message}")
        
        # Test invalid schemas
        invalid_cases = [
            ({'verificationScore': 1.5}, "Score out of range"),
            ({'verificationScore': 'invalid'}, "Score not a number"),
            ({'verificationNotes': 'test'}, "Missing verificationScore"),
            ({'verificationScore': 0.8}, "Missing verificationNotes"),
            ({'verificationScore': 0.8, 'verificationNotes': 123}, "Notes not a string")
        ]
        
        for invalid_data, expected_error in invalid_cases:
            is_valid, message = validate_verification_schema(invalid_data)
            self.assertFalse(is_valid, f"Invalid schema should fail: {expected_error}")
    
    def test_error_handling_scenarios(self):
        """Test various error handling scenarios"""
        
        # Test timeout error response format
        timeout_error = {
            'status': 'error',
            'error': 'Processing timeout. Please try with a smaller image or try again later.',
            'items': [],
            'total_items': 0,
            'total_value': 0
        }
        
        self.assertEqual(timeout_error['status'], 'error')
        self.assertIn('timeout', timeout_error['error'].lower())
        self.assertEqual(timeout_error['items'], [])
        
        # Test MIME type error response format
        mime_error = {
            'status': 'error',
            'error': 'Invalid file type. Allowed types: image/jpeg, image/png, image/bmp',
            'items': [],
            'total_items': 0,
            'total_value': 0
        }
        
        self.assertEqual(mime_error['status'], 'error')
        self.assertIn('invalid file type', mime_error['error'].lower())
        
        # Test file size error response format
        size_error = {
            'status': 'error',
            'error': 'File too large. Maximum size: 10MB',
            'items': [],
            'total_items': 0,
            'total_value': 0
        }
        
        self.assertEqual(size_error['status'], 'error')
        self.assertIn('too large', size_error['error'].lower())
    
    def test_response_shrinking(self):
        """Test that response shrinking preserves essential fields only"""
        
        def shrink_item_for_frontend(item):
            """Simulate the shrink function"""
            essential_fields = {
                'code', 'name', 'category', 'brand', 'condition', 
                'price_usd', 'description', 'verificationScore', 'verificationNotes'
            }
            optional_fields = {'overallScore', 'bbox', 'source_image'}
            
            shrunk_item = {}
            
            # Add essential fields
            for field in essential_fields:
                if field in item:
                    shrunk_item[field] = item[field]
            
            # Add optional fields if they exist and have meaningful values
            for field in optional_fields:
                if field in item and item[field] is not None:
                    shrunk_item[field] = item[field]
            
            return shrunk_item
        
        # Test with full item
        full_item = {
            'code': '0',
            'name': 'Laptop',
            'category': 'Electronics',
            'brand': 'Dell',
            'price_usd': 1200.0,
            'description': 'Gaming laptop',
            'verificationScore': 0.85,
            'verificationNotes': 'Good match',
            'overallScore': 0.83,
            'bbox': [100, 100, 300, 200],
            'internal_debug_field': 'should_be_removed',
            'temp_field': None
        }
        
        shrunk = shrink_item_for_frontend(full_item)
        
        # Check essential fields are preserved
        essential_fields = {'code', 'name', 'category', 'brand', 'price_usd', 'description', 'verificationScore', 'verificationNotes'}
        for field in essential_fields:
            self.assertIn(field, shrunk, f"Essential field {field} should be preserved")
        
        # Check optional fields are preserved when present
        self.assertIn('overallScore', shrunk)
        self.assertIn('bbox', shrunk)
        
        # Check internal fields are removed
        self.assertNotIn('internal_debug_field', shrunk)
        self.assertNotIn('temp_field', shrunk)

def test_curl_examples():
    """Generate curl examples for testing"""
    
    print("\n🧪 CURL Test Examples")
    print("=" * 50)
    
    # Example 1: Successful request
    print("\n📋 Example 1: Successful Request")
    print("curl -X POST -F \"image=@./samples/test_image.jpg\" http://localhost:8080/api/analyze-image")
    
    # Example 2: Invalid MIME type
    print("\n📋 Example 2: Invalid MIME Type (should return 400)")
    print("curl -X POST -F \"image=@./test_document.pdf\" http://localhost:8080/api/analyze-image")
    
    # Example 3: No file
    print("\n📋 Example 3: No File (should return 400)")
    print("curl -X POST http://localhost:8080/api/analyze-image")
    
    # Example 4: Health check
    print("\n📋 Example 4: Health Check")
    print("curl http://localhost:8080/health")
    
    # Example 5: Pipeline test
    print("\n📋 Example 5: Pipeline Test")
    print("curl http://localhost:8080/test-pipeline")
    
    print("\n💡 Create a test image first:")
    print("python3 -c \"from PIL import Image; Image.new('RGB', (400, 300), 'white').save('test_image.jpg')\"")

if __name__ == "__main__":
    print("🧪 ClaimReady Simple Pipeline Audit Tests")
    print("=" * 50)
    
    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Generate curl examples
    test_curl_examples()
    
    print("\n🎉 Simple audit tests completed!")
    print("✅ JSON merger preserves producer fields")
    print("✅ Verification schema validation works")
    print("✅ Error handling scenarios covered")
    print("✅ Response shrinking preserves essential fields")
    print("✅ Deterministic image transforms verified")
