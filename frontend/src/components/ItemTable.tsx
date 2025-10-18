'use client';

import React, { useState, useMemo, useEffect } from 'react';

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
  // New fields for SKU matching
  item_id?: number;
  bbox?: [number, number, number, number];
  crop_size?: [number, number];
  yolo_confidence?: number;
  best_match?: {
    sku_id?: string;
    product_name?: string;
    brand?: string;
    price_usd?: number;
    category?: string;
    confidence?: number;
  };
  price?: number;
  sku_confidence?: number;
  use_producer_2?: boolean;
  top_3_matches?: Array<{
    sku_id?: string;
    product_name?: string;
    brand?: string;
    price_usd?: number;
    category?: string;
    confidence?: number;
  }>;
}

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

  // Safe category display
  const getCategoryText = (c: any): string => {
    if (!c) return 'unknown';
    if (typeof c === 'string') return c;
    if (typeof c?.value === 'string') return c.value;
    try { return String(c); } catch { return 'unknown'; }
  };

  // Normalize incoming items (backend may send price vs price_usd, and categories as objects)
  const normalizedItems = useMemo(() => {
    return items.map((i: any) => {
      const resolvedCategory = typeof i?.category === 'string'
        ? i.category
        : (typeof i?.best_match?.category === 'string'
            ? i.best_match.category
            : (i?.best_match?.category?.value || 'unknown'));
      const resolvedPrice = i?.price ?? i?.price_usd ?? i?.best_match?.price_usd ?? 0;
      const resolvedName = i?.name || i?.best_match?.product_name || `Item ${i?.item_id || ''}`;
      const resolvedBrand = i?.brand || i?.best_match?.brand || '';
      return {
        ...i,
        name: resolvedName,
        brand: resolvedBrand,
        category: resolvedCategory,
        price_usd: resolvedPrice,
      } as Item;
    });
  }, [items]);

  // Get unique categories for filter dropdown (always strings)
  const categories = useMemo(() => {
    const source = tableItems.length ? tableItems : normalizedItems;
    const cats = [...new Set(source.map((item: any) => {
      const c = item?.category;
      return typeof c === 'string' ? c : (c?.value || 'unknown');
    }))];
    return ['all', ...cats];
  }, [tableItems, normalizedItems]);

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
    const source = tableItems.length ? tableItems : normalizedItems;
    console.log('Items for total calculation:', source);
    const total = source.reduce((sum: number, item: any) => {
      const raw = item?.price ?? item?.price_usd ?? item?.best_match?.price_usd;
      const price = typeof raw === 'string' ? parseFloat(raw) : (raw || 0);
      return sum + price;
    }, 0);
    console.log('Calculated total:', total);
    return total;
  }, [tableItems, normalizedItems]);

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
  const currentTotalValue = tableItems
    .filter(item => !item.nullify)
    .reduce((sum: number, item: any) => {
      const raw = item?.price ?? item?.price_usd ?? item?.best_match?.price_usd;
      const price = typeof raw === 'string' ? parseFloat(raw) : (raw || 0);
      return sum + price;
    }, 0);

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
                  {category === 'all' ? 'All Categories' : String(category).charAt(0).toUpperCase() + String(category).slice(1)}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Primary CRUD table temporarily removed for demo */}

      {/* Enhanced Detection Results Table */}
      <div className="mt-8 bg-white rounded-lg shadow-lg overflow-hidden">
        <div className="px-6 py-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 font-kumbh-sans">
            🔍 AI Detection Results ({tableItems.length} items)
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            YOLO object detection + CLIP visual embeddings + Amazon product matching
          </p>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Image
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Item Info
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  YOLO Score
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Best Match
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Price
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  SKU Score
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Top 3 Matches
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {tableItems.map((item, index) => {
                const segment = findSegmentForItem(item);
                return (
                  <tr key={index} className="hover:bg-gray-50">
                    {/* Image Column */}
                    <td className="px-4 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        {segment ? (
                          <img 
                            src={segment.image}
                            alt={`Item ${item.item_id || index + 1}`}
                            className="w-16 h-16 object-cover rounded-lg border-2 border-gray-200 shadow-sm cursor-zoom-in hover:opacity-90"
                            onClick={() => handleImageClick(segment.image)}
                          />
                        ) : (
                          <div className="w-16 h-16 bg-gradient-to-br from-gray-100 to-gray-200 rounded-lg flex items-center justify-center border-2 border-gray-200">
                            <span className="text-xs text-gray-500 font-medium">No Image</span>
                          </div>
                        )}
                      </div>
                    </td>
                    
                    {/* Item Info Column */}
                    <td className="px-4 py-4">
                      <div className="text-sm font-medium text-gray-900">
                        Item #{item.item_id || index + 1}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        Size: {item.crop_size ? `${item.crop_size[0]}×${item.crop_size[1]}px` : 'Unknown'}
                      </div>
                      <div className="text-xs text-gray-500">
                        BBox: {item.bbox ? `[${item.bbox[0].toFixed(0)}, ${item.bbox[1].toFixed(0)}, ${item.bbox[2].toFixed(0)}, ${item.bbox[3].toFixed(0)}]` : 'N/A'}
                      </div>
                    </td>
                    
                    {/* YOLO Confidence Column */}
                    <td className="px-4 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className={`w-4 h-4 rounded-full mr-2 ${
                          (item.yolo_confidence || 0) > 0.5 ? 'bg-green-400' : 
                          (item.yolo_confidence || 0) > 0.2 ? 'bg-yellow-400' : 'bg-red-400'
                        }`}></div>
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {((item.yolo_confidence || 0) * 100).toFixed(1)}%
                          </div>
                          <div className="text-xs text-gray-500">
                            {item.yolo_confidence && item.yolo_confidence > 0.5 ? 'High' : 
                             item.yolo_confidence && item.yolo_confidence > 0.2 ? 'Medium' : 'Low'}
                          </div>
                        </div>
                      </div>
                    </td>
                    
                    {/* Best Match Column */}
                    <td className="px-4 py-4">
                      <div className="max-w-xs">
                        <div className="text-sm font-medium text-gray-900 truncate">
                          {item.best_match?.product_name || 'No match found'}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {item.best_match?.brand || 'Unknown brand'}
                        </div>
                        <div className="text-xs text-gray-500">
                          {(() => {
                            const c: any = item.best_match?.category;
                            if (!c) return 'Unknown category';
                            return typeof c === 'string' ? c : (c?.value || 'Unknown category');
                          })()}
                        </div>
                      </div>
                    </td>
                    
                    {/* Price Column */}
                    <td className="px-4 py-4 whitespace-nowrap">
                      <div className="text-lg font-bold text-green-600">
                        ${(item.price || 0).toFixed(2)}
                      </div>
                      <div className="text-xs text-gray-500">
                        {item.best_match?.sku_id ? `SKU: ${item.best_match.sku_id}` : 'No SKU'}
                      </div>
                    </td>
                    
                    {/* SKU Confidence Column */}
                    <td className="px-4 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className={`w-4 h-4 rounded-full mr-2 ${
                          (item.sku_confidence || 0) > 0.7 ? 'bg-green-400' : 
                          (item.sku_confidence || 0) > 0.4 ? 'bg-yellow-400' : 'bg-red-400'
                        }`}></div>
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {((item.sku_confidence || 0) * 100).toFixed(1)}%
                          </div>
                          <div className="text-xs text-gray-500">
                            {item.sku_confidence && item.sku_confidence > 0.7 ? 'Excellent' : 
                             item.sku_confidence && item.sku_confidence > 0.4 ? 'Good' : 'Poor'}
                          </div>
                        </div>
                      </div>
                    </td>
                    
                    {/* Top 3 Matches Column */}
                    <td className="px-4 py-4">
                      <div className="space-y-2 max-w-sm">
                        {item.top_3_matches?.slice(0, 3).map((match, matchIndex) => (
                          <div key={matchIndex} className="bg-gray-50 rounded-lg p-2 border">
                            <div className="flex justify-between items-start">
                              <div className="flex-1 min-w-0">
                                <div className="text-xs font-medium text-gray-900 truncate">
                                  {matchIndex + 1}. {match.product_name || 'Unknown Product'}
                                </div>
                                <div className="text-xs text-gray-500 truncate">
                                  {match.brand || 'Unknown Brand'}
                                </div>
                              </div>
                              <div className="text-right ml-2">
                                <div className="text-xs font-bold text-green-600">
                                  ${(match.price_usd || 0).toFixed(2)}
                                </div>
                                <div className="text-xs text-gray-500">
                                  {((match.confidence || 0) * 100).toFixed(1)}%
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                        {(!item.top_3_matches || item.top_3_matches.length === 0) && (
                          <div className="text-xs text-gray-400 italic">
                            No matches found
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
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