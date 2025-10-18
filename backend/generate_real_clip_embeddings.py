#!/usr/bin/env python3
"""
Generate real CLIP embeddings from Berkeley Objects product images
This only needs to be run once to create the embedding database
"""

import os
import json
import numpy as np
import torch
import clip
from PIL import Image
from pathlib import Path
import logging
from tqdm import tqdm
import pickle

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CLIP config - using the more accurate model
CLIP_MODEL_NAME = "ViT-L/14"  # More accurate CLIP model (768-dim embeddings)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def load_clip_model():
    """Load CLIP model"""
    logger.info(f"Loading CLIP model {CLIP_MODEL_NAME} on {DEVICE}...")
    model, preprocess = clip.load(CLIP_MODEL_NAME, device=DEVICE)
    logger.info("CLIP model loaded successfully!")
    return model, preprocess

def get_image_embedding(image_path: str, model, preprocess) -> np.ndarray:
    """Generate CLIP embedding for a single image"""
    try:
        # Load and preprocess image
        image = Image.open(image_path).convert('RGB')
        image_input = preprocess(image).unsqueeze(0).to(DEVICE)
        
        # Get image features
        with torch.no_grad():
            image_features = model.encode_image(image_input)
            # Normalize features
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
        return image_features.cpu().numpy().flatten()
    except Exception as e:
        logger.error(f"Failed to process {image_path}: {e}")
        return None

def find_all_images(images_dir: str) -> list:
    """Find all product images in the dataset"""
    logger.info(f"Scanning for images in {images_dir}...")
    
    image_paths = []
    for root, dirs, files in os.walk(images_dir):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_paths.append(os.path.join(root, file))
    
    logger.info(f"Found {len(image_paths)} images")
    return image_paths

def load_sku_metadata(metadata_file: str) -> dict:
    """Load SKU metadata to match with images"""
    logger.info(f"Loading SKU metadata from {metadata_file}...")
    
    with open(metadata_file, 'r') as f:
        sku_data = json.load(f)
    
    # Create mapping from image_id to SKU data
    sku_map = {}
    for sku in sku_data:
        # Extract image_id from the SKU (assuming it's in the filename or metadata)
        sku_id = sku.get('sku_id', '')
        sku_map[sku_id] = sku
    
    logger.info(f"Loaded {len(sku_map)} SKU records")
    return sku_map

def generate_embeddings_for_images(image_paths: list, model, preprocess, output_dir: str, max_images: int = 1000):
    """Generate CLIP embeddings for all images"""
    logger.info(f"Generating CLIP embeddings for up to {max_images} images...")
    
    embeddings = []
    metadata = []
    image_ids = []
    
    # Process images in batches
    processed = 0
    for i, image_path in enumerate(tqdm(image_paths[:max_images], desc="Processing images")):
        if processed >= max_images:
            break
            
        # Generate embedding
        embedding = get_image_embedding(image_path, model, preprocess)
        
        if embedding is not None:
            embeddings.append(embedding)
            
            # Extract image ID from filename
            image_id = os.path.basename(image_path).split('.')[0]
            image_ids.append(image_id)
            
            # Create metadata entry
            metadata_entry = {
                'image_id': image_id,
                'image_path': image_path,
                'embedding_dim': len(embedding),
                'processed_at': str(np.datetime64('now'))
            }
            metadata.append(metadata_entry)
            
            processed += 1
            
            # Save progress every 100 images
            if processed % 100 == 0:
                logger.info(f"Processed {processed} images...")
                # Save intermediate results
                np.save(os.path.join(output_dir, f'embeddings_{processed}.npy'), np.array(embeddings))
                with open(os.path.join(output_dir, f'metadata_{processed}.json'), 'w') as f:
                    json.dump(metadata, f, indent=2)
    
    logger.info(f"Generated embeddings for {len(embeddings)} images")
    return np.array(embeddings), metadata, image_ids

def save_embeddings(embeddings: np.ndarray, metadata: list, image_ids: list, output_dir: str):
    """Save embeddings and metadata to disk"""
    logger.info(f"Saving embeddings to {output_dir}...")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Save embeddings
    embeddings_file = os.path.join(output_dir, 'real_clip_embeddings.npy')
    np.save(embeddings_file, embeddings)
    logger.info(f"Saved embeddings: {embeddings_file}")
    
    # Save metadata
    metadata_file = os.path.join(output_dir, 'real_clip_metadata.json')
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Saved metadata: {metadata_file}")
    
    # Save image IDs
    image_ids_file = os.path.join(output_dir, 'image_ids.json')
    with open(image_ids_file, 'w') as f:
        json.dump(image_ids, f, indent=2)
    logger.info(f"Saved image IDs: {image_ids_file}")
    
    # Save summary
    summary = {
        'total_images': len(embeddings),
        'embedding_dimension': embeddings.shape[1] if len(embeddings) > 0 else 0,
        'model_used': CLIP_MODEL_NAME,
        'device_used': DEVICE,
        'generated_at': str(np.datetime64('now'))
    }
    
    summary_file = os.path.join(output_dir, 'summary.json')
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Saved summary: {summary_file}")
    
    logger.info(f"✅ Real CLIP embeddings saved successfully!")
    logger.info(f"   Total images: {summary['total_images']}")
    logger.info(f"   Embedding dimension: {summary['embedding_dimension']}")
    logger.info(f"   Model: {summary['model_used']}")

def main():
    """Main function"""
    logger.info("🚀 Generating Real CLIP Embeddings from Berkeley Objects Images")
    
    # Paths
    images_dir = "berkeley_images/images/small"
    sku_metadata_file = "berkeley_sku_database/sku_metadata.json"
    output_dir = "real_clip_embeddings"
    
    # Check if images directory exists
    if not os.path.exists(images_dir):
        logger.error(f"Images directory not found: {images_dir}")
        return
    
    # Load CLIP model
    model, preprocess = load_clip_model()
    
    # Find all images
    image_paths = find_all_images(images_dir)
    
    if not image_paths:
        logger.error("No images found!")
        return
    
    # Generate embeddings
    embeddings, metadata, image_ids = generate_embeddings_for_images(
        image_paths, model, preprocess, output_dir, max_images=1000  # Generate embeddings for ALL 1000 SKUs
    )
    
    # Save results
    save_embeddings(embeddings, metadata, image_ids, output_dir)
    
    logger.info("🎉 Real CLIP embeddings generation complete!")

if __name__ == "__main__":
    main()
