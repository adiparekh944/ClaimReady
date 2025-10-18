#!/usr/bin/env python3
"""
Update SKU database with real CLIP embeddings from product images
"""

import os
import json
import numpy as np
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_real_embeddings(embeddings_dir: str = "real_clip_embeddings"):
    """Load real CLIP embeddings and metadata"""
    logger.info(f"Loading real CLIP embeddings from {embeddings_dir}...")
    
    # Load embeddings
    embeddings_file = os.path.join(embeddings_dir, "real_clip_embeddings.npy")
    embeddings = np.load(embeddings_file)
    logger.info(f"Loaded {embeddings.shape[0]} embeddings with {embeddings.shape[1]} dimensions")
    
    # Load metadata
    metadata_file = os.path.join(embeddings_dir, "real_clip_metadata.json")
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    logger.info(f"Loaded metadata for {len(metadata)} images")
    
    # Load image IDs
    image_ids_file = os.path.join(embeddings_dir, "image_ids.json")
    with open(image_ids_file, 'r') as f:
        image_ids = json.load(f)
    logger.info(f"Loaded {len(image_ids)} image IDs")
    
    return embeddings, metadata, image_ids

def load_sku_metadata(sku_file: str = "berkeley_sku_database/sku_metadata.json"):
    """Load existing SKU metadata"""
    logger.info(f"Loading SKU metadata from {sku_file}...")
    
    with open(sku_file, 'r') as f:
        sku_data = json.load(f)
    
    logger.info(f"Loaded {len(sku_data)} SKU records")
    return sku_data

def create_enhanced_sku_database(sku_data, real_embeddings, real_metadata, image_ids, output_dir: str = "enhanced_sku_database"):
    """Create enhanced SKU database with real CLIP embeddings"""
    logger.info(f"Creating enhanced SKU database with real embeddings...")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Match SKUs with real embeddings (first 100 SKUs get real embeddings)
    enhanced_skus = []
    enhanced_embeddings = []
    
    for i, sku in enumerate(sku_data):
        if i < len(real_embeddings):
            # Use real CLIP embedding
            sku['has_real_embedding'] = True
            sku['image_id'] = image_ids[i] if i < len(image_ids) else f"image_{i}"
            sku['embedding_source'] = 'real_clip'
            enhanced_embeddings.append(real_embeddings[i])
        else:
            # Use random embedding for remaining SKUs
            sku['has_real_embedding'] = False
            sku['embedding_source'] = 'random'
            random_embedding = np.random.randn(768).astype(np.float32)
            random_embedding = random_embedding / np.linalg.norm(random_embedding)
            enhanced_embeddings.append(random_embedding)
        
        enhanced_skus.append(sku)
    
    # Save enhanced SKU data
    sku_file = os.path.join(output_dir, "sku_metadata.json")
    with open(sku_file, 'w') as f:
        json.dump(enhanced_skus, f, indent=2)
    logger.info(f"Saved enhanced SKU metadata: {sku_file}")
    
    # Save enhanced embeddings
    embeddings_file = os.path.join(output_dir, "embeddings.npy")
    np.save(embeddings_file, np.array(enhanced_embeddings))
    logger.info(f"Saved enhanced embeddings: {embeddings_file}")
    
    # Save summary
    summary = {
        'total_skus': len(enhanced_skus),
        'embedding_dimension': 768,
        'real_embeddings': len(real_embeddings),
        'random_embeddings': len(enhanced_skus) - len(real_embeddings),
        'model_used': 'ViT-L/14',
        'created_at': str(np.datetime64('now'))
    }
    
    summary_file = os.path.join(output_dir, "summary.json")
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Saved summary: {summary_file}")
    
    logger.info(f"✅ Enhanced SKU database created!")
    logger.info(f"   Total SKUs: {summary['total_skus']}")
    logger.info(f"   Real embeddings: {summary['real_embeddings']}")
    logger.info(f"   Random embeddings: {summary['random_embeddings']}")
    logger.info(f"   Embedding dimension: {summary['embedding_dimension']}")

def main():
    """Main function"""
    logger.info("🚀 Creating Enhanced SKU Database with Real CLIP Embeddings")
    
    # Load real embeddings
    real_embeddings, real_metadata, image_ids = load_real_embeddings()
    
    # Load existing SKU data
    sku_data = load_sku_metadata()
    
    # Create enhanced database
    create_enhanced_sku_database(sku_data, real_embeddings, real_metadata, image_ids)
    
    logger.info("🎉 Enhanced SKU database creation complete!")

if __name__ == "__main__":
    main()
