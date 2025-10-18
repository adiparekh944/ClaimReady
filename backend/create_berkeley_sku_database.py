#!/usr/bin/env python3
"""
Create a real SKU database from Berkeley Objects dataset
"""

import json
import gzip
import os
import numpy as np
import pickle
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_berkeley_listings(listings_dir: str = "/Users/soham/ClaimReady/berkeley_dataset/listings/metadata"):
    """Load all Berkeley Objects listings from JSON files"""
    logger.info(f"Loading Berkeley Objects listings from {listings_dir}")
    
    all_listings = []
    listings_files = list(Path(listings_dir).glob("listings_*.json.gz"))
    
    logger.info(f"Found {len(listings_files)} listing files")
    
    for i, file_path in enumerate(listings_files):
        logger.info(f"Processing file {i+1}/{len(listings_files)}: {file_path.name}")
        
        try:
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                listings = []
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            listing = json.loads(line)
                            listings.append(listing)
                        except json.JSONDecodeError as e:
                            logger.warning(f"  Skipping invalid JSON line: {e}")
                            continue
                all_listings.extend(listings)
                logger.info(f"  Loaded {len(listings)} listings from {file_path.name}")
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            continue
    
    logger.info(f"Total listings loaded: {len(all_listings)}")
    return all_listings

def create_sku_database(listings, max_skus: int = 1000):
    """Create SKU database from Berkeley Objects listings"""
    logger.info(f"Creating SKU database with max {max_skus} items")
    
    sku_data = []
    embeddings = []
    
    # Filter and process listings
    processed = 0
    for listing in listings:
        if processed >= max_skus:
            break
            
        try:
            # Extract relevant fields from Berkeley Objects format
            sku_id = listing.get('item_id', f'berkeley_{processed}')
            
            # Extract title from language-specific array
            title = 'Unknown Product'
            if 'item_name' in listing and listing['item_name']:
                title = listing['item_name'][0].get('value', 'Unknown Product')
            
            # Extract brand from language-specific array
            brand = 'Unknown Brand'
            if 'brand' in listing and listing['brand']:
                brand = listing['brand'][0].get('value', 'Unknown Brand')
            
            # Extract category from product_type
            category = listing.get('product_type', ['Unknown Category'])
            if isinstance(category, list):
                category = category[0] if category else 'Unknown Category'
            
            # For now, use a random price since Berkeley Objects doesn't have prices
            # In production, you'd need to get prices from another source
            price = np.random.uniform(10.0, 500.0)  # Random price between $10-$500
                
            # Create SKU entry
            sku_entry = {
                'sku_id': sku_id,
                'product_name': title,
                'brand': brand,
                'price_usd': float(price),
                'category': category,
                'source': 'berkeley_objects'
            }
            
            # Generate random CLIP-like embedding (768 dimensions for ViT-L/14)
            # TODO: In production, extract actual product images and generate real CLIP embeddings
            embedding = np.random.randn(768).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)  # Normalize
            
            sku_data.append(sku_entry)
            embeddings.append(embedding)
            processed += 1
            
            if processed % 100 == 0:
                logger.info(f"Processed {processed} SKUs...")
                
        except Exception as e:
            logger.error(f"Error processing listing: {e}")
            continue
    
    logger.info(f"Created SKU database with {len(sku_data)} items")
    return sku_data, np.array(embeddings)

def save_sku_database(sku_data, embeddings, output_dir: str = "berkeley_sku_database"):
    """Save SKU database to disk"""
    logger.info(f"Saving SKU database to {output_dir}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Save metadata
    with open(f"{output_dir}/sku_metadata.json", 'w') as f:
        json.dump(sku_data, f, indent=2)
    
    # Save embeddings
    with open(f"{output_dir}/embeddings.npy", 'wb') as f:
        np.save(f, embeddings)
    
    # Save summary
    summary = {
        'total_skus': len(sku_data),
        'embedding_dimension': embeddings.shape[1],
        'price_range': {
            'min': min(sku['price_usd'] for sku in sku_data),
            'max': max(sku['price_usd'] for sku in sku_data),
            'mean': np.mean([sku['price_usd'] for sku in sku_data])
        },
        'categories': list(set(sku['category'] for sku in sku_data if isinstance(sku['category'], str))),
        'brands': list(set(sku['brand'] for sku in sku_data if isinstance(sku['brand'], str)))
    }
    
    with open(f"{output_dir}/summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"SKU database saved successfully!")
    logger.info(f"  Total SKUs: {summary['total_skus']}")
    logger.info(f"  Embedding dimension: {summary['embedding_dimension']}")
    logger.info(f"  Price range: ${summary['price_range']['min']:.2f} - ${summary['price_range']['max']:.2f}")
    logger.info(f"  Categories: {len(summary['categories'])}")
    logger.info(f"  Brands: {len(summary['brands'])}")

def main():
    """Main function"""
    logger.info("🚀 Creating Berkeley Objects SKU Database")
    
    # Load listings
    listings = load_berkeley_listings()
    
    if not listings:
        logger.error("No listings loaded. Exiting.")
        return
    
    # Create SKU database (limit to 1000 for now)
    sku_data, embeddings = create_sku_database(listings, max_skus=1000)
    
    if not sku_data:
        logger.error("No SKU data created. Exiting.")
        return
    
    # Save database
    save_sku_database(sku_data, embeddings)
    
    logger.info("✅ Berkeley Objects SKU database creation complete!")

if __name__ == "__main__":
    main()
