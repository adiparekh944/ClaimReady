'use client';
import React, { useState, useEffect, useRef } from "react";
import Navbar from "@/components/Navbar";
import '@/app/globals.css';
import Grainient from "@/components/Grainient";
import { HiSparkles } from "react-icons/hi2";
import Link from "next/link";

// ── IMPORT: MagicUI Shine Border ──
import { ShineBorder } from "@/components/magicui/shine-border";

// ── ICONS ──
import {
  FiCommand, FiSquare, FiPieChart, FiSend, FiChevronRight,
  FiLock, FiMail, FiInstagram, FiLinkedin, FiAlertTriangle,
  FiTarget, FiHome, FiFileText, FiTool, FiImage, FiEdit2, FiTrash2,
  FiBox, FiDownload, FiPlus, FiCheck, FiX
} from "react-icons/fi";
import { HiOutlineChartBar, HiOutlineSwitchHorizontal } from "react-icons/hi";
import { RiSparklingLine } from "react-icons/ri";
import { TbActivity, TbExchange } from "react-icons/tb";

// --- Beta Badge Component ---
const BetaBadge = () => {
  return (
    <div className="beta-badge-wrapper">
      <div className="beta-badge">
        <span className="beta-dot" />
        <span className="beta-text font-geist-sans">ClaimReady is in beta development</span>
      </div>
      <style dangerouslySetInnerHTML={{ __html: `
        .beta-badge-wrapper { display: inline-flex; justify-content: center; }
        .beta-badge {
          display: inline-flex; align-items: center; gap: 8px;
          padding: 0.45em 1.1em; background-color: #ffffff;
          border-radius: 999px; border: solid 1px rgba(0,0,0,0.1);
          font-family: var(--font-geist-sans);
          font-size: 0.85em; font-weight: 500; color: rgba(0,0,0,0.75);
          position: relative;
          box-shadow:
            inset 0px 1px 1px rgba(255,255,255,0.8),
            inset 0px 2px 2px rgba(255,255,255,0.6),
            0px 0px 8px rgba(255,255,255,0.25),
            0px 0px 20px rgba(255,255,255,0.15),
            0px 0px 40px rgba(255,255,255,0.08);
        }
        .beta-badge::before {
          content: ""; position: absolute; top: -4px; left: -4px;
          width: calc(100% + 8px); height: calc(100% + 8px);
          border-radius: 999px;
          background-image: linear-gradient(0deg, #f0f0f0, #ffffff);
          z-index: -1;
          box-shadow:
            0px 0px 16px rgba(255,255,255,0.3),
            0px 0px 32px rgba(255,255,255,0.15),
            0px 0px 20px rgba(255,255,255,0.1);
        }
        .beta-dot {
          width: 7px; height: 7px; border-radius: 50%;
          background-color: #0051ff; box-shadow: 0 0 6px rgba(0,81,255,0.7);
          flex-shrink: 0; animation: pulse-dot 2s ease-in-out infinite;
        }
        .beta-text { white-space: nowrap; }
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; box-shadow: 0 0 6px rgba(0,81,255,0.7); }
          50% { opacity: 0.6; box-shadow: 0 0 10px rgba(0,81,255,1); }
        }
      `}} />
    </div>
  );
};

// --- Framed White Button Component ---
const FramedWhiteButton = () => {
  return (
    <div className="btn-wrapper">
      <Link href="/upload" className="flex justify-center text-center no-underline">
        <button className="btn group flex items-center justify-center">
          <HiSparkles
            className="btn-sparkle"
            style={{
              height: "20px",
              width: "20px",
              marginRight: "0.5rem",
              flexShrink: 0,
              fill: "rgba(0,0,0,0.8)",
              transition: "fill 0.4s ease, filter 0.4s ease",
            }}
          />
          <span className="txt-wrapper">Try it now</span>
        </button>
      </Link>

      <style dangerouslySetInnerHTML={{ __html: `
        .btn-wrapper { position: relative; display: inline-block; }
        .btn {
          --border-radius: 24px; --padding: 4px;
          --button-color: #ffffff; --highlight-color-hue: 210deg;
          user-select: none; display: flex; align-items: center;
          justify-content: center; padding: 0.5em 0.8em 0.5em 0.8em;
          font-family: var(--font-geist-sans);
          font-size: 1.1em; font-weight: 500; color: rgba(0,0,0,0.8);
          background-color: var(--button-color);
          box-shadow:
            inset 0px 1px 1px rgba(255,255,255,0.8),
            inset 0px 2px 2px rgba(255,255,255,0.6),
            inset 0px 4px 4px rgba(255,255,255,0.4),
            inset 0px 8px 8px rgba(0,0,0,0.02),
            inset 0px 16px 16px rgba(0,0,0,0.03),
            0px 0px 4px rgba(0,0,0,0.05),
            0px 0px 8px rgba(0,0,0,0.08),
            0px 0px 16px rgba(0,0,0,0.1);
          border: solid 1px rgba(0,0,0,0.1);
          border-radius: var(--border-radius); cursor: pointer;
          transition: transform 0.2s ease, background-color 0.2s ease;
        }
        .btn::before {
          content: ""; position: absolute;
          top: calc(0px - var(--padding)); left: calc(0px - var(--padding));
          width: calc(100% + var(--padding) * 2);
          height: calc(100% + var(--padding) * 2);
          border-radius: calc(var(--border-radius) + var(--padding));
          pointer-events: none;
          background-image: linear-gradient(0deg, #f0f0f0, #ffffff);
          z-index: -1; transition: box-shadow 0.4s ease;
          box-shadow:
            0 -8px 8px -6px rgba(0,0,0,0.05) inset,
            0 -16px 16px -8px rgba(0,0,0,0.02) inset,
            1px 1px 2px rgba(0,0,0,0.05), 2px 2px 4px rgba(0,0,0,0.05),
            -1px -1px 2px rgba(255,255,255,0.8), -2px -2px 4px rgba(255,255,255,0.5),
            0px 0px 24px rgba(255,255,255,0.4),
            0px 0px 48px rgba(255,255,255,0.2),
            0px 0px 20px rgba(255,255,255,0.1);
        }
        .btn:hover::before {
          box-shadow:
            0 -8px 8px -6px rgba(0,0,0,0.05) inset,
            0 -16px 16px -8px rgba(0,0,0,0.02) inset,
            1px 1px 2px rgba(0,0,0,0.05), 2px 2px 4px rgba(0,0,0,0.05),
            -1px -1px 2px rgba(255,255,255,0.8), -2px -2px 4px rgba(255,255,255,0.5),
            0px 0px 24px rgba(0,81,255,0.8),
            0px 0px 48px rgb(0,140,255),
            0px 0px 80px rgba(0,153,255,0.4);
        }
        .btn:hover .btn-sparkle {
          fill: rgb(0,81,255) !important;
          filter: drop-shadow(0 0 4px rgba(0,81,255,0.4));
        }
        .txt-wrapper {
          position: relative; display: flex; align-items: center;
          min-width: 5em; white-space: nowrap;
        }
        .btn:active {
          border: solid 1px hsla(var(--highlight-color-hue), 100%, 70%, 40%);
          background-color: #f8f9fa; transform: scale(0.98);
        }
      `}} />
    </div>
  );
};

// --- APP HELPERS ---
const getCategoryGradient = (category: string) => {
  const cat = category?.toLowerCase().trim() || '';
  if (cat.includes('electronic') || cat.includes('tech') || cat.includes('computer')) return 'bg-gradient-to-r from-blue-500 to-cyan-400 text-white shadow-blue-500/20';
  if (cat.includes('furniture') || cat.includes('home')) return 'bg-gradient-to-r from-orange-400 to-amber-500 text-white shadow-orange-500/20';
  if (cat.includes('jewelry') || cat.includes('watch') || cat.includes('accessory')) return 'bg-gradient-to-r from-purple-500 to-fuchsia-500 text-white shadow-purple-500/20';
  if (cat.includes('appliance') || cat.includes('kitchen')) return 'bg-gradient-to-r from-teal-400 to-emerald-500 text-white shadow-teal-500/20';
  if (cat.includes('art') || cat.includes('decor')) return 'bg-gradient-to-r from-rose-400 to-red-500 text-white shadow-rose-500/20';
  if (cat.includes('clothing') || cat.includes('apparel') || cat.includes('textile')) return 'bg-gradient-to-r from-indigo-400 to-blue-500 text-white shadow-indigo-500/20';
  return 'bg-gradient-to-r from-[rgb(21,89,249)] to-[rgb(87,168,255)] text-white shadow-blue-500/20';
};

const Badge = ({ icon, text, active = false }: { icon: React.ReactNode; text: string; active?: boolean }) => (
  <button
    className={`flex items-center gap-2 px-3 py-1.5 rounded-[10px] border text-[13px] font-medium transition-colors font-geist-sans
      ${active
        ? 'bg-[#1a1a1a] border-[#333333] text-white shadow-sm'
        : 'bg-[#0f0f11] border-[#1f1f22] text-[#888888] hover:bg-[#161618] hover:text-neutral-300'
      }`}
  >
    <span className={active ? "text-yellow-400" : "text-[#666666]"}>{icon}</span>
    {text}
  </button>
);

// --- TWINKLE DOT MATRIX ---
const TWINKLE_DOTS = Array.from({ length: 60 }, (_, i) => ({
  id: i,
  x: ((i * 12.3 + i * i * 0.07) % 97) + 1.5,
  y: ((i * 17.7 + i * i * 0.11) % 97) + 1.5,
  delay: (i * 0.19) % 5,
  duration: 2.5 + (i * 0.23) % 2.5,
  opacity: 0.1 + (i % 5) * 0.08,
}));

const TwinklingDots = () => (
  <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}>
    {TWINKLE_DOTS.map(dot => (
      <div
        key={dot.id}
        style={{
          position: 'absolute',
          left: `${dot.x}%`,
          top: `${dot.y}%`,
          width: '2px',
          height: '2px',
          borderRadius: '50%',
          backgroundColor: `rgba(255,255,255,${dot.opacity})`,
          animation: `twinkle-dot ${dot.duration}s ${dot.delay}s ease-in-out infinite`,
        }}
      />
    ))}
  </div>
);

const GlowLine = () => (
  <div style={{
    backgroundImage: "linear-gradient(to right, rgb(21, 89, 249), rgb(87, 168, 255))",
    width: "52px",
    height: "2.5px",
    position: "absolute",
    inset: "1px auto auto 40px",
    boxShadow: "0 33px 90px rgba(0, 81, 255, 0.9), 0 16px 50px rgba(87, 168, 255, 0.9), 0 10px 30px rgba(0, 81, 255, 0.8), 0 12px 30px rgba(87, 168, 255, 0.8), 0 4.2px 12px rgba(0, 81, 255, 0.7), 0 2.5px 8px rgba(87, 168, 255, 0.6), 0 1.5px 4px rgba(0, 81, 255, 0.5), 0 0px 15px rgba(87, 168, 255, 0.8)",
    zIndex: 0
  }} />
);

// ── 1. MOCK DISPLAY TABLE (Read Only - AI Results) ──
const MockDisplayTable = () => {
  const items = [
    { id: 1, name: "Area Rug",            category: "Textiles",   price: "$300.00",   desc: "Light-colored area rug with a geometric pattern" },
    { id: 2, name: "Coffee Table",         category: "Furniture",  price: "$450.00",   desc: "Dark wood rectangular coffee table"            },
    { id: 3, name: "Samsung Refrigerator", category: "Appliances", price: "$1,899.00", desc: "Stainless steel french door refrigerator"       },
    { id: 4, name: "Decorative Bowl",      category: "Decor",      price: "$25.00",    desc: "Dark ceramic bowl with painted accents"        },
  ];

  return (
    <div className="w-full overflow-hidden rounded-[20px] border border-gray-100 bg-white shadow-sm relative">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-[13px] whitespace-nowrap">
          <thead className="bg-gray-50/80 border-b border-gray-100 text-gray-400 uppercase tracking-wider text-[10px] font-semibold font-just-sans">
            <tr>
              <th className="px-5 py-3.5 w-10 text-center">#</th>
              <th className="px-5 py-3.5 w-14">Asset</th>
              <th className="px-5 py-3.5">Name</th>
              <th className="px-5 py-3.5">Valuation</th>
              <th className="px-5 py-3.5">Category</th>
              <th className="px-5 py-3.5">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {items.map((item, i) => (
              <tr key={item.id} className="hover:bg-gray-50/60 transition-colors group font-geist-sans">
                <td className="px-5 py-3.5 text-center text-gray-400 font-semibold font-just-sans text-xs">{i + 1}</td>
                <td className="px-5 py-3.5">
                  <div className="w-9 h-9 rounded-lg bg-gray-100 border border-gray-200 flex items-center justify-center text-gray-400">
                    <FiImage size={14} />
                  </div>
                </td>
                <td className="px-5 py-3.5 text-gray-900 font-semibold font-just-sans">{item.name}</td>
                <td className="px-5 py-3.5 text-gray-700 font-semibold font-just-sans">{item.price}</td>
                <td className="px-5 py-3.5">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold shadow-sm capitalize ${getCategoryGradient(item.category)}`}>
                    {item.category}
                  </span>
                </td>
                <td className="px-5 py-3.5 text-gray-400 font-geist-sans truncate max-w-[200px]">{item.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ── 2. MOCK EDITABLE TABLE (Add/Edit/Delete) ──
const MockEditableTable = () => {
  const [items, setItems] = useState([
    { id: 1, name: "Books",           category: "Decor",     price: 20,  desc: "Stack of decorative books on the shelf" },
    { id: 2, name: "Decorative Bowl", category: "Decor",     price: 25,  desc: "Dark ceramic bowl with painted accents"  },
    { id: 3, name: "Floor Lamp",      category: "Furniture", price: 120, desc: "Brushed brass arc lamp with linen shade" },
  ]);

  const [adding, setAdding]           = useState(false);
  const [newName, setNewName]         = useState("");
  const [newPrice, setNewPrice]       = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [newDesc, setNewDesc]         = useState("");
  const [saveFlash, setSaveFlash]     = useState(false);
  const [errors, setErrors]           = useState<Record<string, boolean>>({});

  const [editingId, setEditingId]     = useState<number | null>(null);
  const [editName, setEditName]       = useState("");
  const [editPrice, setEditPrice]     = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [editDesc, setEditDesc]       = useState("");

  const formatPrice = (p: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(p);

  const handleAdd = () => {
    const e: Record<string, boolean> = {};
    if (!newName.trim())     e.name     = true;
    if (!newPrice.trim())    e.price    = true;
    if (!newCategory.trim()) e.category = true;
    if (Object.keys(e).length) { setErrors(e); return; }
    setItems(prev => [
      { id: Date.now(), name: newName.trim(), category: newCategory.trim(),
        price: parseFloat(newPrice), desc: newDesc.trim() || "Added manually" },
      ...prev,
    ]);
    setSaveFlash(true);
    setTimeout(() => setSaveFlash(false), 1200);
    setAdding(false);
    setNewName(""); setNewPrice(""); setNewCategory(""); setNewDesc("");
    setErrors({});
  };

  const handleAddCancel = () => {
    setAdding(false);
    setNewName(""); setNewPrice(""); setNewCategory(""); setNewDesc("");
    setErrors({});
  };

  const startEdit = (item: typeof items[0]) => {
    setEditingId(item.id);
    setEditName(item.name);
    setEditPrice(String(item.price));
    setEditCategory(item.category);
    setEditDesc(item.desc);
  };

  const handleEditSave = () => {
    if (!editName.trim() || !editPrice || !editCategory.trim()) return;
    setItems(prev => prev.map(i =>
      i.id === editingId
        ? { ...i, name: editName.trim(), price: parseFloat(editPrice),
            category: editCategory.trim(), desc: editDesc.trim() }
        : i
    ));
    setSaveFlash(true);
    setTimeout(() => setSaveFlash(false), 1200);
    setEditingId(null);
  };

  const handleEditCancel = () => setEditingId(null);

  const handleDelete = (id: number) => setItems(prev => prev.filter(i => i.id !== id));

  const addInputCls = (err?: boolean) =>
    `w-full bg-blue-50 border rounded px-2.5 py-1.5 text-gray-800 text-xs outline-none transition-colors font-geist-sans
    ${err ? "border-red-400 focus:border-red-500" : "border-blue-200 focus:border-[#0051ff]"}`;

  const editInputCls =
    "w-full bg-gray-50 border border-gray-200 rounded px-2.5 py-1.5 text-gray-800 text-xs outline-none focus:border-[#0051ff] transition-colors font-geist-sans";

  return (
    <div className="w-full overflow-hidden rounded-[20px] border border-gray-100 bg-white shadow-sm relative">

      {/* Toolbar */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100 bg-gray-50/60">
        <span className="text-gray-400 text-[11px] font-geist-sans uppercase tracking-wider font-semibold">
          {items.length} asset{items.length !== 1 ? "s" : ""}
        </span>
        <div className="flex items-center gap-3">
          {saveFlash && (
            <span className="text-emerald-500 text-[11px] font-semibold font-geist-sans flex items-center gap-1">
              <FiCheck size={12} /> Saved
            </span>
          )}
          {!adding && (
            <button
              onClick={() => { setAdding(true); setEditingId(null); }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-[rgb(21,89,249)] to-[rgb(87,168,255)]
                text-white text-[11px] font-bold font-geist-sans shadow-sm hover:opacity-90 transition-opacity"
            >
              <FiPlus size={12} /> Add Asset
            </button>
          )}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-[13px] whitespace-nowrap">
          <thead className="bg-gray-50/80 border-b border-gray-100 text-gray-400 uppercase tracking-wider text-[10px] font-semibold font-geist-sans">
            <tr>
              <th className="px-5 py-3.5 w-10 text-center">#</th>
              <th className="px-5 py-3.5 w-14">Asset</th>
              <th className="px-5 py-3.5">Name</th>
              <th className="px-5 py-3.5">Valuation</th>
              <th className="px-5 py-3.5">Category</th>
              <th className="px-5 py-3.5">Details</th>
              <th className="px-5 py-3.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">

            {/* ── Add Row ── */}
            {adding && (
              <tr className="bg-blue-50/40">
                <td className="px-5 py-3 text-center text-blue-400"><FiPlus size={13} className="mx-auto" /></td>
                <td className="px-5 py-3">
                  <div className="w-9 h-9 rounded-lg bg-blue-100 border border-blue-200 flex items-center justify-center text-blue-400">
                    <FiImage size={13} />
                  </div>
                </td>
                <td className="px-5 py-3 min-w-[130px]">
                  <input autoFocus type="text" value={newName}
                    onChange={e => { setNewName(e.target.value); setErrors(p => ({ ...p, name: false })); }}
                    placeholder="Asset name" className={addInputCls(errors.name)} />
                  {errors.name && <p className="text-red-400 text-[9px] mt-0.5 font-geist-sans">Required</p>}
                </td>
                <td className="px-5 py-3 min-w-[90px]">
                  <input type="number" value={newPrice}
                    onChange={e => { setNewPrice(e.target.value); setErrors(p => ({ ...p, price: false })); }}
                    placeholder="0.00" className={addInputCls(errors.price) + " !w-24"} />
                  {errors.price && <p className="text-red-400 text-[9px] mt-0.5 font-geist-sans">Required</p>}
                </td>
                <td className="px-5 py-3 min-w-[110px]">
                  <input type="text" value={newCategory}
                    onChange={e => { setNewCategory(e.target.value); setErrors(p => ({ ...p, category: false })); }}
                    placeholder="Category" className={addInputCls(errors.category)} />
                  {errors.category && <p className="text-red-400 text-[9px] mt-0.5 font-geist-sans">Required</p>}
                </td>
                <td className="px-5 py-3 min-w-[160px]">
                  <input type="text" value={newDesc}
                    onChange={e => setNewDesc(e.target.value)}
                    placeholder="Short description (optional)" className={addInputCls()} />
                </td>
                <td className="px-5 py-3 text-right">
                  <div className="flex justify-end gap-1">
                    <button onClick={handleAdd}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200
                        text-emerald-600 text-[11px] font-bold font-geist-sans hover:bg-emerald-100 transition-colors">
                      <FiCheck size={12} /> Save
                    </button>
                    <button onClick={handleAddCancel}
                      className="p-1.5 rounded-lg border border-gray-200 text-gray-400 hover:text-red-500
                        hover:border-red-200 hover:bg-red-50 transition-colors">
                      <FiX size={13} />
                    </button>
                  </div>
                </td>
              </tr>
            )}

            {items.length === 0 && !adding ? (
              <tr>
                <td colSpan={7} className="px-6 py-10 text-center text-gray-400 font-geist-sans text-sm">
                  No assets yet — click <strong className="text-[#0051ff]">Add Asset</strong> to get started.
                </td>
              </tr>
            ) : (
              items.map((item, i) => {
                const isEditing = editingId === item.id;
                return (
                  <tr key={item.id} className={`transition-colors group font-geist-sans ${isEditing ? "bg-gray-50" : "hover:bg-gray-50/60"}`}>
                    <td className="px-5 py-3 text-center text-gray-400 font-semibold font-just-sans text-xs">{i + 1}</td>
                    <td className="px-5 py-3">
                      <div className="w-9 h-9 rounded-lg bg-gray-100 border border-gray-200 flex items-center justify-center text-gray-400">
                        <FiImage size={14} />
                      </div>
                    </td>

                    {/* Name */}
                    <td className="px-5 py-3">
                      {isEditing
                        ? <input autoFocus type="text" value={editName}
                            onChange={e => setEditName(e.target.value)}
                            className={editInputCls} />
                        : <span className="text-gray-900 font-semibold font-just-sans">{item.name}</span>
                      }
                    </td>

                    {/* Valuation */}
                    <td className="px-5 py-3">
                      {isEditing
                        ? <input type="number" value={editPrice}
                            onChange={e => setEditPrice(e.target.value)}
                            className={editInputCls + " w-24"} />
                        : <span className="text-gray-700 font-semibold font-just-sans">{formatPrice(item.price)}</span>
                      }
                    </td>

                    {/* Category */}
                    <td className="px-5 py-3">
                      {isEditing
                        ? <input type="text" value={editCategory}
                            onChange={e => setEditCategory(e.target.value)}
                            className={editInputCls} />
                        : <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold shadow-sm capitalize ${getCategoryGradient(item.category)}`}>
                            {item.category}
                          </span>
                      }
                    </td>

                    {/* Details */}
                    <td className="px-5 py-3">
                      {isEditing
                        ? <input type="text" value={editDesc}
                            onChange={e => setEditDesc(e.target.value)}
                            className={editInputCls + " max-w-[200px]"} />
                        : <span className="text-gray-400 font-geist-sans truncate max-w-[200px] block">{item.desc}</span>
                      }
                    </td>

                    {/* Actions */}
                    <td className="px-5 py-3 text-right">
                      {isEditing ? (
                        <div className="flex justify-end gap-1">
                          <button onClick={handleEditSave}
                            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200
                              text-emerald-600 text-[11px] font-bold font-geist-sans hover:bg-emerald-100 transition-colors">
                            <FiCheck size={12} /> Save
                          </button>
                          <button onClick={handleEditCancel}
                            className="p-1.5 rounded-lg border border-gray-200 text-gray-400 hover:text-red-500
                              hover:border-red-200 hover:bg-red-50 transition-colors">
                            <FiX size={13} />
                          </button>
                        </div>
                      ) : (
                        <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button onClick={() => { startEdit(item); setAdding(false); }}
                            className="p-1.5 text-gray-400 hover:text-[#0051ff] hover:bg-blue-50 rounded-md transition-colors"
                            title="Edit">
                            <FiEdit2 size={14} />
                          </button>
                          <button onClick={() => handleDelete(item.id)}
                            className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors"
                            title="Delete">
                            <FiTrash2 size={14} />
                          </button>
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
  );
};

// ── 3. MOCK CSV PREVIEW (Insurer Ready Spreadsheet Style) ──
const MockCSVPreview = () => {
  const [status, setStatus] = useState("idle");

  const rows = [
    { id: 1, category: "Textiles", name: "Area Rug", brand: "", desc: "Light-colored area rug with a geometric pattern.", value: "300.00" },
    { id: 2, category: "Decor", name: "Books", brand: "", desc: "Stack of decorative books on a tray.", value: "20.00" },
    { id: 3, category: "Decor", name: "Books", brand: "", desc: "Stack of books on the coffee table lower shelf.", value: "15.00" },
    { id: 4, category: "Decor", name: "Books", brand: "", desc: "Small stack of books on the lower shelf of the l...", value: "10.00" },
    { id: 5, category: "Furniture", name: "Coffee Table", brand: "", desc: "Dark wood rectangular coffee table with a low...", value: "450.00" },
    { id: 6, category: "Decor", name: "Decorative Bowl", brand: "", desc: "Dark decorative bowl with paper items on the c...", value: "25.00" },
  ];

  const total = 820.00; // Mock total value

  const handleDownload = () => {
    if (status !== "idle") return;
    setStatus("loading");
    setTimeout(() => setStatus("done"), 1400);
    setTimeout(() => setStatus("idle"), 3200);
  };

  return (
    <div className="relative w-full rounded-[20px] border border-[#1a1a1c] bg-[#0c0c0e] overflow-hidden flex flex-col h-[320px]">
      
      {/* Window chrome */}
      <div className="bg-[#141416] border-b border-[#1a1a1c] px-4 py-2.5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f57]/40 border border-[#ff5f57]/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#febc2e]/40 border border-[#febc2e]/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#28c840]/40 border border-[#28c840]/60" />
          </div>
          <span className="text-[#555] text-[11px] font-mono ml-2">claimready_inventory.csv</span>
        </div>
        <span className="text-[#444] text-[10px] font-geist-sans">{rows.length} rows · ${total.toLocaleString()}</span>
      </div>

      {/* Spreadsheet table preview (Light mode to mimic Excel/Sheets) */}
      <div className="overflow-auto bg-white flex-1 relative">
        <table className="w-full text-[11px] md:text-xs font-sans border-collapse text-black">
          <thead className="bg-[#cccccc]">
            <tr>
              <th className="px-3 py-2 border border-[#b3b3b3] text-left font-bold w-[15%]">category</th>
              <th className="px-3 py-2 border border-[#b3b3b3] text-left font-bold w-[20%]">name</th>
              <th className="px-3 py-2 border border-[#b3b3b3] text-left font-bold w-[10%]">brand</th>
              <th className="px-3 py-2 border border-[#b3b3b3] text-left font-bold w-[40%]">description</th>
              <th className="px-3 py-2 border border-[#b3b3b3] text-right font-bold w-[15%]">price_usd</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={row.id} className={i % 2 === 0 ? "bg-white" : "bg-[#ebebeb]"}>
                <td className="px-3 py-2 border border-[#d9d9d9] font-bold">{row.category}</td>
                <td className="px-3 py-2 border border-[#d9d9d9]">{row.name}</td>
                <td className="px-3 py-2 border border-[#d9d9d9]">{row.brand}</td>
                <td className="px-3 py-2 border border-[#d9d9d9] whitespace-nowrap overflow-hidden text-ellipsis max-w-[200px]">{row.desc}</td>
                <td className="px-3 py-2 border border-[#d9d9d9] text-right">{row.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer bar with download */}
      <div className="border-t border-[#1a1a1c] bg-[#141416] px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-[#86efac] shadow-[0_0_6px_rgba(134,239,172,0.6)]" />
          <span className="text-[#555] text-[11px] font-geist-sans">
            Insurance-formatted · <span className="text-[#86efac] font-semibold">${total.toLocaleString()} total</span>
          </span>
        </div>

        <button
          onClick={handleDownload}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-[12px] font-bold font-just-sans
            transition-all duration-300 select-none
            ${status === "done"
              ? "bg-[#86efac] text-[#0a0a0c] scale-95"
              : status === "loading"
              ? "bg-white/10 text-[#888] cursor-wait"
              : "bg-white text-black hover:bg-[#f0f0f0] active:scale-95 shadow-md"
            }`}
        >
          {status === "done"    && <><FiCheck size={14} /> Downloaded!</>}
          {status === "loading" && (
            <>
              <span className="inline-block w-3 h-3 border border-[#888] border-t-transparent rounded-full animate-spin" />
              Preparing…
            </>
          )}
          {status === "idle" && <><FiDownload size={14} /> Download .CSV</>}
        </button>
      </div>
    </div>
  );
};


// --- Bento Grid Section ---
const BentoGridSection = () => {
  return (
    <div className="w-full pb-32 px-6 flex justify-center z-10 relative">
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes twinkle-dot {
          0%, 100% { opacity: 0; transform: scale(0.8); }
          50%       { opacity: 1; transform: scale(1.2); }
        }
      `}} />

      <div className="max-w-[1000px] w-full flex flex-col gap-6">

        {/* ── ROW 1: Instant AI Valuations (FULL WIDTH) ── */}
        <div className="relative overflow-hidden rounded-[32px] border border-white/5 bg-[#0c0c0e] p-8 md:p-10 shadow-2xl group">
          <TwinklingDots />
          <GlowLine />

          <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
            <div className="max-w-xl">
              <div className="relative z-10 flex items-center justify-center w-[46px] h-[46px] rounded-2xl bg-[#161618] border border-white/5 mb-6 shadow-inner">
                <RiSparklingLine className="text-xl" style={{ fill: "url(#brand-gradient)" }} />
              </div>
              <h3 className="relative z-10 text-[26px] font-bold text-white mb-3 tracking-tight font-just-sans">
                Instant AI Valuations
              </h3>
              <p className="relative z-10 text-[#888888] text-[15px] leading-relaxed" style={{ fontFamily: "var(--font-geist-sans)"}}>
                Upload a photo of any item and ClaimReady identifies it, researches current market prices, and assigns an accurate replacement value — in seconds.
              </p>
            </div>
          </div>

          <div className="relative z-10 w-full">
            <MockDisplayTable />
          </div>
        </div>

        {/* ── ROW 2: Your asset inventory, always up to date (FULL WIDTH) ── */}
        <div className="relative overflow-hidden rounded-[32px] border border-white/5 bg-[#0c0c0e] p-8 md:p-10 shadow-2xl group">
          <TwinklingDots />
          <GlowLine />

          <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
            <div className="max-w-xl">
              <div className="relative z-10 flex items-center justify-center w-[46px] h-[46px] rounded-2xl bg-[#161618] border border-white/5 mb-6 shadow-inner">
                <TbExchange className="text-xl" style={{ stroke: "url(#brand-gradient)" }} />
              </div>
              <h3 className="relative z-10 text-[26px] font-bold text-white mb-3 tracking-tight font-just-sans">
                Your asset inventory, always up to date
              </h3>
              <p className="relative z-10 text-[#888888] text-[15px] leading-relaxed" style={{ fontFamily: "var(--font-geist-sans)"}}>
                Add new items, edit valuations, remove things you no longer own. Stay current so you're never caught off guard when filing.
              </p>
            </div>

            <div className="relative z-10 flex flex-col items-end opacity-50 group-hover:opacity-100 transition-opacity duration-300">
              <span className="text-[11px] text-[#888] font-just-sans tracking-wide uppercase flex items-center gap-1.5 mb-1">
                <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse " />
                Live Interactive Demo
              </span>
              <span className="text-[11px] text-[#666]" style={{ fontFamily: "var(--font-geist-sans)"}}>
                Try adding or deleting a row below
              </span>
            </div>
          </div>

          <div className="relative z-10 w-full">
            <MockEditableTable />
          </div>
        </div>

        {/* ── ROW 3: Insurer Ready (2/3) + Secure (1/3) ── */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

          {/* Insurer Ready in one click */}
          <div className="md:col-span-2 relative overflow-hidden rounded-[32px] border border-white/5 bg-[#0c0c0e] p-8 md:p-10 shadow-2xl group">
            <TwinklingDots />
            <GlowLine />

            <div className="relative z-10 flex items-center justify-center w-[46px] h-[46px] rounded-2xl bg-[#161618] border border-white/5 mb-6 shadow-inner">
              <FiSend className="text-xl" style={{ stroke: "url(#brand-gradient)" }} />
            </div>

            <h3 className="relative z-10 text-[26px] font-bold text-white mb-3 tracking-tight font-just-sans">
              Insurer-ready in one click
            </h3>
            <p className="relative z-10 text-[#888888] text-[15px] mb-8 leading-relaxed max-w-[80%]" style={{ fontFamily: "var(--font-geist-sans)"}}>
              Generate a professional CSV report formatted exactly the way insurance companies expect. No reformatting, no back and forth.
            </p>

            <div className="relative z-10 w-full">
              <MockCSVPreview />
            </div>
          </div>

          {/* Secure & Private */}
          <div className="md:col-span-1 relative overflow-hidden rounded-[32px] border border-white/5 bg-[#0c0c0e] p-8 md:p-10 shadow-2xl group flex flex-col">
            <TwinklingDots />
            <GlowLine />

            <div className="relative z-10 flex items-center justify-center w-[46px] h-[46px] rounded-2xl bg-[#161618] border border-white/5 mb-6 shadow-inner">
              <FiLock className="text-xl" style={{ stroke: "url(#brand-gradient)" }} />
            </div>

            <h3 className="relative z-10 text-[26px] font-bold text-white mb-3 tracking-tight font-just-sans">
              Secure & private
            </h3>
            <p className="relative z-10 text-[#888888] text-[15px] mb-auto leading-relaxed" style={{ fontFamily: "var(--font-geist-sans)"}}>
              Your data is encrypted end-to-end and never shared or sold. Built with privacy and security as the #1 priority.
            </p>

            <div className="relative z-10 w-full rounded-[20px] border border-[#1a1a1c] bg-[#080809] p-5 flex flex-col gap-5 mt-8">
              <div className="flex items-center justify-between w-full rounded-xl bg-[#141416] border border-[#222] px-4 py-3">
                <div className="flex items-center gap-3">
                  <FiLock className="text-white" />
                  <span className="text-[14px] text-white font-medium font-just-sans">End-to-end encrypted</span>
                </div>
              </div>
              <div className="border-t border-dashed border-[#222] pt-4 flex items-center gap-2 text-[#555] text-[12px] font-geist-sans">
                <div className="w-3.5 h-3.5 rounded-full border border-[#555] flex items-center justify-center text-[9px]" >i</div>
                <span style={{ fontFamily: "var(--font-geist-sans)"}}>Never shared or sold</span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

// --- Card Data for Scrollspy ---
const FEATURES = [
  {
    id: 1,
    shortTitle: "SCAN ROOM",
    title: "Scan your room",
    description: "Simply pan your phone's camera around any room. No need to catalog items one by one.",
  },
  {
    id: 2,
    shortTitle: "AI IDENTIFICATION",
    title: "Our AI model identifies assets",
    description: "Our vision models instantly recognize, categorize, and estimate the value of your belongings.",
  },
  {
    id: 3,
    shortTitle: "Safety first",
    title: "Securely stored",
    description: "Your inventory is encrypted end-to-end and your data is never shared or sold.",
  },
  {
    id: 4,
    shortTitle: "READY REPORTS",
    title: "Ready when needed",
    description: "Generate comprehensive, insurer-approved reports in seconds if you ever need to file a claim.",
  }
];

export default function AboutPage() {
  const BADGE_TOP_PX = 20;

  const [activeSection, setActiveSection] = useState(1);
  const isClickScrolling = useRef(false);
  const scrollTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !isClickScrolling.current) {
            setActiveSection(Number(entry.target.getAttribute("data-id")));
          }
        });
      },
      {
        rootMargin: "-20% 0px -40% 0px",
        threshold: 0,
      }
    );

    const elements = document.querySelectorAll(".feature-anchor");
    elements.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, []);

  const scrollToSection = (id: number) => {
    isClickScrolling.current = true;
    setActiveSection(id);

    const element = document.getElementById(`feature-anchor-${id}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    if (scrollTimeout.current) {
      clearTimeout(scrollTimeout.current);
    }

    scrollTimeout.current = setTimeout(() => {
      isClickScrolling.current = false;
    }, 1000);
  };

  return (
    <div className="relative min-h-screen bg-[var(--color-bg-primary)]">
      
      {/* Global SVG Gradient for Icons */}
      <svg width="0" height="0" className="absolute pointer-events-none">
        <defs>
          <linearGradient id="brand-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop stopColor="rgb(21, 89, 249)" offset="0%" />
            <stop stopColor="rgb(87, 168, 255)" offset="100%" />
          </linearGradient>
        </defs>
      </svg>

      <div className="sticky top-0 z-50 w-full">
        <Navbar />
      </div>

      {/* ── HERO & TABLE WRAPPER ── */}
      <div className="relative w-full max-w-7xl mx-auto px-6 md:px-12 mt-12 mb-32">
        <div
          className="md:-left-[80px] md:-right-[80px] md:-top-[40px]"
          style={{
            position: 'absolute',
            top: '-20px', left: '-60px', right: '-60px', bottom: '-70px',
            borderRadius: '20px',
            overflow: 'hidden',
            zIndex: 0,
            pointerEvents: 'none'
          }}
        >
          <Grainient
            color1="#0031ad" color2="#004cff" color3="#000000"
            timeSpeed={0.25} colorBalance={0} warpStrength={1}
            warpFrequency={5} warpSpeed={2} warpAmplitude={50}
            blendAngle={0} blendSoftness={0.05} rotationAmount={500}
            noiseScale={2} grainAmount={0.1} grainScale={1}
            grainAnimated={false} contrast={1.5} gamma={2}
            saturation={1} centerX={0} centerY={0} zoom={0.9}
          />
        </div>

        <div className="relative z-10 w-full flex flex-col items-center">
          <div style={{ width: "100%", height: "45vh", minHeight: "450px", position: "relative" }}>
            <div
              style={{
                position: "absolute",
                top: `${BADGE_TOP_PX}px`,
                left: "50%",
                transform: "translateX(-50%)",
                zIndex: 10,
                pointerEvents: "auto",
                whiteSpace: "nowrap",
              }}
            >
              <BetaBadge />
            </div>

            <div
              style={{
                position: "absolute",
                top: "50%",
                left: "50%",
                transform: "translate(-50%, -50%)",
                width: "100%",
                textAlign: "center",
                zIndex: 10,
                pointerEvents: "none",
              }}
            >
              <h1
                style={{
                  color: "#ffffff",
                  fontFamily: "var(--font-just-sans)",
                  fontSize: "6.4rem",
                  marginBottom: "1.5rem",
                  lineHeight: "1.1",
                }}
              >
                The AI Home Inventory
              </h1>

              <div
                style={{
                  background: "linear-gradient(90deg, rgba(255, 255, 255, 0) 0%, rgba(255, 255, 255, 0.91) 50%, rgba(255, 255, 255, 0) 100%)",
                  opacity: 1,
                  transform: "none",
                  height: "2px",
                  width: "60%",
                  maxWidth: "500px",
                  margin: "0 auto 1.5rem auto",
                }}
              />

              <p
                style={{
                  color: "rgba(231, 231, 231, 0.78)",
                  fontFamily: "var(--font-geist-sans)",
                  fontSize: "1.3rem",
                  marginBottom: "1rem",
                }}
              >
                ClaimReady documents your assets with AI <br />
                so you're always ready when it matters most.
              </p>

              <div
                style={{
                  marginTop: "2rem",
                  display: "flex",
                  justifyContent: "center",
                  pointerEvents: "auto",
                }}
              >
                <FramedWhiteButton />
              </div>
            </div>
          </div>

          <div className="relative w-full flex justify-center">
            <div
              className="relative w-full max-w-6xl rounded-2xl border border-white/20 bg-white/5 overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.5)]"
              style={{ backdropFilter: 'blur(12px)' }}
            >
              <img
                src="/new_table.png"
                alt="ClaimReady Dashboard Preview"
                className="block relative w-full h-full rounded-[inherit] object-contain dark:hidden"
              />
            </div>
          </div>
        </div>
      </div>

      {/* ── HOW IT WORKS: STACKING SCROLLSPY SECTION ── */}
      <div className="relative w-full max-w-7xl mx-auto px-6 md:px-12 pt-24 pb-32 z-10">
        <div className="mb-20 max-w-7xl">
          <div className="inline-block border border-white px-3 py-1 mb-6">
            <span
              className="text-xs tracking-widest text-white uppercase"
              style={{ fontFamily: "var(--font-geist-sans)" }}
            >
              ■ How it works
            </span>
          </div>
          <h2
            className="text-4xl md:text-5xl font-bold text-white leading-tight text-center"
            style={{ fontFamily: "var(--font-just-sans)" }}
          >
            From hours to minutes.
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-[300px_1fr] gap-16 lg:gap-32 items-start relative">
          <div className="hidden md:flex flex-col sticky top-40 z-20">
            {FEATURES.map((feature) => (
              <button
                key={feature.id}
                onClick={() => scrollToSection(feature.id)}
                className={`group text-left py-4 px-6 border-l-2 transition-all duration-300 ${
                  activeSection === feature.id
                    ? "border-[#0051ff] bg-[#0051ff]/10 text-white"
                    : "border-neutral-800 text-neutral-500 hover:text-neutral-300 hover:bg-white/5"
                }`}
              >
                <span
                  className="text-sm mr-4 opacity-70"
                  style={{ fontFamily: "var(--font-geist-sans)" }}
                >
                  0{feature.id}
                </span>
                <span
                  className="font-bold tracking-wide uppercase text-sm"
                  style={{ fontFamily: "var(--font-geist-sans)" }}
                >
                  {feature.shortTitle}
                </span>
              </button>
            ))}
          </div>

          <div className="flex flex-col relative w-full pb-[10vh]">
            {FEATURES.map((feature, index) => (
              <React.Fragment key={feature.id}>
                <div style={{ height: index === 0 ? "0" : "60vh" }} />
                <div
                  id={`feature-anchor-${feature.id}`}
                  data-id={feature.id}
                  className="feature-anchor w-full h-[1px] invisible"
                  style={{ scrollMarginTop: "10rem" }}
                />
                <div
                  className="feature-card sticky top-40 w-full rounded-[32px] transition-all duration-300"
                  style={{ zIndex: index + 10 }}
                >
                  <div className="relative w-full min-h-[450px] overflow-hidden rounded-[32px] border border-white/10 bg-[#0c0c0e] p-8 md:p-12">
                    <ShineBorder shineColor={["#ffffff", "#000000"]} duration={20} borderWidth={1.5} />
                    <div className="relative z-10 max-w-xl">
                      <div className="mb-8">
                        <span
                          className="inline-block px-3 py-1 rounded bg-neutral-900 text-neutral-400 text-xs mb-6 border border-white/10"
                          style={{ fontFamily: "var(--font-geist-sans)" }}
                        >
                          STEP 0{feature.id}
                        </span>
                        <h3
                          className="text-3xl md:text-4xl font-bold text-white mb-4"
                          style={{ fontFamily: "var(--font-just-sans)" }}
                        >
                          {feature.title}
                        </h3>
                        <p
                          className="text-lg text-[#888888] leading-relaxed"
                          style={{ fontFamily: "var(--font-geist-sans)" }}
                        >
                          {feature.description}
                        </p>
                      </div>
                      <div className="mt-8 w-full flex items-center justify-center p-4">
                        {/* The main container card that matches your image_0.png layout */}
                        <div className="w-full max-w-[900px] aspect-[16/9] rounded-xl border border-white/5 bg-gradient-to-br from-[#161618] to-[#0d0d0f] flex items-center justify-center p-2 box-border overflow-hidden">
                          
                          {/* The image, sized and contained perfectly */}
                          <img
                            src="/scanyourroom.png" // The URL or local path to your image
                            alt="A 3D isometric visualization showing a digital scan of a room, highlighting a blue couch and other furniture." // Descriptive alt text
                            className="max-w-full max-h-full h-auto w-auto object-contain rounded-md" 
                          />

                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>

      {/* ── FEATURES SECTION ── */}
      <div className="relative w-full max-w-7xl mx-auto px-6 md:px-12 pt-24 pb-12 z-10">
        <div className="mb-20 max-w-7xl flex flex-col items-center">
          <div className="inline-block border border-white px-3 py-1 mb-6">
            <span
              className="text-xs tracking-widest text-white uppercase"
              style={{ fontFamily: "var(--font-geist-sans)" }}
            >
              ■ features
            </span>
          </div>
          <h2
            className="text-4xl md:text-5xl font-bold text-white leading-tight text-center"
            style={{ fontFamily: "var(--font-just-sans)" }}
          >
            Catalog with ease.
          </h2>
        </div>
        <BentoGridSection />
      </div>

      {/* ── USE CASES SECTION ── */}
      <div className="relative w-full max-w-7xl mx-auto px-6 md:px-12 pt-12 pb-32 z-10">
        <div className="mb-20 max-w-7xl flex flex-col items-center">
          <div className="inline-block border border-white px-3 py-1 mb-6">
            <span
              className="text-xs tracking-widest text-white uppercase"
              style={{ fontFamily: "var(--font-geist-sans)" }}
            >
              ■ Use Cases
            </span>
          </div>
          <h2
            className="text-4xl md:text-5xl font-bold text-white leading-tight text-center max-w-4xl"
            style={{ fontFamily: "var(--font-just-sans)" }}
          >
            Built for every stage of the claim.
          </h2>
          <p className="text-[#888888] text-lg text-center mt-6 max-w-4xl" style ={{ fontFamily: "var(--font-geist-sans)"}}>
            Whether you're recovering from a loss or managing the restoration, ClaimReady accelerates the process.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Use Case 1: Policyholders */}
          <div className="relative overflow-hidden rounded-[32px] border border-white/5 bg-[#0c0c0e] p-8 md:p-10 shadow-2xl group transition-all hover:-translate-y-1">
            <GlowLine />
            <div className="relative z-10 flex items-center justify-center w-[46px] h-[46px] rounded-2xl bg-[#161618] border border-white/5 mb-8 shadow-inner">
              <FiHome className="text-xl" style={{ stroke: "url(#brand-gradient)" }} />
            </div>
            <h3 className="relative z-10 text-[24px] font-bold text-white mb-3 tracking-tight font-just-sans">
              For Policyholders
            </h3>
            <p className="relative z-10 text-[#555555] text-[13px] uppercase tracking-wider mb-4 font-bold font-geist-sans">
              Post-Disaster Inventory
            </p>
            <p className="relative z-10 text-[#888888] text-[15px] leading-relaxed font-geist-sans">
              Snap photos of a damaged room to instantly identify belongings, extract market values, and generate a comprehensive loss report without the manual headache.
            </p>
          </div>

          {/* Use Case 2: Desk Adjusters */}
          <div className="relative overflow-hidden rounded-[32px] border border-white/5 bg-[#0c0c0e] p-8 md:p-10 shadow-2xl group transition-all hover:-translate-y-1">
            <GlowLine />
            <div className="relative z-10 flex items-center justify-center w-[46px] h-[46px] rounded-2xl bg-[#161618] border border-white/5 mb-8 shadow-inner">
              <FiFileText className="text-xl" style={{ stroke: "url(#brand-gradient)" }} />
            </div>
            <h3 className="relative z-10 text-[24px] font-bold text-white mb-3 tracking-tight font-just-sans">
              For Desk Adjusters
            </h3>
            <p className="relative z-10 text-[#555555] text-[13px] uppercase tracking-wider mb-4 font-bold font-geist-sans">
              Accelerated Processing
            </p>
            <p className="relative z-10 text-[#888888] text-[15px] leading-relaxed font-geist-sans">
              Automate line-item extraction and pricing validation from claimant photos, cutting down hours of manual web-searching and data entry.
            </p>
          </div>

          {/* Use Case 3: Restoration Contractors */}
          <div className="relative overflow-hidden rounded-[32px] border border-white/5 bg-[#0c0c0e] p-8 md:p-10 shadow-2xl group transition-all hover:-translate-y-1">
            <GlowLine />
            <div className="relative z-10 flex items-center justify-center w-[46px] h-[46px] rounded-2xl bg-[#161618] border border-white/5 mb-8 shadow-inner">
              <FiTool className="text-xl" style={{ stroke: "url(#brand-gradient)" }} />
            </div>
            <h3 className="relative z-10 text-[24px] font-bold text-white mb-3 tracking-tight font-just-sans">
              For Restoration Contractors
            </h3>
            <p className="relative z-10 text-[#555555] text-[13px] uppercase tracking-wider mb-4 font-bold font-geist-sans">
              Pack-Out Efficiency
            </p>
            <p className="relative z-10 text-[#888888] text-[15px] leading-relaxed font-geist-sans">
              Quickly document and value a room's contents on-site before packing everything out for mitigation or demolition.
            </p>
          </div>
        </div>
      </div>

      {/* ── CALL TO ACTION SECTION ── */}
      <div className="relative w-full max-w-7xl mx-auto px-6 md:px-12 py-32 z-10 flex flex-col items-center text-center">
        <h2
          className="text-5xl md:text-6xl font-extrabold text-white leading-tight mb-6"
          style={{ fontFamily: "var(--font-just-sans)", letterSpacing: '-0.03em' }}
        >
          Your assets, secured. <br /> In minutes.
        </h2>
        <p
          className="text-lg text-[#aaaaaa] leading-relaxed mb-10 max-w-5xl"
          style={{ fontFamily: "var(--font-geist-sans)" }}
        >
          ClaimReady is in beta and available to early users. Start building your digital proof of ownership today.
        </p>
        <FramedWhiteButton />
      </div>

      {/* ── FOOTER SECTION ── */}
      <footer className="relative bg-[#0c0c0e] text-white overflow-hidden pt-24 pb-8 mt-20">

        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-[rgb(21,89,249)] to-[rgb(87,168,255)]" />

        <div className="relative z-10 container mx-auto px-6 md:px-12 grid grid-cols-1 md:grid-cols-12 gap-12">

          <div className="md:col-span-5 flex flex-col gap-6">
            <div className="relative flex items-center gap-4 mb-2 mt-4">
              <div style={{
                backgroundImage: "linear-gradient(to right, rgb(21, 89, 249), rgb(87, 168, 255))",
                width: "52px",
                height: "2.5px",
                position: "absolute",
                top: "-20px",
                left: "0",
                boxShadow: "0 33px 90px rgba(0, 81, 255, 0.9), 0 16px 50px rgba(87, 168, 255, 0.9), 0 10px 30px rgba(0, 81, 255, 0.8), 0 12px 30px rgba(87, 168, 255, 0.8), 0 4.2px 12px rgba(0, 81, 255, 0.7), 0 2.5px 8px rgba(87, 168, 255, 0.6), 0 1.5px 4px rgba(0, 81, 255, 0.5), 0 0px 15px rgba(87, 168, 255, 0.8)",
                zIndex: 0
              }} />
              <div className="flex items-center justify-center w-[46px] h-[46px] rounded-xl bg-[#161618] border border-white/5 shadow-inner flex-shrink-0">
                <span className="font-just-sans font-bold text-white text-lg tracking-wider">CR</span>
              </div>
              <div className="bg-white text-black px-5 py-3 w-max rounded-tl-xl rounded-br-xl rounded-tr-sm rounded-bl-sm">
                <h2 className="text-2xl font-extrabold font-just-sans tracking-tight">ClaimReady</h2>
              </div>
            </div>

            <p
              className="text-[#888888] font-geist-sans text-[15px] leading-relaxed max-w-sm"
              style={{ fontFamily: "var(--font-geist-sans)" }}
            >
              A smart AI inventory platform that connects your assets with precise valuations, offering secure, flexible, and instant protection.
            </p>

            <div className="flex gap-4 mt-2">
              <a href="#" className="w-12 h-12 rounded-full bg-[#161618] hover:bg-[#0051ff] transition-colors flex items-center justify-center text-white/70 hover:text-white border border-white/5 shadow-lg">
                <FiMail size={20} />
              </a>
              <a href="#" className="w-12 h-12 rounded-full bg-[#161618] hover:bg-[#0051ff] transition-colors flex items-center justify-center text-white/70 hover:text-white border border-white/5 shadow-lg">
                <FiInstagram size={20} />
              </a>
              <a href="#" className="w-12 h-12 rounded-full bg-[#161618] hover:bg-[#0051ff] transition-colors flex items-center justify-center text-white/70 hover:text-white border border-white/5 shadow-lg">
                <FiLinkedin size={20} />
              </a>
            </div>
          </div>

          <div className="hidden md:block md:col-span-1" />

          <div className="md:col-span-2 flex flex-col gap-5">
            <h4 className="text-[13px] font-just-sans font-semibold tracking-wider text-white uppercase mb-2">Company</h4>
            <Link href="#" className="text-[#888888] hover:text-white text-[15px] transition-colors" style={{ fontFamily: "var(--font-geist-sans)" }}>Contact</Link>
          </div>

          <div className="md:col-span-2 flex flex-col gap-5">
            <h4 className="text-[13px] font-semibold tracking-wider text-white uppercase mb-2" style={{ fontFamily: "var(--font-geist-sans)" }}>Product</h4>
            <Link href="#" className="text-[#888888] hover:text-white text-[15px] font-geist-sans transition-colors" style={{ fontFamily: "var(--font-geist-sans)" }}>Pricing</Link>
            <Link href="#" className="text-[#888888] hover:text-white text-[15px] font-geist-sans transition-colors" style={{ fontFamily: "var(--font-geist-sans)" }}>How It Works</Link>
            <Link href="#" className="text-[#888888] hover:text-white text-[15px] font-geist-sans transition-colors" style={{ fontFamily: "var(--font-geist-sans)" }}>FAQ</Link>
          </div>

          <div className="md:col-span-2 flex flex-col gap-5">
            <h4 className="text-[13px] font-just-sans font-semibold tracking-wider text-white uppercase mb-2">Legal</h4>
            <Link href="/terms-of-service" className="text-[#888888] hover:text-white text-[15px] transition-colors" style={{ fontFamily: "var(--font-geist-sans)" }}>Terms</Link>
            <Link href="/privacy-policy" className="text-[#888888] hover:text-white text-[15px] transition-colors" style={{ fontFamily: "var(--font-geist-sans)" }}>Privacy</Link>
          </div>
        </div>

        <div className="relative z-10 container mx-auto px-6 md:px-12 mt-24 text-center md:text-right">
          <p className="text-[#555555] text-[13px]" style={{ fontFamily: "var(--font-geist-sans)" }}>
            © 2026 — CLAIMREADY. All rights reserved.
          </p>
        </div>

        <div className="absolute bottom-[-8%] left-0 w-full flex justify-center pointer-events-none select-none z-0">
          <span
            className="font-just-sans font-black text-[#111114] leading-none"
            style={{
              fontSize: 'min(23.2vw, 450px)',
              whiteSpace: 'nowrap',
              letterSpacing: '-0.02em',
              textShadow: '0px -1px 1px rgba(255, 255, 255, 0.18)'
            }}
          >
            CLMRDY
          </span>
        </div>
      </footer>
    </div>
  );
}