'use client';

import React from 'react';
import AnalyticsDashboard from '@/components/AnalyticsDashboard';

export default function AnalyticsPage() {
  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">ClaimReady Analytics</h1>
          <p className="mt-2 text-gray-600">
            Real-time analytics for all queries processed by ClaimReady
          </p>
        </div>
        
        <AnalyticsDashboard />
        
        <div className="mt-8 bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">API Endpoints</h2>
          <div className="space-y-2 text-sm">
            <div className="flex items-center space-x-2">
              <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-mono">GET</span>
              <code className="text-gray-700">/api/analytics/metrics</code>
              <span className="text-gray-500">- Full metrics data</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-mono">GET</span>
              <code className="text-gray-700">/api/analytics/metrics/summary</code>
              <span className="text-gray-500">- Dashboard summary</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-mono">GET</span>
              <code className="text-gray-700">/api/analytics/health</code>
              <span className="text-gray-500">- Health check</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
