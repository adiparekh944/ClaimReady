# === SIMPLE SKU DATABASE (No FAISS) ===
# For testing SKU matching without external dependencies

import os
import json
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class SimpleSKUDatabase:
    def __init__(self, dataset_path: str = "../enhanced_sku_database"):
        self.dataset_path = dataset_path
        self.sku_metadata = []
        self.embeddings = None
        self.is_loaded = False
        
    def load_dataset(self):
        """Load test SKU dataset"""
        try:
            print("🔄 Loading test SKU dataset...")
            
            # Create test data if it doesn't exist
            if not os.path.exists(self.dataset_path):
                self._create_test_data()
            
            # Load metadata
            metadata_file = os.path.join(self.dataset_path, "sku_metadata.json")
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    self.sku_metadata = json.load(f)
                print(f"✅ Loaded {len(self.sku_metadata)} SKU records")
            else:
                print("❌ Metadata file not found")
                return False
            
            # Load embeddings
            embeddings_file = os.path.join(self.dataset_path, "embeddings.npy")
            if os.path.exists(embeddings_file):
                self.embeddings = np.load(embeddings_file)
                print(f"✅ Loaded {self.embeddings.shape[0]} embeddings")
            else:
                print("❌ Embeddings file not found")
                return False
            
            self.is_loaded = True
            print("🎉 Simple SKU database loaded successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            return False
    
    def _create_test_data(self):
        """Create test SKU data"""
        print("🎲 Creating test SKU data...")
        
        os.makedirs(self.dataset_path, exist_ok=True)
        
        # Sample furniture SKUs
        test_skus = [
            {
                "sku_id": "IKEA_HEMNES_001",
                "product_name": "IKEA Hemnes 3-Drawer Chest",
                "brand": "IKEA",
                "price_usd": 149.99,
                "category": "Furniture",
                "description": "White 3-drawer chest with solid wood construction"
            },
            {
                "sku_id": "ASHLEY_DINING_002", 
                "product_name": "Ashley Furniture Dining Table",
                "brand": "Ashley Furniture",
                "price_usd": 299.99,
                "category": "Furniture",
                "description": "Oak dining table seats 6 people"
            },
            {
                "sku_id": "WEST_ELM_SOFA_003",
                "product_name": "West Elm Modern Sofa",
                "brand": "West Elm", 
                "price_usd": 899.99,
                "category": "Furniture",
                "description": "Gray fabric 3-seat sofa with wooden legs"
            },
            {
                "sku_id": "TARGET_LAMP_004",
                "product_name": "Target Table Lamp",
                "brand": "Target",
                "price_usd": 29.99,
                "category": "Lighting",
                "description": "White ceramic table lamp with fabric shade"
            },
            {
                "sku_id": "MACY_BED_005",
                "product_name": "Macy's Queen Bed Frame",
                "brand": "Macy's",
                "price_usd": 399.99,
                "category": "Furniture", 
                "description": "Upholstered queen bed frame in navy blue"
            },
            {
                "sku_id": "WAYFAIR_CHAIR_006",
                "product_name": "Wayfair Accent Chair",
                "brand": "Wayfair",
                "price_usd": 199.99,
                "category": "Furniture",
                "description": "Velvet accent chair in emerald green"
            },
            {
                "sku_id": "AMAZON_DESK_007",
                "product_name": "Amazon Basics Computer Desk",
                "brand": "Amazon Basics",
                "price_usd": 79.99,
                "category": "Furniture",
                "description": "Simple white computer desk with drawer"
            },
            {
                "sku_id": "CB2_MIRROR_008",
                "product_name": "CB2 Wall Mirror",
                "brand": "CB2",
                "price_usd": 149.99,
                "category": "Home Decor",
                "description": "Round gold-framed wall mirror 24 inches"
            },
            {
                "sku_id": "POTTERY_BARN_RUG_009",
                "product_name": "Pottery Barn Area Rug",
                "brand": "Pottery Barn",
                "price_usd": 249.99,
                "category": "Home Decor",
                "description": "Wool area rug 5x8 feet in neutral colors"
            },
            {
                "sku_id": "COSTCO_TV_010",
                "product_name": "Costco 55-inch TV",
                "brand": "Samsung",
                "price_usd": 499.99,
                "category": "Electronics",
                "description": "55-inch 4K Smart TV with HDR"
            }
        ]
        
        # Generate random embeddings (768-dim for ViT-L/14)
        np.random.seed(42)
        embeddings = np.random.rand(len(test_skus), 768).astype('float32')
        
        # Save metadata
        metadata_file = os.path.join(self.dataset_path, "metadata.json")
        with open(metadata_file, 'w') as f:
            json.dump(test_skus, f, indent=2)
        
        # Save embeddings
        embeddings_file = os.path.join(self.dataset_path, "embeddings.npy")
        np.save(embeddings_file, embeddings)
        
        print(f"✅ Created test data with {len(test_skus)} SKUs")
    
    def search_sku(self, item_embedding: np.ndarray, top_k: int = 3, confidence_threshold: float = 0.7) -> Dict:
        """
        Search for top K SKU matches using simple cosine similarity
        """
        if not self.is_loaded or self.embeddings is None:
            return {
                'matches': [],
                'best_match': None,
                'confidence': 0.0,
                'use_producer_2': True
            }
        
        try:
            # Normalize query embedding
            query_norm = item_embedding / np.linalg.norm(item_embedding)
            
            # Calculate cosine similarity with all SKUs
            similarities = []
            for i, sku_embedding in enumerate(self.embeddings):
                sku_norm = sku_embedding / np.linalg.norm(sku_embedding)
                similarity = np.dot(query_norm, sku_norm)
                similarities.append((similarity, i))
            
            # Sort by similarity (highest first)
            similarities.sort(reverse=True)
            
            # Get top K matches
            matches = []
            for i, (similarity, idx) in enumerate(similarities[:top_k]):
                if idx < len(self.sku_metadata):
                    sku_data = self.sku_metadata[idx]
                    match = {
                        'rank': i + 1,
                        'sku_id': sku_data.get('sku_id', f'unknown_{idx}'),
                        'product_name': sku_data.get('product_name', 'Unknown Product'),
                        'brand': sku_data.get('brand', 'Unknown Brand'),
                        'price_usd': float(sku_data.get('price_usd', 0.0)),
                        'category': sku_data.get('category', 'Unknown'),
                        'confidence': float(similarity),
                        'description': sku_data.get('description', 'No description available')
                    }
                    matches.append(match)
            
            # Determine best match and routing decision
            best_match = matches[0] if matches else None
            best_confidence = float(best_match['confidence']) if best_match else 0.0
            
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
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        if not self.is_loaded:
            return {'status': 'not_loaded'}
        
        return {
            'status': 'loaded',
            'total_skus': len(self.sku_metadata),
            'total_embeddings': len(self.embeddings) if self.embeddings is not None else 0,
            'embedding_dimension': self.embeddings.shape[1] if self.embeddings is not None else 0
        }

# Global SKU database instance
sku_db = SimpleSKUDatabase()

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
    
    # Create a dummy 768-dim embedding
    dummy_embedding = np.random.rand(768).astype('float32')
    
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
    print("🚀 Testing Simple SKU Database...")
    initialize_sku_database()
    test_sku_database()
