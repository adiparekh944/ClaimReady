'use client';

import '@/app/globals.css';
import React, { useState, useMemo, useEffect } from 'react';
import { 
  FiSearch, FiFilter, FiEdit2, FiTrash2, FiPlus, 
  FiDownload, FiX, FiCheck, FiImage, FiBox, FiDollarSign, FiCamera 
} from 'react-icons/fi';

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
  analysisResults?: any;
}

// Helper to assign vibrant gradients based on the category name
const getCategoryGradient = (category: string) => {
  const cat = category?.toLowerCase().trim() || '';
  
  if (cat.includes('electronic') || cat.includes('tech') || cat.includes('computer')) {
    return 'bg-gradient-to-r from-blue-500 to-cyan-400 text-white shadow-blue-500/20';
  }
  if (cat.includes('furniture') || cat.includes('home')) {
    return 'bg-gradient-to-r from-orange-400 to-amber-500 text-white shadow-orange-500/20';
  }
  if (cat.includes('jewelry') || cat.includes('watch') || cat.includes('accessory')) {
    return 'bg-gradient-to-r from-purple-500 to-fuchsia-500 text-white shadow-purple-500/20';
  }
  if (cat.includes('appliance') || cat.includes('kitchen')) {
    return 'bg-gradient-to-r from-teal-400 to-emerald-500 text-white shadow-teal-500/20';
  }
  if (cat.includes('art') || cat.includes('decor')) {
    return 'bg-gradient-to-r from-rose-400 to-red-500 text-white shadow-rose-500/20';
  }
  if (cat.includes('clothing') || cat.includes('apparel')) {
    return 'bg-gradient-to-r from-indigo-400 to-blue-500 text-white shadow-indigo-500/20';
  }
  
  // Default Brand Blue Gradient for unrecognized categories
  return 'bg-gradient-to-r from-[rgb(21,89,249)] to-[rgb(87,168,255)] text-white shadow-blue-500/20';
};

const ItemTable: React.FC<ItemTableProps> = ({ 
  items, 
  totalItems = 0, 
  imagesProcessed = 0,
  segments = [],
}) => {
  const [sortField, setSortField] = useState<keyof Item>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');
  
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editItem, setEditItem] = useState<Partial<Item> | null>(null);
  const [tableItems, setTableItems] = useState<Item[]>([]);
  
  const [deleteIndex, setDeleteIndex] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);
  const [newItem, setNewItem] = useState<Partial<Item>>({ 
    name: '', price_usd: undefined, category: '', description: '', brand: '', condition: '', code: '', nullify: false 
  });
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  useEffect(() => {
    const processedItems = items?.map(item => ({
      ...item,
      nullify: typeof item.nullify === 'string' ? item.nullify === 'true' : item.nullify
    })) || [];
    setTableItems(processedItems);
  }, [items]);

  const categories = useMemo(() => {
    const cats = Array.from(new Set(
      tableItems
        .map(item => item.category?.trim().toLowerCase())
        .filter(Boolean)
    ));
    return ['all', ...cats];
  }, [tableItems]);

  const filteredAndSortedItems = useMemo(() => {
    let filtered = tableItems.filter(item => !item.nullify);

    if (filterCategory !== 'all') {
      const activeFilter = filterCategory.trim().toLowerCase();
      filtered = filtered.filter(item => item.category?.trim().toLowerCase() === activeFilter);
    }

    if (searchTerm) {
      const lowerSearch = searchTerm.trim().toLowerCase();
      filtered = filtered.filter(item =>
        item.name?.toLowerCase().includes(lowerSearch) ||
        item.description?.toLowerCase().includes(lowerSearch) ||
        item.brand?.toLowerCase().includes(lowerSearch)
      );
    }

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
  }, [tableItems, sortField, sortDirection, filterCategory, searchTerm]);

  const handleSort = (field: keyof Item) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const formatPrice = (price: number | string | undefined) => {
    let p = typeof price === 'string' ? parseFloat(price) : price;
    if (isNaN(p as number) || p === undefined) p = 0;
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(p);
  };

  const findSegmentForItem = (item: Item): Segment | undefined => {
    if (!segments.length || !item.code) return undefined;
    return segments.find(segment => String(segment.index) === String(item.code));
  };

  const exportToCSV = () => {
    if (!filteredAndSortedItems.length) return;
    const userHeaders = ['category', 'name', 'brand', 'description', 'price_usd'];
    if (filteredAndSortedItems.some(item => 'source_image' in item)) userHeaders.push('source_image');
    
    const csvRows = [userHeaders.join(",")];
    for (const item of filteredAndSortedItems) {
      const row = userHeaders.map(h => {
        const val = (item as any)[h];
        if (h === 'price_usd' && typeof val === 'number') return val.toFixed(2);
        if (typeof val === 'string') return '"' + val.replace(/"/g, '""') + '"';
        if (val === undefined || val === null) return '';
        return val;
      });
      csvRows.push(row.join(","));
    }
    
    const blob = new Blob([csvRows.join("\n")], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'claimready_inventory.csv';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // --- Fixed Handlers ---
  const handleEditClick = (index: number) => { 
    setEditingIndex(index); 
    setEditItem({ ...filteredAndSortedItems[index] }); 
  };
  
  const handleEditChange = (field: keyof Item, value: string | number) => {
    setEditItem(prev => prev ? { ...prev, [field]: value } : prev);
  };
  
  const handleEditSave = (index: number) => {
    if (editItem) {
      const itemToEdit = filteredAndSortedItems[index];
      const updated = [...tableItems];
      const realIndex = tableItems.findIndex(item => item === itemToEdit);
      
      if(realIndex !== -1) {
        updated[realIndex] = { ...updated[realIndex], ...editItem } as Item;
        setTableItems(updated); 
      }
      setEditingIndex(null); 
      setEditItem(null);
    }
  };
  
  const handleEditCancel = () => { 
    setEditingIndex(null); 
    setEditItem(null); 
  };
  
  const handleDeleteConfirm = () => {
    if (deleteIndex !== null) {
      const toDelete = filteredAndSortedItems[deleteIndex];
      setTableItems(prev => prev.map(item => item === toDelete ? { ...item, nullify: true } : item));
      setDeleteIndex(null);
    }
  };

  // MISSING ADD HANDLERS RE-ADDED HERE
  const handleAddChange = (field: keyof Item, value: string | number) => {
    if (field === 'price_usd') {
      const num = value === '' ? undefined : Number(value);
      setNewItem(prev => ({ ...prev, [field]: num }));
    } else {
      setNewItem(prev => ({ ...prev, [field]: value }));
    }
  };

  const handleAddSave = () => {
    if (newItem.name && newItem.price_usd !== undefined && newItem.category) {
      setTableItems(prev => [...prev, { ...newItem, price_usd: Number(newItem.price_usd), code: Math.random().toString(36).substr(2, 9) } as Item]);
      setAdding(false);
      setNewItem({ name: '', price_usd: undefined, category: '', description: '', brand: '', condition: '', code: '', nullify: false });
    }
  };

  const handleAddCancel = () => {
    setAdding(false);
    setNewItem({ name: '', price_usd: undefined, category: '', description: '', brand: '', condition: '', code: '', nullify: false });
  };

  // --- Derived Stats ---
  const currentTotalItems = tableItems.filter(item => !item.nullify).length;
  const currentTotalValue = tableItems.filter(item => !item.nullify).reduce((sum, item) => sum + (item.price_usd || 0), 0);

  // --- Reusable UI Sub-components ---
  const SortIcon = ({ field }: { field: keyof Item }) => {
    if (sortField !== field) return <span className="text-gray-300 ml-1 opacity-0 group-hover:opacity-100 transition-opacity">↕</span>;
    return <span className="text-[#0051ff] ml-1">{sortDirection === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6 font-geist-sans">
      
      {/* --- DASHBOARD HEADER --- */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-2">
        <div>
          <h2 className="text-4xl font-bold font-just-sans text-white tracking-tight">Inventory Assets</h2>
        </div>
        <div className="flex gap-3">
          <button
            onClick={exportToCSV}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-semibold shadow-sm hover:bg-gray-50 hover:text-gray-900 transition-all font-just-sans"
          >
            <FiDownload size={16} /> Export CSV
          </button>
          <button
            onClick={() => setAdding(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[rgb(21,89,249)] to-[rgb(87,168,255)] text-white rounded-lg text-sm font-semibold shadow-lg shadow-blue-500/30 hover:opacity-90 transition-all font-just-sans"
          >
            <FiPlus size={16} /> Add Asset
          </button>
        </div>
      </div>

      {/* --- STAT CARDS --- */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-just-sans">
        {[
          { label: 'Active Items', value: currentTotalItems, icon: <FiBox className="text-blue-500" size={30}/> },
          { label: 'Total Valuation', value: formatPrice(currentTotalValue), icon: <FiDollarSign className="text-emerald-500" size={20}/> },
          { label: 'Images Processed', value: imagesProcessed, icon: <FiCamera className="text-purple-500" size={30}/> },
          { label: 'Items Found', value: tableItems.length, icon: <FiSearch className="text-orange-500" size={30}/> },
        ].map((stat, i) => (
          <div key={i} className="bg-white rounded-xl border border-gray-100 p-5 shadow-[0_2px_10px_rgba(0,0,0,0.02)] flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">{stat.label}</p>
              <h3 className="text-2xl font-bold font-just-sans text-gray-900">{stat.value}</h3>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
              {stat.icon}
            </div>
          </div>
        ))}
      </div>

      {/* --- FILTER BAR --- */}
      <div className="bg-white rounded-xl border border-gray-100 p-2 shadow-[0_2px_10px_rgba(0,0,0,0.02)] flex flex-col md:flex-row gap-2">
        <div className="relative flex-1">
          <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search assets by name, brand, or description..."
            className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border-transparent rounded-lg text-sm focus:bg-white focus:border-[#0051ff] focus:ring-1 focus:ring-[#0051ff] transition-all outline-none font-just-sans" 
          />
        </div>
        <div className="relative w-full md:w-64 flex-shrink-0">
          <FiFilter className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="w-full pl-10 pr-8 py-2.5 bg-gray-50 border-transparent rounded-lg text-sm focus:bg-white focus:border-[#0051ff] focus:ring-1 focus:ring-[#0051ff] transition-all outline-none appearance-none cursor-pointer font-just-sans"
          >
            {categories.map(category => (
              <option key={category} value={category}>
                {category === 'all' ? 'All Categories' : category.charAt(0).toUpperCase() + category.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* --- DATA TABLE --- */}
      <div className="relative bg-white border border-gray-100 rounded-xl shadow-[0_4px_20px_rgba(0,0,0,0.03)] overflow-hidden">
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-gray-50/80 border-b border-gray-100 text-gray-500 uppercase tracking-wider text-[11px] font-semibold">
              <tr>
                <th className="px-6 py-4 w-12 text-center font-just-sans">#</th>
                <th className="px-6 py-4 w-20 font-just-sans">Asset</th>
                <th className="px-6 py-4 cursor-pointer hover:text-gray-900 group transition-colors font-just-sans" onClick={() => handleSort('name')}>
                  Name <SortIcon field="name" />
                </th>
                <th className="px-6 py-4 cursor-pointer hover:text-gray-900 group transition-colors font-just-sans" onClick={() => handleSort('price_usd')}>
                  Valuation <SortIcon field="price_usd" />
                </th>
                <th className="px-6 py-4 cursor-pointer hover:text-gray-900 group transition-colors font-just-sans" onClick={() => handleSort('category')}>
                  Category <SortIcon field="category" />
                </th>
                <th className="px-6 py-4 font-just-sans">Details</th>
                <th className="px-6 py-4 text-right font-just-sans">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              
              {/* Add Row Inline */}
              {adding && (
                <tr className="bg-blue-50/50">
                  <td className="px-6 py-4 text-center text-blue-400 font-bold" style={{ fontFamily: "var(--font-just-sans)" }}>+</td>
                  <td className="px-6 py-4"><div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center"><FiPlus className="text-blue-500"/></div></td>
                  <td className="px-6 py-4"><input autoFocus type="text" value={newItem.name} onChange={e => handleAddChange('name', e.target.value)} placeholder="Asset name" className="w-full px-3 py-1.5 border border-gray-200 rounded-md text-sm outline-none focus:border-[#0051ff]" /></td>
                  <td className="px-6 py-4"><input type="number" value={newItem.price_usd || ''} onChange={e => handleAddChange('price_usd', e.target.value)} placeholder="0.00" className="w-24 px-3 py-1.5 border border-gray-200 rounded-md text-sm outline-none focus:border-[#0051ff]" /></td>
                  <td className="px-6 py-4"><input type="text" value={newItem.category} onChange={e => handleAddChange('category', e.target.value)} placeholder="Category" className="w-32 px-3 py-1.5 border border-gray-200 rounded-md text-sm outline-none focus:border-[#0051ff]" /></td>
                  <td className="px-6 py-4"><input type="text" value={newItem.description} onChange={e => handleAddChange('description', e.target.value)} placeholder="Short description" className="w-full px-3 py-1.5 border border-gray-200 rounded-md text-sm outline-none focus:border-[#0051ff]" /></td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex justify-end gap-2">
                      <button onClick={handleAddSave} className="p-1.5 text-blue-600 hover:bg-blue-100 rounded-md transition-colors" title="Save"><FiCheck size={18}/></button>
                      <button onClick={handleAddCancel} className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors" title="Cancel"><FiX size={18}/></button>
                    </div>
                  </td>
                </tr>
              )}

              {filteredAndSortedItems.length === 0 && !adding ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center">
                    <div className="flex flex-col items-center justify-center text-gray-400">
                      <FiBox size={48} className="mb-4 opacity-20" />
                      <p className="text-base font-medium text-gray-600">No assets found</p>
                      <p className="text-sm">Try adjusting your filters or search term.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredAndSortedItems.map((item, index) => {
                  const segment = findSegmentForItem(item);
                  const isEditing = editingIndex === index;
                  
                  return (
                    <tr key={`row-${item.code || 'nocode'}-${index}`} className="hover:bg-gray-50/50 transition-colors group">
                      
                      {/* Number Column with font-just-sans */}
                      <td 
                        className="px-6 py-3 text-center text-gray-400 font-semibold text-[13px]" 
                        style={{ fontFamily: "var(--font-just-sans)" }}
                      >
                        {index + 1}
                      </td>

                      <td className="px-6 py-3">
                        {segment ? (
                          <div 
                            className="w-10 h-10 rounded-lg overflow-hidden border border-gray-200 cursor-pointer relative"
                            onClick={() => setSelectedImage(segment.image)}
                          >
                            <img src={segment.image} alt={item.name} className="w-full h-full object-cover" />
                            <div className="absolute inset-0 bg-black/0 hover:bg-black/10 transition-colors flex items-center justify-center opacity-0 hover:opacity-100">
                               <FiSearch className="text-white drop-shadow-md" size={14}/>
                            </div>
                          </div>
                        ) : (
                          <div className="w-10 h-10 bg-gray-100 border border-gray-200 rounded-lg flex items-center justify-center">
                            <FiImage className="text-gray-400" size={16} />
                          </div>
                        )}
                      </td>

                      <td className="px-6 py-3">
                        {isEditing ? (
                          <input type="text" value={editItem?.name || ''} onChange={e => handleEditChange('name', e.target.value)} className="w-full px-2 py-1 border border-gray-300 rounded focus:border-[#0051ff] outline-none font-just-sans" />
                        ) : (
                          <div className="font-just-sans text-gray-900">{item.name}</div>
                        )}
                      </td>

                      <td className="px-6 py-3">
                        {isEditing ? (
                          <input type="number" value={editItem?.price_usd || ''} onChange={e => handleEditChange('price_usd', parseFloat(e.target.value))} className="w-24 px-2 py-1 border border-gray-300 rounded focus:border-[#0051ff] outline-none font-just-sans"/>
                        ) : (
                          <div className="font-semibold text-gray-700 font-just-sans">{formatPrice(item.price_usd)}</div>
                        )}
                      </td>

                      <td className="px-6 py-3">
                        {isEditing ? (
                          <input type="text" value={editItem?.category || ''} onChange={e => handleEditChange('category', e.target.value)} className="w-full px-2 py-1 border border-gray-300 rounded focus:border-[#0051ff] outline-none font-just-sans" />
                        ) : (
                          <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold shadow-sm capitalize font-just-sans ${getCategoryGradient(item.category)}`} >
                            {item.category}
                          </span>
                        )}
                      </td>

                      <td className="px-6 py-3">
                        {isEditing ? (
                          <input type="text" value={editItem?.description || ''} onChange={e => handleEditChange('description', e.target.value)} className="w-full px-2 py-1 border border-gray-300 rounded focus:border-[#0051ff] outline-none" style={{ fontFamily: "var(--font-geist-sans)"}}/>
                        ) : (
                          <div className="text-gray-500 max-w-[200px] truncate" style={{ fontFamily: "var(--font-geist-sans)"}} title={item.description}>
                            {item.description || <span className="italic opacity-50" style={{ fontFamily: "var(--font-geist-sans)"}}>No description</span>}
                          </div>
                        )}
                      </td>

                      <td className="px-6 py-3 text-right">
                        {isEditing ? (
                          <div className="flex justify-end gap-1">
                            <button onClick={() => handleEditSave(index)} className="p-2 text-green-600 hover:bg-green-50 rounded-md transition-colors" title="Save Changes"><FiCheck size={16}/></button>
                            <button onClick={handleEditCancel} className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors" title="Cancel"><FiX size={16}/></button>
                          </div>
                        ) : (
                          <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button onClick={() => handleEditClick(index)} className="p-2 text-gray-400 hover:text-[#0051ff] hover:bg-blue-50 rounded-md transition-colors" title="Edit Asset"><FiEdit2 size={16}/></button>
                            <button onClick={() => setDeleteIndex(index)} className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors" title="Delete Asset"><FiTrash2 size={16}/></button>
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

      {/* --- DELETE CONFIRMATION MODAL --- */}
      {deleteIndex !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-sm w-full overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="p-6">
              <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center mb-4">
                <FiTrash2 className="text-red-600" size={24} />
              </div>
              <h2 className="text-lg font-bold text-gray-900 mb-2 font-just-sans">Delete Asset</h2>
              <p className="text-sm text-gray-500 mb-6">
                Are you sure you want to remove <strong>{filteredAndSortedItems[deleteIndex]?.name}</strong>? This will exclude it from your total valuation and exports.
              </p>
              <div className="flex gap-3">
                <button onClick={() => setDeleteIndex(null)} className="flex-1 px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-semibold hover:bg-gray-50 transition-colors">
                  Cancel
                </button>
                <button onClick={handleDeleteConfirm} className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-semibold hover:bg-red-700 shadow-sm transition-colors">
                  Delete Asset
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* --- IMAGE VIEWER MODAL --- */}
      {selectedImage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/80 backdrop-blur-md p-4" onClick={() => setSelectedImage(null)}>
          <div className="relative max-w-3xl max-h-[90vh] flex flex-col items-center animate-in fade-in zoom-in-95 duration-200" onClick={e => e.stopPropagation()}>
            <button onClick={() => setSelectedImage(null)} className="absolute -top-12 right-0 p-2 text-white/70 hover:text-white transition-colors">
              <FiX size={24} />
            </button>
            <img src={selectedImage} alt="Enlarged asset" className="w-auto max-w-full max-h-[85vh] object-contain rounded-lg shadow-2xl ring-1 ring-white/10" />
          </div>
        </div>
      )}
    </div>
  );
};

export default ItemTable;