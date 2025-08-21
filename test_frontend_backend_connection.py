#!/usr/bin/env python3
"""
Test script to verify frontend-backend connection
"""
import requests
import json

def test_frontend_backend_connection():
    """Test if frontend can connect to backend"""
    
    # Test 1: Check if backend is reachable
    print("🔍 Testing backend connectivity...")
    try:
        health_response = requests.get('http://localhost:8080/health')
        if health_response.status_code == 200:
            print("✅ Backend is reachable")
        else:
            print(f"❌ Backend health check failed: {health_response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot reach backend: {e}")
        return
    
    # Test 2: Check if frontend is reachable
    print("\n🔍 Testing frontend connectivity...")
    try:
        frontend_response = requests.get('http://localhost:3000')
        if frontend_response.status_code == 200:
            print("✅ Frontend is reachable")
        else:
            print(f"❌ Frontend health check failed: {frontend_response.status_code}")
    except Exception as e:
        print(f"❌ Cannot reach frontend: {e}")
    
    # Test 3: Test CORS headers
    print("\n🔍 Testing CORS headers...")
    try:
        # Make a preflight request
        preflight_response = requests.options('http://localhost:8080/api/analyze-image')
        cors_headers = preflight_response.headers
        print(f"✅ CORS headers present: {dict(cors_headers)}")
    except Exception as e:
        print(f"❌ CORS test failed: {e}")
    
    # Test 4: Test actual API endpoint
    print("\n🔍 Testing API endpoint...")
    try:
        # Create a simple test request
        test_data = {'test': 'data'}
        api_response = requests.post('http://localhost:8080/api/analyze-image', 
                                   data=test_data, 
                                   headers={'Content-Type': 'application/x-www-form-urlencoded'})
        print(f"✅ API endpoint responds (status: {api_response.status_code})")
        if api_response.status_code != 200:
            print(f"Response: {api_response.text[:200]}...")
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")

if __name__ == "__main__":
    print("🧪 Testing frontend-backend connection...")
    test_frontend_backend_connection() 