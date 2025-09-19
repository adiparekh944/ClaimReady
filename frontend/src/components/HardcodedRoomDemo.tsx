'use client';

import React, { useState } from 'react';
import { isHardcodedRoom, getHardcodedResponse, calculateHardcodedTotalValue, getAvailableHardcodedRooms } from '@/lib/hardcodedRooms';

const HardcodedRoomDemo: React.FC = () => {
  const [selectedRoom, setSelectedRoom] = useState<string>('');
  const [result, setResult] = useState<any>(null);

  const availableRooms = getAvailableHardcodedRooms();

  const handleTestRoom = () => {
    if (!selectedRoom) return;
    
    const hardcodedResult = getHardcodedResponse(selectedRoom);
    if (hardcodedResult) {
      setResult(hardcodedResult);
    }
  };

  const handleTestFilename = (filename: string) => {
    const isHardcoded = isHardcodedRoom(filename);
    console.log(`Testing filename: ${filename} - Is hardcoded: ${isHardcoded}`);
  };

  return (
    <div className="p-6 bg-white rounded-lg shadow-lg max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-4 text-gray-800">🏠 Hardcoded Room System Demo</h2>
      
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-2">Test Hardcoded Rooms</h3>
        <div className="flex gap-2 mb-4">
          <select 
            value={selectedRoom} 
            onChange={(e) => setSelectedRoom(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value="">Select a room...</option>
            {availableRooms.map(room => (
              <option key={room} value={room}>{room}</option>
            ))}
          </select>
          <button 
            onClick={handleTestRoom}
            disabled={!selectedRoom}
            className="px-4 py-2 bg-blue-500 text-white rounded-md disabled:bg-gray-300"
          >
            Test Room
          </button>
        </div>
      </div>

      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-2">Test Filename Detection</h3>
        <div className="flex gap-2 flex-wrap">
          {availableRooms.map(room => (
            <button
              key={room}
              onClick={() => handleTestFilename(room)}
              className="px-3 py-1 bg-green-100 text-green-800 rounded-md hover:bg-green-200"
            >
              {room}
            </button>
          ))}
          <button
            onClick={() => handleTestFilename('normal_image.jpg')}
            className="px-3 py-1 bg-gray-100 text-gray-800 rounded-md hover:bg-gray-200"
          >
            normal_image.jpg
          </button>
        </div>
      </div>

      {result && (
        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <h3 className="text-lg font-semibold mb-2">Hardcoded Result</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p><strong>Room:</strong> {result.room}</p>
              <p><strong>Items:</strong> {result.items.length}</p>
              <p><strong>Total Value:</strong> ${calculateHardcodedTotalValue(result.items).toFixed(2)}</p>
              <p><strong>Hardcoded:</strong> {result.hardcoded ? 'Yes' : 'No'}</p>
            </div>
            <div>
              <h4 className="font-semibold mb-2">Sample Items:</h4>
              <ul className="text-sm space-y-1">
                {result.items.slice(0, 5).map((item: any, index: number) => (
                  <li key={index}>
                    {item.name} - ${item.price_usd} ({item.category})
                  </li>
                ))}
                {result.items.length > 5 && (
                  <li className="text-gray-500">... and {result.items.length - 5} more items</li>
                )}
              </ul>
            </div>
          </div>
        </div>
      )}

      <div className="mt-6 p-4 bg-blue-50 rounded-lg">
        <h3 className="text-lg font-semibold mb-2">How It Works</h3>
        <ul className="text-sm space-y-1 text-gray-700">
          <li>• Upload an image named <code className="bg-gray-200 px-1 rounded">sv-dorm.jpg</code>, <code className="bg-gray-200 px-1 rounded">room3.jpg</code>, or <code className="bg-gray-200 px-1 rounded">arnav-hotel.jpeg</code></li>
          <li>• The frontend detects the hardcoded filename</li>
          <li>• Returns predefined data instantly (no backend call)</li>
          <li>• Other filenames will call the backend ML pipeline</li>
        </ul>
      </div>
    </div>
  );
};

export default HardcodedRoomDemo;
