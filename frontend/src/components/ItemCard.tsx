'use client';

import { motion } from 'framer-motion';
import { useState } from 'react';

interface ItemCardProps {
  itemKey: string;
  item: any;
  index: number;
  onEdit?: (key: string, field: string, value: any) => void;
  onRemove?: (key: string) => void;
}

export default function ItemCard({ itemKey, item, index, onEdit, onRemove }: ItemCardProps) {
  const [editingName, setEditingName] = useState(false);
  const [editingPrice, setEditingPrice] = useState(false);
  const [name, setName] = useState(item.estimated_name || '');
  const [price, setPrice] = useState(item.estimated_price || '');

  const handleNameBlur = () => {
    setEditingName(false);
    if (onEdit) onEdit(itemKey, 'estimated_name', name);
  };
  const handlePriceBlur = () => {
    setEditingPrice(false);
    if (onEdit) onEdit(itemKey, 'estimated_price', Number(price));
  };

  return (
    <motion.div 
      key={itemKey}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
      className="bg-white rounded-lg shadow-md overflow-hidden relative w-full max-w-md mx-auto mb-4 sm:mb-0"
    >
      <div className="h-40 sm:h-48 overflow-hidden bg-gray-100">
        {item.public_url && (
          <img 
            src={item.public_url}
            alt={item.estimated_name || 'Unknown item'}
            className="w-full h-full object-cover"
          />
        )}
      </div>
      <div className="p-3 sm:p-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-2 gap-2">
          {editingName ? (
            <input
              className="text-base sm:text-lg font-semibold border-b border-gray-300 focus:outline-none focus:border-[var(--color-primary)] bg-transparent break-words w-full max-w-xs"
              value={name}
              onChange={e => setName(e.target.value)}
              onBlur={handleNameBlur}
              autoFocus
            />
          ) : (
            <h3
              className="text-base sm:text-lg font-semibold cursor-pointer break-words w-full max-w-xs"
              onClick={() => setEditingName(true)}
              title="Click to edit name"
            >
              {name || 'Unknown Item'}
            </h3>
          )}
          {onRemove && (
            <button
              className="ml-0 sm:ml-2 text-red-500 hover:text-red-700 font-bold text-lg"
              title="Remove item"
              onClick={() => onRemove(itemKey)}
            >
              ×
            </button>
          )}
        </div>
        <div className="space-y-2">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-1 sm:gap-2">
            <span className="font-medium mr-0 sm:mr-2">Estimated Price:</span>
            {editingPrice ? (
              <input
                type="number"
                className="border-b border-gray-300 focus:outline-none focus:border-[var(--color-primary)] bg-transparent w-20 sm:w-24"
                value={price}
                onChange={e => setPrice(e.target.value)}
                onBlur={handlePriceBlur}
                autoFocus
              />
            ) : (
              <span
                className="cursor-pointer"
                onClick={() => setEditingPrice(true)}
                title="Click to edit price"
              >
                ${price?.toLocaleString() || 'N/A'}
              </span>
            )}
          </div>
          <p className="text-gray-700 text-sm sm:text-base">
            <span className="font-medium">Confidence:</span> {Math.round((item.best_confidence || 0) * 100)}%
          </p>
          <p className="text-gray-700 text-sm sm:text-base">
            <span className="font-medium">Type:</span> {item.class}
          </p>
        </div>
      </div>
    </motion.div>
  );
}