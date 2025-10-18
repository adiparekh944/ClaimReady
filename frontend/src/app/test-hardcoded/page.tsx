'use client';

import React from 'react';
import Navbar from '@/components/Navbar';
import HardcodedRoomDemo from '@/components/HardcodedRoomDemo';

export default function TestHardcodedPage() {
  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-3xl font-bold text-center mb-8 text-gray-800">
            Hardcoded Room System Test
          </h1>
          <HardcodedRoomDemo />
        </div>
      </div>
    </div>
  );
}
