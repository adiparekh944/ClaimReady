'use client';

import React, { useState, useMemo, useEffect } from 'react';
import { Item } from '@/types/item';

interface Segment {
  index: string | number;
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
  analysisResults?: any; // Add this prop
}

const ItemTable: React.FC<ItemTableProps> = ({ 
  items, 
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  totalItems = 0, 
  imagesProcessed = 0,
  segments = [],
}) => {
  // 1. Add state for editing and deleting sdhjgfjghdsfx
  const [sortField, setSortField] = useState<keyof Item>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editItem, setEditItem] = useState<Partial<Item> | null>(null);
  const [tableItems, setTableItems] = useState<Item[]>(items);
  const [deleteIndex, setDeleteIndex] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);
  const [newItem, setNewItem] = useState<Partial<Item>>({ name: '', price_usd: undefined, category: '', description: '', brand: '', condition: '', code: '', nullify: false });
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  // Initialize tableItems when items prop changes
  useEffect(() => {
    console.log('🔄 ItemTable useEffect - items prop changed:', items);
    console.log('🔄 Items array length:', items?.length || 0);
    console.log('🔄 Items structure:', items?.map(item => ({
      code: item.code,
      name: item.name,
      category: item.category,
      brand: item.brand,
      condition: item.condition,
      price_usd: item.price_usd,
      nullify: item.nullify,
      nullifyType: typeof item.nullify,
      hasDescription: !!item.description
    })));
    
    // Check if nullify fields are strings and convert them to booleans
    const processedItems = items.map(item => ({
      ...item,
      nullify: typeof item.nullify === 'string' ? item.nullify === 'true' : item.nullify
    }));
    console.log('🔄 Processed items with converted nullify:', processedItems);
    setTableItems(processedItems);
  }, [items]);

  console.log('ItemTable items:', items);
  console.log('ItemTable items structure:', items.map(item => ({
    code: item.code,
    name: item.name,
    category: item.category,
    brand: item.brand,
    condition: item.condition,
    price_usd: item.price_usd,
    nullify: item.nullify,
    hasDescription: !!item.description
  })));
  console.log('ItemTable segments:', segments);
  console.log('ItemTable tableItems state:', tableItems);

  // Get unique categories for filter dropdown
  const categories = useMemo(() => {
    const cats = [...new Set(tableItems.map(item => item.category))];
    return ['all', ...cats];
  }, [tableItems]);

  // Filter and sort items
  const filteredAndSortedItems = useMemo(() => {
    console.log('🔍 Filtering tableItems:', tableItems);
    console.log('🔍 TableItems length:', tableItems.length);
    console.log('🔍 Nullify field types:', tableItems.map(item => ({ code: item.code, nullify: item.nullify, nullifyType: typeof item.nullify })));
    console.log('🔍 Items with nullify true:', tableItems.filter(item => item.nullify));
    console.log('🔍 Items with nullify false:', tableItems.filter(item => !item.nullify));
    let filtered = tableItems.filter(item => !item.nullify);
    console.log('🔍 After nullify filtering:', filtered.length, 'items');

    // Apply category filter
    if (filterCategory !== 'all') {
      filtered = filtered.filter(item => item.category === filterCategory);
      console.log('🔍 After category filtering:', filtered.length, 'items');
    }

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(item =>
        item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.description.toLowerCase().includes(searchTerm.toLowerCase())
      );
      console.log('🔍 After search filtering:', filtered.length, 'items');
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

    console.log('🔍 Final filteredAndSortedItems:', filtered);
    return filtered;
  }, [tableItems, sortField, sortDirection, filterCategory, searchTerm]);

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
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
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
    
    // Safety check for item.code
    if (!item.code) return undefined;
    
    // Direct match by code - segments use the actual code as index
    const found = segments.find(segment => segment.index === item.code);
    return found;
  };

  // CSV Export Functionality
  const exportToCSV = () => {
    if (!filteredAndSortedItems.length) return;
    // Only include user-facing columns in the specified order
    const userHeaders = [
      'category',
      'name',
      'description',
      'price_usd',
    ];
    // Optionally include source_image if present
    if (filteredAndSortedItems.some(item => 'source_image' in item)) {
      userHeaders.push('source_image');
    }
    const csvRows = [userHeaders.join(",")];
    for (const item of filteredAndSortedItems) {
      const row = userHeaders.map(h => {
        const val = (item as any)[h];
        if (h === 'price_usd' && typeof val === 'number') {
          // Output as plain number (no $ sign)
          return val.toFixed(2);
        } else if (typeof val === 'string') {
          return '"' + val.replace(/"/g, '""') + '"';
        } else if (val === undefined || val === null) {
          return '';
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

  // 3. Edit handlers
  const handleEditClick = (index: number) => {
    setEditingIndex(index);
    setEditItem({ ...filteredAndSortedItems[index] });
  };
  const handleEditChange = (field: keyof Item, value: string | number) => {
    setEditItem(prev => prev ? { ...prev, [field]: value } : prev);
  };
  const handleEditSave = (index: number) => {
    if (editItem) {
      const updated = [...tableItems];
      const filteredIndex = tableItems.findIndex(item => item.code === filteredAndSortedItems[index].code);
      updated[filteredIndex] = { ...updated[filteredIndex], ...editItem } as Item;
      setTableItems(updated);
      setEditingIndex(null);
      setEditItem(null);
    }
  };
  const handleEditCancel = () => {
    setEditingIndex(null);
    setEditItem(null);
  };

  // 4. Delete handlers
  const handleDeleteClick = (index: number) => {
    console.log('Delete clicked for index:', index);
    setDeleteIndex(index);
  };
  const handleDeleteConfirm = () => {
    if (deleteIndex !== null) {
      const toDelete = filteredAndSortedItems[deleteIndex];
      console.log('Deleting item:', toDelete);
      // Mark the item as nullified instead of removing it completely
      setTableItems(prev => {
        const updated = prev.map(item => 
          item.code === toDelete.code ? { ...item, nullify: true } : item
        );
        console.log('Updated tableItems after delete:', updated);
        return updated;
      });
      setDeleteIndex(null);
    }
  };
  const handleDeleteCancel = () => setDeleteIndex(null);

  const handleAddClick = () => {
    setAdding(true);
    setNewItem({ name: '', price_usd: undefined, category: '', description: '', brand: '', condition: '', code: Math.random().toString(36).substr(2, 9), nullify: false });
  };
  const handleAddChange = (field: keyof Item, value: string | number) => {
    if (field === 'price_usd') {
      const num = value === '' ? undefined : Number(value);
      setNewItem(prev => ({ ...prev, [field]: num }));
    } else {
      setNewItem(prev => ({ ...prev, [field]: value }));
    }
  };
  const handleAddSave = () => {
    if (newItem.name && newItem.price_usd !== undefined && newItem.category && newItem.description) {
      setTableItems(prev => [...prev, { ...newItem, price_usd: Number(newItem.price_usd) } as Item]);
      setAdding(false);
      setNewItem({ name: '', price_usd: undefined, category: '', description: '', brand: '', condition: '', code: '', nullify: false });
    }
  };
  const handleAddCancel = () => {
    setAdding(false);
    setNewItem({ name: '', price_usd: undefined, category: '', description: '', brand: '', condition: '', code: '', nullify: false });
  };

  const handleImageClick = (imageSrc: string) => {
    setSelectedImage(imageSrc);
  };

  const handleCloseImage = () => {
    setSelectedImage(null);
  };

  // Calculate current total items after filtering
  const currentTotalItems = tableItems.filter(item => !item.nullify).length;
  // Calculate current total value after filtering
  const currentTotalValue = tableItems.filter(item => !item.nullify).reduce((sum, item) => sum + (item.price_usd || 0), 0);

  // Debug logging for table rendering
  console.log('🎯 ItemTable render debug:');
  console.log('  - items prop length:', items.length);
  console.log('  - tableItems length:', tableItems.length);
  console.log('  - filteredAndSortedItems length:', filteredAndSortedItems.length);
  console.log('  - segments length:', segments.length);
  console.log('  - currentTotalItems:', currentTotalItems);
  console.log('  - currentTotalValue:', currentTotalValue);

  return (
    <div className="w-full p-0 font-kumbh-sans">
      {/* Export Button  s*/}
      <div className="flex justify-between mb-4">
        <button
          onClick={handleAddClick}
          className="px-4 py-2 bg-gradient-to-r from-green-500 to-green-700 text-white rounded-md font-semibold shadow-lg hover:from-green-600 hover:to-green-800 transition-colors font-kumbh-sans"
        >
          Add Item
        </button>


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
          <p className="text-2xl font-bold text-gray-900">{currentTotalItems}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-500">Total Value</h3>
          <p className="text-2xl font-bold text-green-600">{formatPrice(currentTotalValue)}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-medium text-gray-500">Images Processed</h3>
          <p className="text-2xl font-bold text-blue-600">{imagesProcessed}</p>
        </div>
                        <div className="bg-white rounded-lg shadow p-4">
                  <h3 className="text-sm font-medium text-gray-500">Items Found</h3>
                  <p className="text-2xl font-bold text-purple-600">{tableItems.length}</p>
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
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Verification Score
                </th>
                {tableItems.some(item => item.source_image !== undefined) && (
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Source Image
                  </th>
                )}
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {adding && (
                <tr className="bg-green-50">
                  <td className="px-6 py-4 whitespace-nowrap"></td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <input
                      type="text"
                      value={newItem.name}
                      onChange={e => handleAddChange('name', e.target.value)}
                      className="w-full px-2 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-green-500"
                      placeholder="Name"
                    />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <input
                      type="number"
                      value={newItem.price_usd === undefined ? '' : newItem.price_usd}
                      onChange={e => handleAddChange('price_usd', e.target.value)}
                      className="w-full px-2 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-green-500"
                      placeholder="Price"
                    />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <input
                      type="text"
                      value={newItem.category}
                      onChange={e => handleAddChange('category', e.target.value)}
                      className="w-full px-2 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-green-500"
                      placeholder="Category"
                    />
                  </td>
                  <td className="px-6 py-4">
                    <textarea
                      value={newItem.description}
                      onChange={e => handleAddChange('description', e.target.value)}
                      className="w-full px-2 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-green-500"
                      placeholder="Description"
                    />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-400">—</div>
                  </td>
                  {tableItems.some(item => item.source_image !== undefined) && <td className="px-6 py-4 whitespace-nowrap"></td>}
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex gap-2">
                      <button
                        className="px-3 py-1 rounded bg-gradient-to-r from-green-500 to-green-700 text-white font-semibold shadow hover:from-green-600 hover:to-green-800 transition-colors"
                        onClick={handleAddSave}
                      >Save</button>
                      <button
                        className="px-3 py-1 rounded bg-gray-300 text-gray-700 font-semibold hover:bg-gray-400 transition-colors"
                        onClick={handleAddCancel}
                      >Cancel</button>
                    </div>
                  </td>
                </tr>
              )}
              {filteredAndSortedItems.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-4 text-center text-gray-500">
                    No items found matching your criteria
                  </td>
                </tr>
              ) : (
                filteredAndSortedItems.map((item, index) => {
                  const segment = findSegmentForItem(item);
                  const isEditing = editingIndex === index;
                  return (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        {segment ? (
                          <img 
                            src={segment.image}
                            alt={`Segment of ${item.name}`}
                            className="w-16 h-16 object-cover rounded border cursor-pointer hover:opacity-80 transition-opacity"
                            onClick={() => handleImageClick(segment.image)}
                          />
                        ) : (
                          <div className="w-16 h-16 bg-gray-200 rounded flex items-center justify-center">
                            <span className="text-xs text-gray-500">No image</span>
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {isEditing ? (
                          <input
                            type="text"
                            value={editItem?.name || ''}
                            onChange={(e) => handleEditChange('name', e.target.value)}
                            className="w-full px-2 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                        ) : (
                          <div className="text-sm font-medium text-gray-900">{item.name}</div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {isEditing ? (
                          <input
                            type="text"
                            value={editItem?.price_usd || ''}
                            onChange={(e) => handleEditChange('price_usd', parseFloat(e.target.value))}
                            className="w-full px-2 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                        ) : (
                          <div className="text-sm font-semibold text-green-600">
                            {formatPrice(item.price_usd)}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {isEditing ? (
                          <input
                            type="text"
                            value={editItem?.category || ''}
                            onChange={(e) => handleEditChange('category', e.target.value)}
                            className="w-full px-2 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                        ) : (
                          <div className="text-sm text-gray-900 capitalize">{item.category}</div>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {isEditing ? (
                          <textarea
                            value={editItem?.description || ''}
                            onChange={(e) => handleEditChange('description', e.target.value)}
                            className="w-full px-2 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                        ) : (
                          <div className="text-sm text-gray-900 max-w-xs truncate" title={item.description}>
                            {item.description}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {item.verificationScore !== undefined ? (
                          <div className="flex items-center space-x-2">
                            <div className="flex-1">
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
                              <div className="text-xs text-gray-600 mt-1">
                                {Math.round(item.verificationScore * 100)}%
                              </div>
                            </div>
                            {item.verificationNotes && (
                              <div 
                                className="text-gray-400 cursor-help"
                                title={item.verificationNotes}
                              >
                                ℹ️
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="text-sm text-gray-400">—</div>
                        )}
                      </td>
                      {item.source_image !== undefined && (
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500">Image {item.source_image + 1}</div>
                        </td>
                      )}
                      <td className="px-6 py-4 whitespace-nowrap">
                        {isEditing ? (
                          <div className="flex gap-2">
                            <button
                              className="px-3 py-1 rounded bg-gradient-to-r from-blue-500 to-blue-700 text-white font-semibold shadow hover:from-blue-600 hover:to-blue-800 transition-colors"
                              onClick={() => handleEditSave(index)}
                            >Save</button>
                            <button
                              className="px-3 py-1 rounded bg-gray-300 text-gray-700 font-semibold hover:bg-gray-400 transition-colors"
                              onClick={handleEditCancel}
                            >Cancel</button>
                          </div>
                        ) : (
                          <div className="flex gap-2">
                            <button
                              className="px-3 py-1 rounded bg-gradient-to-r from-blue-500 to-blue-700 text-white font-semibold shadow hover:from-blue-600 hover:to-blue-800 transition-colors"
                              onClick={() => handleEditClick(index)}
                            >Edit</button>
                            <button
                              className="px-3 py-1 rounded bg-gradient-to-r from-red-500 to-red-700 text-white font-semibold shadow hover:from-red-600 hover:to-red-800 transition-colors"
                              onClick={() => handleDeleteClick(index)}
                            >Delete</button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
      {/* Confirmation Dialog */}
      {deleteIndex !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-lg p-8 max-w-sm w-full">
            <h2 className="text-xl font-bold mb-4 font-kumbh-sans">Confirm Delete</h2>
            <p className="mb-6 text-gray-700">Are you sure you want to delete this item?</p>
            <div className="flex justify-end gap-4">
              <button
                className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 font-kumbh-sans"
                onClick={handleDeleteCancel}
              >Cancel</button>
              <button
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 font-kumbh-sans"
                onClick={handleDeleteConfirm}
              >Delete</button>
            </div>
          </div>
        </div>
      )}
      {/* Image Modal */}
      {selectedImage && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={handleCloseImage}
        >
          <div 
            className="relative w-96 h-96"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={handleCloseImage}
              className="absolute -top-2 -right-2 w-8 h-8 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition-colors z-10 text-lg font-bold"
            >
              ×
            </button>
            <img 
              src={selectedImage} 
              alt="Enlarged item" 
              className="w-full h-full object-contain rounded-lg shadow-2xl"
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default ItemTable; 