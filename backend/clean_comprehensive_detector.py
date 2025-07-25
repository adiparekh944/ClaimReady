import time
import os
import cv2
import numpy as np
import torch
from ultralytics import YOLO
from datetime import datetime
import json

# ================= CONFIGURATION =================
YOLO_MODEL_PATH = "yolo11n-seg.pt"

# Optimized parameters for enhanced image detection with furniture focus
SCALES = [640, 1280, 1920]  # Added larger scale for furniture
CONF_THRESHOLDS = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.15, 0.2]  # Much lower thresholds for furniture
IOU_NMS = 0.2  # Lower NMS for more detections
MASK_IOU_THRESH = 0.2  # Lower threshold for duplicate removal
MIN_MASK_AREA = 10  # Smaller minimum for furniture details
MAX_MASK_AREA = 150000  # Larger maximum for furniture

# Output directories
OUTPUT_DIR = "enhanced_detection_outputs"
MASKS_DIR = "enhanced_detection_masks"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MASKS_DIR, exist_ok=True)

# Load model once
yolo_model = YOLO(YOLO_MODEL_PATH)

# ================= HELPERS =================

def get_timestamp():
    """Get current timestamp for unique filenames"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def mask_iou(mask1, mask2):
    """Calculate IoU between two masks"""
    if mask1 is None or mask2 is None:
        return 0.0
    intersection = np.logical_and(mask1, mask2)
    union = np.logical_or(mask1, mask2)
    if np.sum(union) == 0:
        return 0.0
    return np.sum(intersection) / np.sum(union)

def mask_area(mask):
    """Calculate area of mask"""
    if mask is None:
        return 0
    return np.sum(mask > 0)

def mask_contains(mask1, mask2, threshold=0.6):
    """Check if mask1 contains mask2"""
    if mask1 is None or mask2 is None:
        return False
    intersection = np.logical_and(mask1, mask2)
    if np.sum(mask2) == 0:
        return False
    return np.sum(intersection) / np.sum(mask2) > threshold

def create_furniture_specific_enhancements(img):
    """
    Specialized image enhancements specifically designed for furniture detection
    
    These enhancements focus on:
    1. Edge detection for furniture boundaries
    2. Contrast enhancement for wooden surfaces
    3. Shadow removal for better furniture visibility
    4. Texture enhancement for furniture details
    """
    furniture_enhanced_images = []
    
    # 1. Edge-preserving bilateral filter for furniture
    bilateral = cv2.bilateralFilter(img, 9, 75, 75)
    furniture_enhanced_images.append(("bilateral_furniture", bilateral))
    
    # 2. Gamma correction to brighten dark furniture areas
    gamma = 0.5  # More aggressive brightening
    gamma_corrected = np.power(img/255.0, gamma) * 255.0
    gamma_corrected = gamma_corrected.astype(np.uint8)
    furniture_enhanced_images.append(("gamma_furniture", gamma_corrected))
    
    # 3. CLAHE with higher clip limit for furniture contrast
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(8,8))  # Higher clip limit
    lab[:,:,0] = clahe.apply(lab[:,:,0])
    clahe_furniture = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    furniture_enhanced_images.append(("clahe_furniture", clahe_furniture))
    
    # 4. Unsharp masking for furniture detail enhancement
    gaussian = cv2.GaussianBlur(img, (0, 0), 3.0)
    unsharp_mask = cv2.addWeighted(img, 2.0, gaussian, -1.0, 0)  # More aggressive
    furniture_enhanced_images.append(("unsharp_furniture", unsharp_mask))
    
    # 5. Multi-scale morphological operations for furniture structure
    kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    kernel_medium = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    
    # Opening to remove noise while preserving furniture structure
    morph_opened = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel_small)
    morph_opened = cv2.morphologyEx(morph_opened, cv2.MORPH_CLOSE, kernel_medium)
    furniture_enhanced_images.append(("morphological_furniture", morph_opened))
    
    # 6. Adaptive histogram equalization for furniture visibility
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    adaptive_eq = cv2.equalizeHist(gray)
    adaptive_eq_col = cv2.cvtColor(adaptive_eq, cv2.COLOR_GRAY2BGR)
    furniture_enhanced_images.append(("adaptive_hist_furniture", adaptive_eq_col))
    
    # 7. High-pass filtering for furniture edges
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    high_pass = cv2.filter2D(img, -1, kernel)
    furniture_enhanced_images.append(("high_pass_furniture", high_pass))
    
    return furniture_enhanced_images

def detect_furniture_specific_objects(img, model, existing_detections):
    """
    Specialized detection pass for furniture objects using very low confidence thresholds
    and furniture-specific image enhancements
    """
    print("Running specialized furniture detection pass...")
    furniture_detections = []
    
    # Create mask of existing detections to avoid overlap
    img_height, img_width = img.shape[:2]
    existing_mask = np.zeros((img_height, img_width), dtype=bool)
    
    for det in existing_detections:
        if det['mask'] is not None:
            existing_mask = np.logical_or(existing_mask, det['mask'] > 0)
    
    # Create furniture-specific enhancements
    furniture_enhanced_images = create_furniture_specific_enhancements(img)
    print(f"Created {len(furniture_enhanced_images)} furniture-specific enhancements")
    
    # Very low confidence thresholds for furniture
    furniture_conf_thresholds = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05]
    
    for enhancement_name, enhanced_img in furniture_enhanced_images:
        print(f"Processing furniture enhancement: {enhancement_name}")
        
        for scale in [1280, 1920]:  # Focus on larger scales for furniture
            for conf_thresh in furniture_conf_thresholds:
                results = model.predict(
                    enhanced_img,
                    imgsz=scale,
                    conf=conf_thresh,
                    iou=0.1,  # Very low NMS for furniture
                    verbose=False,
                    max_det=1000
                )
                
                for result in results:
                    masks, scores, boxes = process_masks(result, img.shape[:2])
                    
                    for mask, score, box in zip(masks, scores, boxes):
                        area = mask_area(mask)
                        
                        # Focus on larger objects that might be furniture
                        if area > 1000:  # Reasonable furniture size
                            # Check if this area is mostly uncovered by existing detections
                            overlap_ratio = np.sum(np.logical_and(mask > 0, existing_mask)) / np.sum(mask > 0)
                            
                            if overlap_ratio < 0.5:  # Less than 50% overlap with existing
                                # Check if it has furniture-like characteristics
                                box_width = box[2] - box[0]
                                box_height = box[3] - box[1]
                                aspect_ratio = box_width / box_height if box_height > 0 else 1
                                
                                # Furniture is often rectangular with reasonable aspect ratios
                                if 0.2 <= aspect_ratio <= 5.0:
                                    detection = {
                                        'mask': mask,
                                        'score': max(score, 0.01),  # Boost very low scores slightly
                                        'box': box,
                                        'scale': scale,
                                        'conf_thresh': conf_thresh,
                                        'source': f'furniture_{enhancement_name}'
                                    }
                                    furniture_detections.append(detection)
    
    print(f"Found {len(furniture_detections)} potential furniture objects")
    return furniture_detections

def create_sophisticated_enhancements(img):
    """
    Sophisticated image enhancement pipeline to make objects more detectable by YOLO
    
    This pipeline uses advanced computer vision techniques:
    1. Multi-scale edge preservation
    2. Adaptive histogram equalization
    3. Frequency domain enhancement
    4. Spatial domain filtering
    5. Color space transformations
    6. Contrast enhancement with noise reduction
    """
    enhanced_images = []
    
    # Original image
    enhanced_images.append(("original", img))
    
    # 1. CLAHE (Contrast Limited Adaptive Histogram Equalization)
    # This is one of the most effective techniques for object detection
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    lab[:,:,0] = clahe.apply(lab[:,:,0])
    clahe_enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    enhanced_images.append(("clahe", clahe_enhanced))
    
    # 2. Multi-scale edge enhancement using Laplacian pyramids
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Create Laplacian pyramid for multi-scale edge detection
    kernel_sizes = [3, 5, 7]
    edge_enhanced = np.zeros_like(gray)
    
    for kernel_size in kernel_sizes:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=kernel_size)
        laplacian = np.uint8(np.absolute(laplacian))
        edge_enhanced = cv2.add(edge_enhanced, laplacian)
    
    # Normalize and convert to BGR
    edge_enhanced = cv2.normalize(edge_enhanced, None, 0, 255, cv2.NORM_MINMAX)
    edge_enhanced_col = cv2.cvtColor(edge_enhanced, cv2.COLOR_GRAY2BGR)
    
    # Blend with original for edge-enhanced version
    edge_blended = cv2.addWeighted(img, 0.7, edge_enhanced_col, 0.3, 0)
    enhanced_images.append(("edge_enhanced", edge_blended))
    
    # 3. Frequency domain enhancement using FFT
    # Convert to grayscale for FFT
    gray_float = np.float32(gray)
    
    # Apply FFT
    f_transform = cv2.dft(gray_float, flags=cv2.DFT_COMPLEX_OUTPUT)
    f_shift = np.fft.fftshift(f_transform)
    
    # Create high-pass filter to enhance edges
    rows, cols = gray.shape
    crow, ccol = rows//2, cols//2
    mask = np.ones((rows, cols, 2), np.uint8)
    r = 30
    center = [crow, ccol]
    x, y = np.ogrid[:rows, :cols]
    mask_area = (x - center[0])**2 + (y - center[1])**2 <= r*r
    mask[mask_area] = 0
    
    # Apply filter
    f_shift_filtered = f_shift * mask
    f_ishift = np.fft.ifftshift(f_shift_filtered)
    img_back = cv2.idft(f_ishift)
    img_back = cv2.magnitude(img_back[:,:,0], img_back[:,:,1])
    
    # Normalize and convert to BGR
    img_back = cv2.normalize(img_back, None, 0, 255, cv2.NORM_MINMAX)
    fft_enhanced = cv2.cvtColor(np.uint8(img_back), cv2.COLOR_GRAY2BGR)
    enhanced_images.append(("fft_enhanced", fft_enhanced))
    
    # 4. Bilateral filtering for edge-preserving smoothing
    bilateral = cv2.bilateralFilter(img, 9, 75, 75)
    enhanced_images.append(("bilateral", bilateral))
    
    # 5. Gamma correction for better visibility in dark areas
    gamma = 0.6  # Brighten dark areas
    gamma_corrected = np.power(img/255.0, gamma) * 255.0
    gamma_corrected = gamma_corrected.astype(np.uint8)
    enhanced_images.append(("gamma_corrected", gamma_corrected))
    
    # 6. Multi-scale morphological operations for object enhancement
    # Create structuring elements of different sizes
    kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    kernel_medium = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    
    # Apply morphological operations
    morph_enhanced = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel_small)
    morph_enhanced = cv2.morphologyEx(morph_enhanced, cv2.MORPH_CLOSE, kernel_medium)
    enhanced_images.append(("morphological", morph_enhanced))
    
    # 7. Adaptive thresholding for object separation
    gray_blur = cv2.GaussianBlur(gray, (5, 5), 0)
    adaptive_thresh = cv2.adaptiveThreshold(gray_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    adaptive_col = cv2.cvtColor(adaptive_thresh, cv2.COLOR_GRAY2BGR)
    
    # Blend with original
    adaptive_blended = cv2.addWeighted(img, 0.8, adaptive_col, 0.2, 0)
    enhanced_images.append(("adaptive_threshold", adaptive_blended))
    
    # 8. Color space transformations for better object separation
    # HSV transformation
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # Enhance saturation
    hsv[:,:,1] = cv2.multiply(hsv[:,:,1], 1.3)
    hsv[:,:,1] = np.clip(hsv[:,:,1], 0, 255)
    hsv_enhanced = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    enhanced_images.append(("hsv_enhanced", hsv_enhanced))
    
    # 9. Unsharp masking for detail enhancement
    gaussian = cv2.GaussianBlur(img, (0, 0), 2.0)
    unsharp_mask = cv2.addWeighted(img, 1.5, gaussian, -0.5, 0)
    enhanced_images.append(("unsharp_mask", unsharp_mask))
    
    # 10. Multi-scale contrast enhancement
    # Apply different contrast enhancements and blend
    contrast1 = cv2.convertScaleAbs(img, alpha=1.5, beta=10)
    contrast2 = cv2.convertScaleAbs(img, alpha=2.0, beta=20)
    contrast_blended = cv2.addWeighted(contrast1, 0.6, contrast2, 0.4, 0)
    enhanced_images.append(("contrast_enhanced", contrast_blended))
    
    return enhanced_images

def process_masks(results, img_shape):
    """Extract and process masks from YOLO results"""
    masks = []
    scores = []
    boxes = []
    
    if results.masks is not None:
        for i, mask_tensor in enumerate(results.masks.data):
            # Convert tensor to numpy and resize to original image size
            mask = mask_tensor.cpu().numpy()
            mask = cv2.resize(mask, (img_shape[1], img_shape[0]))
            mask = (mask > 0.01).astype(np.uint8)  # Very low threshold
            
            area = mask_area(mask)
            
            # Filter by area constraints
            if MIN_MASK_AREA <= area <= MAX_MASK_AREA:
                masks.append(mask)
                
                # Get corresponding score and box
                if results.boxes is not None and i < len(results.boxes):
                    score = float(results.boxes[i].conf[0])
                    box = results.boxes[i].xyxy[0].cpu().numpy()
                else:
                    score = 1.0
                    box = [0, 0, img_shape[1], img_shape[0]]
                
                scores.append(score)
                boxes.append(box)
    
    return masks, scores, boxes

def simple_duplicate_removal(detections):
    """
    Simple and fast duplicate removal optimized for enhanced image detections
    
    Since we're using sophisticated image enhancements, YOLO should detect
    objects with higher confidence and fewer duplicates naturally.
    """
    if not detections:
        return []
    
    if len(detections) == 1:
        return detections

    # Sort by confidence (high to low)
    detections.sort(key=lambda x: x['score'], reverse=True)
    
    final_detections = []
    
    for det in detections:
        should_keep = True
        
        # Check against already accepted detections
        for accepted_det in final_detections:
            iou = mask_iou(det['mask'], accepted_det['mask'])
            
            # If high overlap, keep the one with higher confidence
            if iou > MASK_IOU_THRESH:
                if det['score'] > accepted_det['score'] * 1.1:  # 10% better
                    # Replace the accepted detection
                    final_detections.remove(accepted_det)
                    break
                else:
                    should_keep = False
                    break
        
        if should_keep:
            final_detections.append(det)
    
    print(f"Simple duplicate removal: {len(detections)} -> {len(final_detections)} detections")
    return final_detections

def simple_quality_filtering(detections, img_shape):
    """Simple quality filtering optimized for enhanced image detections with furniture focus"""
    if not detections:
        return detections
    
    filtered_detections = []
    
    for det in detections:
        score = det['score']
        area = mask_area(det['mask'])
        source = det.get('source', 'unknown')
        
        # Keep high-confidence detections
        if score > 0.3:
            filtered_detections.append(det)
            continue
        
        # Keep medium-confidence detections with reasonable area
        if 0.1 <= score <= 0.3 and 50 <= area <= 100000:
            filtered_detections.append(det)
            continue
        
        # Keep large objects even with lower confidence (they're likely real furniture)
        if area > 3000 and score > 0.02:  # Lowered threshold for furniture
            filtered_detections.append(det)
            continue
        
        # Keep furniture-specific detections with very low confidence
        if 'furniture' in source and area > 1000 and score > 0.01:
            filtered_detections.append(det)
            continue
        
        # Keep very large objects (likely furniture) with any confidence
        if area > 10000 and score > 0.005:
            filtered_detections.append(det)
            continue
    
    return filtered_detections

def enhanced_comprehensive_detection(img, model):
    """Enhanced comprehensive detection using sophisticated image transformations"""
    all_detections = []
    
    # Create sophisticated enhancements
    enhanced_images = create_sophisticated_enhancements(img)
    print(f"Created {len(enhanced_images)} sophisticated image enhancements")
    
    for enhancement_name, enhanced_img in enhanced_images:
        print(f"Processing {enhancement_name} enhancement...")
        
        for scale in SCALES:
            for conf_thresh in CONF_THRESHOLDS:
                results = model.predict(
                    enhanced_img, 
                    imgsz=scale, 
                    conf=conf_thresh, 
                    iou=IOU_NMS, 
                    verbose=False,
                    max_det=200  # Reduced for speed
                )
                
                for result in results:
                    masks, scores, boxes = process_masks(result, img.shape[:2])
                    
                    for mask, score, box in zip(masks, scores, boxes):
                            detection = {
                                'mask': mask,
                                'score': score,
                                'box': box,
                                'scale': scale,
                                'conf_thresh': conf_thresh,
                                'source': enhancement_name
                            }
                            all_detections.append(detection)
    
    print(f"Total detections before filtering: {len(all_detections)}")
    return all_detections

def visualize_detections(img, detections, title, save_path):
    """Visualize detections and save to disk"""
    vis = img.copy()
    
    # Create mask overlay
    mask_overlay = np.zeros_like(img)
    
    # Generate colors for each detection
    colors = []
    for i in range(len(detections)):
        hue = int(180 * i / max(1, len(detections)))
        color = cv2.cvtColor(np.uint8([[[hue, 255, 255]]]), cv2.COLOR_HSV2BGR)[0][0]
        colors.append(tuple(int(c) for c in color))
    
    for i, det in enumerate(detections):
        mask = det['mask']
        score = det['score']
        box = det['box']
        
        if mask is not None:
            # Use different color for each detection
            color = colors[i % len(colors)] if i < len(colors) else (255, 255, 255)
            
            # Apply colored mask
            mask_overlay[mask > 0] = color
            
            # Draw bounding box
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
            
            # Add score text
            cv2.putText(vis, f'{score:.3f}', (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.putText(vis, f'{score:.3f}', (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Blend mask overlay with original image
    if np.any(mask_overlay):
        vis = cv2.addWeighted(vis, 0.4, mask_overlay, 0.6, 0)
    
    # Save image
    cv2.imwrite(save_path, vis)
    print(f"Saved visualization: {save_path}")

def save_detection_results(detections, output_dir, base_filename):
    """Save detection results and metadata"""
    timestamp = get_timestamp()
    
    # Save individual masks
    for i, det in enumerate(detections):
        mask = det['mask']
        score = det['score']
        box = det['box']
        
        if mask is not None:
            mask_filename = f"{base_filename}_mask_{i+1:03d}_score_{score:.3f}.png"
            mask_path = os.path.join(output_dir, mask_filename)
            cv2.imwrite(mask_path, (mask * 255).astype(np.uint8))
    
    # Save metadata
    metadata = {
        'timestamp': timestamp,
        'total_detections': len(detections),
        'detections': []
    }
    
    for i, det in enumerate(detections):
        metadata['detections'].append({
            'id': i + 1,
            'score': float(det['score']),
            'area': int(mask_area(det['mask'])),
            'box': [float(x) for x in (det['box'].tolist() if hasattr(det['box'], 'tolist') else det['box'])],
            'scale': det.get('scale', 0),
            'conf_thresh': det.get('conf_thresh', 0),
            'source': det.get('source', 'unknown')
        })
    
    metadata_path = os.path.join(output_dir, f"{base_filename}_metadata_{timestamp}.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Saved metadata: {metadata_path}")

def enhanced_comprehensive_detect_objects(img, model):
    """Main enhanced comprehensive detection function using sophisticated image transformations"""
    print("Starting enhanced comprehensive object detection...")
    print("Using sophisticated image transformations to improve YOLO detection...")
    
    # Get all detections with enhanced parameters
    all_detections = enhanced_comprehensive_detection(img, model)
    
    # Apply simple duplicate removal
    print("Applying simple duplicate removal...")
    unique_detections = simple_duplicate_removal(all_detections)
    print(f"After duplicate removal: {len(unique_detections)} detections")
    
    # Add specialized furniture detection pass
    print("Running specialized furniture detection...")
    furniture_detections = detect_furniture_specific_objects(img, model, unique_detections)
    if furniture_detections:
        unique_detections.extend(furniture_detections)
        print(f"After furniture detection: {len(unique_detections)} detections")
        
        # Run duplicate removal again to handle any overlaps
        unique_detections = simple_duplicate_removal(unique_detections)
        print(f"After final duplicate removal: {len(unique_detections)} detections")
    
    # Apply simple quality filtering
    print("Applying simple quality filtering...")
    final_detections = simple_quality_filtering(unique_detections, img.shape[:2])
    print(f"After quality filtering: {len(final_detections)} detections")
    
    # Sort by score
    final_detections.sort(key=lambda x: x['score'], reverse=True)
    
    return final_detections

def analyze_detection_quality(detections):
    """Analyze detection quality"""
    print("\n=== ENHANCED COMPREHENSIVE DETECTION QUALITY ANALYSIS ===")
    print(f"Detected objects: {len(detections)}")
    
    # Analyze score distribution
    scores = [det['score'] for det in detections]
    areas = [mask_area(det['mask']) for det in detections]
    
    print(f"Score range: {min(scores):.3f} - {max(scores):.3f}")
    print(f"Area range: {min(areas)} - {max(areas)} pixels")
    
    # Count high-confidence detections
    high_conf = [d for d in detections if d['score'] > 0.5]
    medium_conf = [d for d in detections if 0.2 <= d['score'] <= 0.5]
    low_conf = [d for d in detections if d['score'] < 0.2]
    
    print(f"High confidence (>0.5): {len(high_conf)}")
    print(f"Medium confidence (0.2-0.5): {len(medium_conf)}")
    print(f"Low confidence (<0.2): {len(low_conf)}")
    
    # Analyze by source
    sources = {}
    for det in detections:
        source = det.get('source', 'unknown')
        if source not in sources:
            sources[source] = 0
        sources[source] += 1
    
    print(f"Detections by source: {sources}")
    
    return {
        'total_detections': len(detections),
        'high_conf_count': len(high_conf),
        'medium_conf_count': len(medium_conf),
        'low_conf_count': len(low_conf),
        'avg_score': np.mean(scores),
        'avg_area': np.mean(areas),
        'sources': sources
    }

# Main execution
if __name__ == "__main__":
    img_path = 'C:/Users/Arnav/Downloads/Room3.jpg'
    img = cv2.imread(img_path)
    
    if img is None:
        raise FileNotFoundError(f"Failed to load image at {img_path}")
    
    print(f"Loaded image with shape: {img.shape}")
    
    # Expected objects for testing
    expected_objects = [
        "chair", "couch", "tv", "dresser", "paintings", "table", "clock", "stool",
        "candle", "magazines", "vase", "pot", "media console", "media console shelf 1", "media console shelf 2"
    ]
    
    print(f"Expected objects: {len(expected_objects)}")
    for obj in expected_objects:
        print(f"  - {obj}")
    
    # Run fast comprehensive detection
    detections = enhanced_comprehensive_detect_objects(img, yolo_model)
    
    # Analyze quality
    quality_metrics = analyze_detection_quality(detections)
    
    # Save results
    timestamp = get_timestamp()
    base_name = os.path.splitext(os.path.basename(img_path))[0]
    
    # Save visualization
    vis_path = os.path.join(OUTPUT_DIR, f"{base_name}_enhanced_comprehensive_{timestamp}.png")
    visualize_detections(img, detections, "Enhanced Comprehensive Detection", vis_path)
    
    # Save individual masks and metadata
    save_detection_results(detections, MASKS_DIR, base_name)
    
    print(f"\nEnhanced comprehensive detection complete!")
    print(f"Final detections: {len(detections)}")
    print(f"Expected objects: {len(expected_objects)}")
    print(f"Results saved to: {OUTPUT_DIR} and {MASKS_DIR}")
    
    # Check if we detected enough objects
    if len(detections) >= len(expected_objects):
        print(f"✅ SUCCESS: Detected {len(detections)} objects, expected {len(expected_objects)}")
    else:
        print(f"⚠️  NEEDS IMPROVEMENT: Detected {len(detections)} objects, expected {len(expected_objects)}") 