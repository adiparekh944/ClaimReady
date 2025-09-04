// Shared type definitions for items across the application

export interface Item {
  code: string;
  name: string;
  category: string;
  brand: string;
  condition: string;
  price_usd: number;
  description: string;
  nullify: boolean;
  source_image?: number;
  verificationScore?: number;
  verificationNotes?: string;
}

// Legacy item interface for backward compatibility
export interface LegacyItem {
  estimated_name?: string;
  estimated_price?: number;
  best_confidence?: number;
  class?: string;
  public_url?: string;
  verificationScore?: number;
  verificationNotes?: string;
}

// Table row interface for display
export interface TableRow {
  item: string;
  price: string;
  verificationScore?: number;
  verificationNotes?: string;
}

// API response interface
export interface AnalysisResult {
  items: Item[];
  total_items: number;
  total_value: number;
  images?: Record<string, string>;
  status: string;
}
