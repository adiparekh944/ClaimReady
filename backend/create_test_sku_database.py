#!/usr/bin/env python3
"""
Create a test SKU database with sample furniture data
This allows us to test the SKU matching system without downloading 50GB
"""

import os
import json
import numpy as np
import faiss
from sku_database import SKUDatabase

def create_test_sku_database():
    """Create a test SKU database with sample furniture data"""
    
    # Create test dataset directory
    os.makedirs("test_sku_database", exist_ok=True)
    
    # Sample furniture SKUs (realistic data)
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
    
    # Generate random CLIP embeddings (512-dim) for each SKU
    print("🎲 Generating test CLIP embeddings...")
    np.random.seed(42)  # For reproducible results
    embeddings = np.random.rand(len(test_skus), 512).astype('float32')
    
    # Normalize embeddings (like real CLIP embeddings)
    faiss.normalize_L2(embeddings)
    
    # Save metadata
    metadata_file = os.path.join("test_sku_database", "metadata.json")
    with open(metadata_file, 'w') as f:
        json.dump(test_skus, f, indent=2)
    print(f"✅ Saved {len(test_skus)} SKU records to {metadata_file}")
    
    # Save embeddings
    embeddings_file = os.path.join("test_sku_database", "embeddings.npy")
    np.save(embeddings_file, embeddings)
    print(f"✅ Saved embeddings to {embeddings_file}")
    
    # Test the database
    print("\n🧪 Testing the SKU database...")
    db = SKUDatabase("test_sku_database")
    if db.load_dataset():
        print("✅ Test database loaded successfully!")
        
        # Test search with a random query
        test_query = np.random.rand(512).astype('float32')
        results = db.search_sku(test_query, top_k=3)
        
        print(f"\n📊 Search Results:")
        print(f"   Total matches: {len(results['matches'])}")
        print(f"   Best confidence: {results['confidence']:.3f}")
        print(f"   Use Producer 2: {results['use_producer_2']}")
        
        print(f"\n🏆 Top 3 SKU Matches:")
        for i, match in enumerate(results['matches'][:3]):
            print(f"   {i+1}. {match['product_name']} - ${match['price_usd']:.2f} (conf: {match['confidence']:.3f})")
        
        return True
    else:
        print("❌ Failed to load test database")
        return False

if __name__ == "__main__":
    print("🚀 Creating Test SKU Database...")
    success = create_test_sku_database()
    if success:
        print("\n🎉 Test database created successfully!")
        print("   You can now test SKU matching with real images!")
    else:
        print("\n💥 Failed to create test database")
