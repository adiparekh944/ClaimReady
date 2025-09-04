'use client';

import { useState } from 'react';

export default function TestPage() {
  const [testResult, setTestResult] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const testBackendConnection = async () => {
    setLoading(true);
    setTestResult('Testing...');
    
    try {
      const backendUrl = 'http://127.0.0.1:8080';
      console.log('🔗 Testing backend URL:', backendUrl);
      
      // Test 1: Health check
      const healthResponse = await fetch(`${backendUrl}/health`);
      console.log('🏥 Health check status:', healthResponse.status);
      
      if (healthResponse.ok) {
        setTestResult('✅ Backend is reachable\n');
        
        // Test 2: Try to upload a test image
        const testImageResponse = await fetch(`${backendUrl}/api/analyze-image`, {
          method: 'POST',
          body: new FormData(), // Empty form data to test endpoint
        });
        
        console.log('📤 Test image request status:', testImageResponse.status);
        
        if (testImageResponse.status === 400) {
          setTestResult(prev => prev + '✅ API endpoint responds correctly (400 expected for invalid request)\n');
        } else {
          setTestResult(prev => prev + `⚠️ API endpoint status: ${testImageResponse.status}\n`);
        }
        
        setTestResult(prev => prev + '🎉 Backend connection test completed successfully!');
      } else {
        setTestResult(`❌ Backend health check failed: ${healthResponse.status}`);
      }
    } catch (error) {
      console.error('❌ Test failed:', error);
      setTestResult(`❌ Connection test failed: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-lg p-6">
        <h1 className="text-2xl font-bold mb-4">Frontend-Backend Connection Test</h1>
        
        <button
          onClick={testBackendConnection}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Testing...' : 'Test Backend Connection'}
        </button>
        
        {testResult && (
          <div className="mt-4 p-4 bg-gray-100 rounded">
            <h2 className="font-semibold mb-2">Test Results:</h2>
            <pre className="whitespace-pre-wrap text-sm">{testResult}</pre>
          </div>
        )}
        
        <div className="mt-6 p-4 bg-yellow-100 rounded">
          <h3 className="font-semibold mb-2">Instructions:</h3>
          <ol className="list-decimal list-inside space-y-1 text-sm">
            <li>Click the &ldquo;Test Backend Connection&ldquo; button above</li>
            <li>Check the browser console for detailed logs</li>
            <li>If the test passes, try uploading an image on the main upload page</li>
            <li>Check the console logs to see the data flow</li>
          </ol>
        </div>
      </div>
    </div>
  );
} 