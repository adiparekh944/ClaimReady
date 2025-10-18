# === SKU DATABASE INTEGRATION ===
# Berkeley Objects Dataset + FAISS Vector Search
# 
# This module handles:
# 1. Loading Berkeley Objects dataset
# 2. Building FAISS index for fast similarity search
# 3. Searching item embeddings against SKU database
# 4. Returning SKU matches with confidence scores

import os
import json
import pickle
import numpy as np
import faiss
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class SKUDatabase:
    def __init__(self, dataset_path: str = "test_sku_database"):
        self.dataset_path = dataset_path
        self.index = None
        self.sku_metadata = []
        self.embeddings = None
        self.is_loaded = False
        
    def load_dataset(self):
        """Load Berkeley Objects dataset and build FAISS index"""
        try:
            print("🔄 Loading Berkeley Objects dataset...")
            
            # Check if dataset exists
            if not os.path.exists(self.dataset_path):
                print(f"❌ Dataset not found at {self.dataset_path}")
                print("   Please download berkeley_objects.zip and extract it")
                return False
            
            # Load metadata (product info, prices, etc.)
            metadata_file = os.path.join(self.dataset_path, "metadata.json")
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    self.sku_metadata = json.load(f)
                print(f"✅ Loaded {len(self.sku_metadata)} SKU records")
            else:
                print("⚠️  Metadata file not found, creating placeholder")
                self.sku_metadata = []
            
            # Load pre-computed CLIP embeddings
            embeddings_file = os.path.join(self.dataset_path, "embeddings.npy")
            if os.path.exists(embeddings_file):
                self.embeddings = np.load(embeddings_file)
                print(f"✅ Loaded {self.embeddings.shape[0]} embeddings")
            else:
                print("⚠️  Embeddings file not found, will need to compute them")
                return False
            
            # Build FAISS index
            self._build_faiss_index()
            
            self.is_loaded = True
            print("🎉 SKU database loaded successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            return False
    
    def _build_faiss_index(self):
        """Build FAISS index for fast similarity search"""
        if self.embeddings is None:
            return
        
        print("🔨 Building FAISS index...")
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(self.embeddings)
        
        # Create FAISS index (512-dim for CLIP ViT-B/32)
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner Product for cosine similarity
        
        # Add embeddings to index
        self.index.add(self.embeddings.astype('float32'))
        
        print(f"✅ FAISS index built with {self.index.ntotal} vectors")
    
    def search_sku(self, item_embedding: np.ndarray, top_k: int = 3, confidence_threshold: float = 0.7) -> Dict:
        """
        Search for SKU matches for a given item embedding
        
        Args:
            item_embedding: 512-dim CLIP embedding of the item
            top_k: Number of top matches to return
            confidence_threshold: Minimum confidence score for a match
            
        Returns:
            Dict with SKU matches and confidence scores
        """
        if not self.is_loaded or self.index is None:
            return {
                'matches': [],
                'best_match': None,
                'confidence': 0.0,
                'use_producer_2': True
            }
        
        try:
            # Normalize the query embedding
            query_embedding = item_embedding.reshape(1, -1).astype('float32')
            faiss.normalize_L2(query_embedding)
            
            # Search for similar embeddings
            scores, indices = self.index.search(query_embedding, top_k)
            
            matches = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(self.sku_metadata):
                    sku_data = self.sku_metadata[idx]
                    match = {
                        'rank': i + 1,
                        'sku_id': sku_data.get('sku_id', f'unknown_{idx}'),
                        'product_name': sku_data.get('product_name', 'Unknown Product'),
                        'brand': sku_data.get('brand', 'Unknown Brand'),
                        'price_usd': sku_data.get('price_usd', 0.0),
                        'category': sku_data.get('category', 'Unknown'),
                        'confidence': float(score),
                        'description': sku_data.get('description', 'No description available')
                    }
                    matches.append(match)
            
            # Determine best match and routing decision
            best_match = matches[0] if matches else None
            best_confidence = best_match['confidence'] if best_match else 0.0
            
            # Route to Producer 1 (SKU found) or Producer 2 (LLM fallback)
            use_producer_2 = best_confidence < confidence_threshold
            
            return {
                'matches': matches,
                'best_match': best_match,
                'confidence': best_confidence,
                'use_producer_2': use_producer_2,
                'total_matches': len(matches)
            }
            
        except Exception as e:
            logger.error(f"SKU search failed: {e}")
            return {
                'matches': [],
                'best_match': None,
                'confidence': 0.0,
                'use_producer_2': True,
                'error': str(e)
            }
    
    def get_sku_info(self, sku_id: str) -> Optional[Dict]:
        """Get detailed SKU information by ID"""
        for sku in self.sku_metadata:
            if sku.get('sku_id') == sku_id:
                return sku
        return None
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        if not self.is_loaded:
            return {'status': 'not_loaded'}
        
        return {
            'status': 'loaded',
            'total_skus': len(self.sku_metadata),
            'total_embeddings': self.index.ntotal if self.index else 0,
            'embedding_dimension': self.embeddings.shape[1] if self.embeddings is not None else 0
        }

# Global SKU database instance
sku_db = SKUDatabase()

def initialize_sku_database():
    """Initialize the SKU database on startup"""
    return sku_db.load_dataset()

def search_item_sku(item_embedding: np.ndarray, confidence_threshold: float = 0.7) -> Dict:
    """Search for SKU matches for an item embedding"""
    return sku_db.search_sku(item_embedding, confidence_threshold=confidence_threshold)

def get_database_stats() -> Dict:
    """Get SKU database statistics"""
    return sku_db.get_stats()

# Test function
def test_sku_database():
    """Test the SKU database with a dummy embedding"""
    if not sku_db.is_loaded:
        print("❌ SKU database not loaded")
        return
    
    # Create a dummy 512-dim embedding
    dummy_embedding = np.random.rand(512).astype('float32')
    
    print("🧪 Testing SKU search with dummy embedding...")
    results = search_item_sku(dummy_embedding)
    
    print(f"✅ Search completed:")
    print(f"   Matches found: {len(results['matches'])}")
    print(f"   Best confidence: {results['confidence']:.3f}")
    print(f"   Use Producer 2: {results['use_producer_2']}")
    
    if results['best_match']:
        print(f"   Best match: {results['best_match']['product_name']}")
        print(f"   Price: ${results['best_match']['price_usd']:.2f}")

if __name__ == "__main__":
    # Test the SKU database
    print("🚀 Testing SKU Database...")
    initialize_sku_database()
    test_sku_database()
