#!/usr/bin/env python3
"""
Test script for ClaimReady Analytics
Tests the analytics API endpoints
"""

import requests
import json
import time

def test_analytics_api():
    """Test the analytics API endpoints"""
    base_url = "http://localhost:8080"
    
    print("🧪 Testing ClaimReady Analytics API...")
    print(f"Backend URL: {base_url}")
    print("-" * 50)
    
    # Test health endpoint
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/api/analytics/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Health check passed: {data.get('message', 'OK')}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return False
    
    # Test metrics summary endpoint
    print("\n2. Testing metrics summary endpoint...")
    try:
        response = requests.get(f"{base_url}/api/analytics/metrics/summary", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                metrics = data.get('data', {})
                print(f"   ✅ Metrics summary retrieved:")
                print(f"      Total Items: {metrics.get('total_items', 0)}")
                print(f"      Total Value: ${metrics.get('total_value', 0):,.2f}")
                print(f"      Images Processed: {metrics.get('images_processed', 0)}")
                print(f"      Total Queries: {metrics.get('total_queries', 0)}")
                print(f"      Avg Items/Query: {metrics.get('avg_items_per_query', 0):.2f}")
                print(f"      Avg Value/Query: ${metrics.get('avg_value_per_query', 0):.2f}")
            else:
                print(f"   ❌ Metrics summary failed: {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"   ❌ Metrics summary failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Metrics summary error: {e}")
        return False
    
    # Test full metrics endpoint
    print("\n3. Testing full metrics endpoint...")
    try:
        response = requests.get(f"{base_url}/api/analytics/metrics", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                metrics = data.get('data', {})
                print(f"   ✅ Full metrics retrieved:")
                print(f"      Total Price: ${metrics.get('total_price', 0):,.2f}")
                print(f"      Total Images: {metrics.get('total_images', 0)}")
                print(f"      Total Items: {metrics.get('total_items', 0)}")
                print(f"      Total Queries: {metrics.get('total_queries', 0)}")
                print(f"      Avg Items/Query: {metrics.get('avg_items_per_query', 0):.2f}")
                print(f"      Avg Price/Query: ${metrics.get('avg_price_per_query', 0):.2f}")
                print(f"      Avg Price/Item: ${metrics.get('avg_price_per_item', 0):.2f}")
                print(f"      Last Updated: {metrics.get('last_updated', 'N/A')}")
            else:
                print(f"   ❌ Full metrics failed: {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"   ❌ Full metrics failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Full metrics error: {e}")
        return False
    
    print("\n🎉 All analytics tests passed!")
    return True

if __name__ == "__main__":
    print("ClaimReady Analytics Test Suite")
    print("=" * 50)
    
    if test_analytics_api():
        print("\n✅ Analytics system is working correctly!")
        print("\n📊 You can now:")
        print("   1. View analytics at http://localhost:3000/analytics")
        print("   2. Use the API endpoints in your frontend")
        print("   3. Monitor real-time metrics")
    else:
        print("\n❌ Analytics system has issues!")
        print("\n🔧 Troubleshooting:")
        print("   1. Make sure your backend is running on port 8080")
        print("   2. Check that the database schema is set up")
        print("   3. Verify the analytics blueprint is registered")
        print("   4. Check the backend logs for errors")
