'use client';

import { useState } from 'react';
import { API_ENDPOINTS } from '@/lib/config';

export default function DebugPage() {
  const [debugInfo, setDebugInfo] = useState<string>('');

  const runDebug = async () => {
    setDebugInfo('Running debug...\n');
    
    // Check environment variables
    setDebugInfo(prev => prev + `🔗 Backend URL: ${API_ENDPOINTS.HEALTH}\n`);
    
    try {
      // Test backend connection
      const response = await fetch(API_ENDPOINTS.HEALTH);
      setDebugInfo(prev => prev + `🏥 Backend health check: ${response.status}\n`);
      
      if (response.ok) {
        setDebugInfo(prev => prev + '✅ Backend is reachable\n');
        
        // Test with a real image
        const formData = new FormData();
        // Create a simple test image (1x1 pixel)
        const canvas = document.createElement('canvas');
        canvas.width = 1;
        canvas.height = 1;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.fillStyle = 'red';
          ctx.fillRect(0, 0, 1, 1);
          canvas.toBlob(async (blob) => {
            if (blob) {
              formData.append('image', blob, 'test.jpg');
              
              try {
                const imageResponse = await fetch(API_ENDPOINTS.ANALYZE_IMAGE, {
                  method: 'POST',
                  body: formData,
                });
                
                setDebugInfo(prev => prev + `📤 Image analysis request: ${imageResponse.status}\n`);
                
                if (imageResponse.ok) {
                  const result = await imageResponse.json();
                  setDebugInfo(prev => prev + `📥 Response received with ${result.items?.length || 0} items\n`);
                  setDebugInfo(prev => prev + `📥 Items: ${JSON.stringify(result.items?.slice(0, 2), null, 2)}\n`);
                } else {
                  const errorText = await imageResponse.text();
                  setDebugInfo(prev => prev + `❌ Error: ${errorText}\n`);
                }
              } catch (error) {
                setDebugInfo(prev => prev + `❌ Request failed: ${error}\n`);
              }
            }
          });
        }
      } else {
        setDebugInfo(prev => prev + '❌ Backend is not reachable\n');
      }
    } catch (error) {
      setDebugInfo(prev => prev + `❌ Connection failed: ${error}\n`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-lg p-6">
        <h1 className="text-2xl font-bold mb-4">Frontend Debug Page</h1>
        
        <button
          onClick={runDebug}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Run Debug Test
        </button>
        
        {debugInfo && (
          <div className="mt-4 p-4 bg-gray-100 rounded">
            <h2 className="font-semibold mb-2">Debug Output:</h2>
            <pre className="whitespace-pre-wrap text-sm overflow-auto max-h-96">{debugInfo}</pre>
          </div>
        )}
        
        <div className="mt-6 p-4 bg-yellow-100 rounded">
          <h3 className="font-semibold mb-2">Instructions:</h3>
          <ol className="list-decimal list-inside space-y-1 text-sm">
            <li>Click &ldquo;Run Debug Test&ldquo; to check the backend connection</li>
            <li>Check the browser console for additional logs</li>
            <li>If the test passes, try uploading an image on the upload page</li>
            <li>Look for any error messages in the debug output</li>
          </ol>
        </div>
      </div>
    </div>
  );
} 