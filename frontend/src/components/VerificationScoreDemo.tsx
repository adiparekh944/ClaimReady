'use client';

import React from 'react';
import { LegacyItem } from '@/types/item';

// Demo component to show how verification scores will be displayed
export default function VerificationScoreDemo() {
  const sampleItems: LegacyItem[] = [
    {
      estimated_name: "Wooden Chair",
      estimated_price: 250,
      best_confidence: 0.95,
      class: "Furniture",
      verificationScore: 0.92,
      verificationNotes: "Excellent visual match with clear wood grain and chair structure visible"
    },
    {
      estimated_name: "Laptop",
      estimated_price: 1200,
      best_confidence: 0.87,
      class: "Electronics",
      verificationScore: 0.75,
      verificationNotes: "Good match but screen is partially obscured"
    },
    {
      estimated_name: "Coffee Table",
      estimated_price: 400,
      best_confidence: 0.78,
      class: "Furniture",
      verificationScore: 0.45,
      verificationNotes: "Poor image quality makes verification difficult"
    },
    {
      estimated_name: "Old Item",
      estimated_price: 100,
      best_confidence: 0.65,
      class: "Unknown",
      // No verification score - should show fallback
    }
  ];

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <h1 className="text-3xl font-bold mb-6 text-center">Verification Score Demo</h1>
      
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Sample Items with Verification Scores</h2>
          
          <div className="space-y-4">
            {sampleItems.map((item, index) => (
              <div key={index} className="border rounded-lg p-4 bg-gray-50">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-semibold text-lg">{item.estimated_name}</h3>
                  <span className="text-sm text-gray-600">${item.estimated_price}</span>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">
                      <span className="font-medium">Confidence:</span> {Math.round((item.best_confidence || 0) * 100)}%
                    </p>
                    <p className="text-sm text-gray-600">
                      <span className="font-medium">Type:</span> {item.class}
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
        
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="font-semibold text-blue-800 mb-2">Color Coding Guide</h3>
          <div className="space-y-2 text-sm">
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-green-500 rounded"></div>
              <span>80-100%: Excellent match, high confidence</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-yellow-500 rounded"></div>
              <span>60-79%: Good match, some uncertainty</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-orange-500 rounded"></div>
              <span>40-59%: Moderate match, significant uncertainty</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-red-500 rounded"></div>
              <span>0-39%: Poor match, low confidence</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
