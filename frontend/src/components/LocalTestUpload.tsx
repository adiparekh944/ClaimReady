'use client';

import React, { useState } from 'react';
import { AnalysisResult } from '@/types/item';

// Minimal test component for local endpoint testing
export default function LocalTestUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && selectedFile.type.startsWith('image/')) {
      setFile(selectedFile);
      setError(null);
    } else {
      setError('Please select a valid image file');
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      // Exact fetch snippet for local testing
      const formData = new FormData();
      formData.append('image', file);

      const response = await fetch('http://127.0.0.1:8080/api/analyze-image', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to analyze image');
      }

      const analysisResult: AnalysisResult = await response.json();
      setResult(analysisResult);
      
      console.log('✅ Local API Response:', analysisResult);
      console.log('✅ Items with verification:', analysisResult.items.filter(item => item.verificationScore !== undefined));
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      console.error('❌ Upload error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Local API Test</h1>
      
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Upload Image to Local Backend</h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Image File
            </label>
            <input
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
          </div>
          
          <button
            onClick={handleUpload}
            disabled={!file || loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {loading ? 'Analyzing...' : 'Upload & Analyze'}
          </button>
          
          {error && (
            <div className="text-red-600 text-sm">{error}</div>
          )}
        </div>
      </div>

      {result && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-lg font-semibold mb-4">Analysis Results</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="text-sm text-blue-600">Total Items</div>
              <div className="text-2xl font-bold text-blue-800">{result.total_items}</div>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <div className="text-sm text-green-600">Total Value</div>
              <div className="text-2xl font-bold text-green-800">${result.total_value?.toFixed(2)}</div>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <div className="text-sm text-purple-600">With Verification</div>
              <div className="text-2xl font-bold text-purple-800">
                {result.items.filter(item => item.verificationScore !== undefined).length}
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="font-semibold">Items Found:</h3>
            {result.items.map((item, index) => (
              <div key={index} className="border rounded-lg p-4 bg-gray-50">
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-semibold">{item.name}</h4>
                  <span className="text-sm text-gray-600">${item.price_usd}</span>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">
                      <span className="font-medium">Category:</span> {item.category}
                    </p>
                    <p className="text-sm text-gray-600">
                      <span className="font-medium">Description:</span> {item.description}
                    </p>
                  </div>
                  
                  <div>
                    {item.verificationScore !== undefined ? (
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-sm">Verification Score:</span>
                          <span className="text-sm font-semibold">
                            {Math.round(item.verificationScore * 100)}%
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div 
                            className={`h-2 rounded-full transition-all duration-300 ${
                              item.verificationScore >= 0.8 ? 'bg-green-500' :
                              item.verificationScore >= 0.6 ? 'bg-yellow-500' :
                              item.verificationScore >= 0.4 ? 'bg-orange-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${item.verificationScore * 100}%` }}
                          ></div>
                        </div>
                        {item.verificationNotes && (
                          <p className="text-xs text-gray-600 mt-1" title={item.verificationNotes}>
                            {item.verificationNotes}
                          </p>
                        )}
                      </div>
                    ) : (
                      <p className="text-gray-500 text-sm">
                        <span className="font-medium">Verification Score:</span> —
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
