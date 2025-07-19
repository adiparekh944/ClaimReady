'use client';

import React, { useState, useMemo } from 'react';

interface Item {
  code: string;
  name: string;
  category: string;
  brand: string;
  condition: string;
  price_usd: number;
  description: string;
  nullify: boolean;
  source_image?: number;
}

interface Segment {
  index: number;
  original_box: [number, number, number, number];
  original_size: [number, number];
  normalized_size: [number, number];
  image: string; // base64 encoded image
}

interface ItemTableProps {
  items: Item[];
  totalValue?: number;
  totalItems?: number;
  imagesProcessed?: number;
  segments?: Segment[];
}

const ItemTable: React.FC<ItemTableProps> = ({ 
  items, 
  totalItems = 0, 
  imagesProcessed = 0,
  segments = []
}) => {
  const [sortField, setSortField] = useState<keyof Item>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');

  console.log('ItemTable items:', items);
  console.log('ItemTable segments:', segments);

  // Get unique categories for filter dropdown
  const categories = useMemo(() => {
    const cats = [...new Set(items.map(item => item.category))];
    return ['all', ...cats];
  }, [items]);

  // Filter and sort items
  const filteredAndSortedItems = useMemo(() => {
    let filtered = items.filter(item => !item.nullify);

    // Apply category filter
    if (filterCategory !== 'all') {
      filtered = filtered.filter(item => item.category === filterCategory);
    }

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(item =>
        item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.description.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Apply sorting
    filtered.sort((a, b) => {
      const aValue = a[sortField];
      const bValue = b[sortField];
      
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        const comparison = aValue.localeCompare(bValue);
        return sortDirection === 'asc' ? comparison : -comparison;
      }
      
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
      }
      
      return 0;
    });

    return filtered;
  }, [items, sortField, sortDirection, filterCategory, searchTerm]);

  const handleSort = (field: keyof Item) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const formatPrice = (price: number | string) => {
    let p = typeof price === 'string' ? parseFloat(price) : price;
    if (isNaN(p)) p = 0;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(p);
  };

  {/*const getConditionColor = (condition: string) => {
    switch (condition.toLowerCase()) {
      case 'new':
        return 'text-green-600 bg-green-100';
      case 'good':
        return 'text-blue-600 bg-green-100';
      case 'fair':
        return 'text-yellow-600 bg-yellow-100';
      case 'poor':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };*/}

  // Calculate total value from items
  const calculatedTotalValue = useMemo(() => {
    console.log('Items for total calculation:', items);
    const total = items.reduce((sum, item) => {
      const price = typeof item.price_usd === 'string' ? parseFloat(item.price_usd) : item.price_usd;
      console.log(`Item: ${item.name}, Price: ${item.price_usd}, Type: ${typeof item.price_usd}, Parsed: ${price}`);
      return sum + (price || 0);
    }, 0);
    console.log('Calculated total:', total);
    return total;
  }, [items]);

  // Function to find corresponding segment for an item
  const findSegmentForItem = (item: Item): Segment | undefined => {
    if (!segments.length) return undefined;
    return segments.find(segment => String(segment.index) === String(item.code));
  };

  // CSV Export Functionality
  const exportToCSV = () => {
    if (!filteredAndSortedItems.length) return;
    // Only include specific columns, excluding 'brand' and 'condition'
    const headers = Object.keys(filteredAndSortedItems[0]).filter(
      h => h !== 'brand' && h !== 'condition'
    );
    const csvRows = [headers.join(",")];
    for (const item of filteredAndSortedItems) {
      const row = headers.map(h => {
        let val = (item as any)[h];
        if (h === 'price_usd' && typeof val === 'number') {
          val = `$${val.toFixed(2)}`;
        } else if (typeof val === 'string') {
          val = '"' + val.replace(/"/g, '""') + '"';
        }
        return val;
      });
      csvRows.push(row.join(","));
    }
    const csvContent = csvRows.join("\n");
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'items.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full p-0 font-kumbh-sans">
      {/* Export Button  s*/}
      <div className="flex justify-end mb-4">
        <button
          onClick={exportToCSV}
          className="px-4 py-2 bg-gradient-to-r from-purple-500 to-purple-700 text-white rounded-md font-semibold shadow-lg hover:from-purple-600 hover:to-purple-800 transition-colors font-kumbh-sans"
        >
          Export to CSV
        </button>
      </div>
      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-500">Total Items</h3>
          <p className="text-2xl font-bold text-gray-900">{totalItems}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-500">Total Value</h3>
          <p className="text-2xl font-bold text-green-600">{formatPrice(calculatedTotalValue)}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-500">Images Processed</h3>
          <p className="text-2xl font-bold text-blue-600">{imagesProcessed}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-500">Items Found</h3>
          <p className="text-2xl font-bold text-purple-600">{filteredAndSortedItems.length}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-1">
              Search Items
            </label>
            <input
              type="text"
              id="search"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by name, description, or brand..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex-1">
            <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-1">
              Filter by Category
            </label>
            <select
              id="category"
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {categories.map(category => (
                <option key={category} value={category}>
                  {category === 'all' ? 'All Categories' : category.charAt(0).toUpperCase() + category.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden w-full">
        <div className="overflow-x-auto w-full">
          <table className="w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Image
                </th>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('name')}
                >
                  <div className="flex items-center">
                    Name
                    {sortField === 'name' && (
                      <span className="ml-1">
                        {sortDirection === 'asc' ? '↑' : '↓'}
                      </span>
                    )}
                  </div>
                </th>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('price_usd')}
                >
                  <div className="flex items-center">
                    Price
                    {sortField === 'price_usd' && (
                      <span className="ml-1">
                        {sortDirection === 'asc' ? '↑' : '↓'}
                      </span>
                    )}
                  </div>
                </th>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('category')}
                >
                  <div className="flex items-center">
                    Category
                    {sortField === 'category' && (
                      <span className="ml-1">
                        {sortDirection === 'asc' ? '↑' : '↓'}
                      </span>
                    )}
                  </div>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Description
                </th>
                {items.some(item => item.source_image !== undefined) && (
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Source Image
                  </th>
                )}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredAndSortedItems.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    No items found matching your criteria
                  </td>
                </tr>
              ) : (
                filteredAndSortedItems.map((item, index) => {
                  const segment = findSegmentForItem(item);
                  return (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        {segment ? (
                          <img 
                            src={segment.image}
                            alt={`Segment of ${item.name}`}
                            className="w-16 h-16 object-cover rounded border"
                          />
                        ) : (
                          <div className="w-16 h-16 bg-gray-200 rounded flex items-center justify-center">
                            <span className="text-xs text-gray-500">No image</span>
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{item.name}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-semibold text-green-600">
                          {formatPrice(item.price_usd)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900 capitalize">{item.category}</div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-900 max-w-xs truncate" title={item.description}>
                          {item.description}
                        </div>
                      </td>
                      {item.source_image !== undefined && (
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500">Image {item.source_image + 1}</div>
                        </td>
                      )}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ItemTable; 