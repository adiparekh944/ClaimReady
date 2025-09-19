import google.generativeai as genai
import base64
from PIL import Image
import io

# Test Gemini API key - hardcoded
GEMINI_API_KEY = "AIzaSyDIeU3XyxConIUZIKC0BqNaJ4tyIBwGIRg"

def test_gemini_key():
    """Test if the Gemini API key works"""
    try:
        # Configure Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash-lite')
        
        # Test with a simple text prompt
        print("Testing Gemini API key with text prompt...")
        response = model.generate_content("Hello! Please respond with 'API key is working' if you can see this message.")
        
        print("✅ Gemini API Key Test Results:")
        print(f"Response: {response.text}")
        print("✅ API key is working!")
        
        # Test with a simple image (create a small test image)
        print("\nTesting Gemini API key with image...")
        
        # Create a simple test image
        test_image = Image.new('RGB', (100, 100), color='red')
        
        # Test image analysis
        prompt = "What color is this image? Just respond with the color name."
        response = model.generate_content([prompt, test_image])
        
        print(f"Image analysis response: {response.text}")
        print("✅ Image analysis is working!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Gemini API key: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing Gemini API Key...")
    success = test_gemini_key()
    
    if success:
        print("\n🎉 All tests passed! The Gemini API key is working correctly.")
    else:
        print("\n💥 Tests failed! Please check the API key.") 