import time
import os
import cv2
import numpy as np
import torch
from ultralytics import YOLO
from datetime import datetime
import json
from sklearn.cluster import DBSCAN
from scipy.spatial.distance import cdist

# ================= CONFIGURATION =================
YOLO_MODEL_PATH = "yolo11n-seg.pt"

# Advanced parameters
SCALES = [640, 1280, 1920]  # Focused scales for speed
CONF_THRESHOLDS = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.15]  # Strategic thresholds
IOU_NMS = 0.2  # Balanced NMS
MASK_IOU_THRESH = 0.15  # Low threshold for duplicate removal
MIN_MASK_AREA = 5  # Very small minimum
MAX_MASK_AREA = 100000  # Large maximum

# Output directories
OUTPUT_DIR = "advanced_universal_outputs"
MASKS_DIR = "advanced_universal_masks"
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

def analyze_image_characteristics(img):
    """Analyze image characteristics for adaptive parameter selection"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Calculate brightness
    brightness = np.mean(gray)
    
    # Calculate contrast
    contrast = np.std(gray)
    
    # Calculate edge density
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / (img.shape[0] * img.shape[1])
    
    # Calculate image complexity
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
    complexity = np.mean(gradient_magnitude)
    
    return {
        'brightness': brightness,
        'contrast': contrast,
        'edge_density': edge_density,
        'complexity': complexity,
        'image_area': img.shape[0] * img.shape[1]
    }

def adaptive_enhancement(img, characteristics):
    """Apply adaptive image enhancement based on image characteristics"""
    enhanced_images = []
    
    # Original image
    enhanced_images.append(("original", img))
    
    # Adaptive contrast enhancement
    if characteristics['contrast'] < 50:
        # Low contrast image - enhance more
        enhanced1 = cv2.convertScaleAbs(img, alpha=1.8, beta=30)
        enhanced_images.append(("contrast_enhanced", enhanced1))
    
    # Adaptive brightness enhancement
    if characteristics['brightness'] < 100:
        # Dark image - enhance brightness
        enhanced2 = cv2.convertScaleAbs(img, alpha=1.4, beta=40)
        enhanced_images.append(("brightness_enhanced", enhanced2))
    
    # Adaptive sharpening
    if characteristics['complexity'] < 20:
        # Low complexity - apply sharpening
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        enhanced3 = cv2.filter2D(img, -1, kernel)
        enhanced_images.append(("sharpened", enhanced3))
    
    # CLAHE for all images
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    lab[:,:,0] = clahe.apply(lab[:,:,0])
    enhanced4 = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    enhanced_images.append(("clahe", enhanced4))
    
    # Edge enhancement for high edge density images
    if characteristics['edge_density'] > 0.1:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edges_col = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        enhanced5 = cv2.addWeighted(img, 0.7, edges_col, 0.3, 0)
        enhanced_images.append(("edge_enhanced", enhanced5))
    
    return enhanced_images

def intelligent_scale_selection(characteristics):
    """Select scales based on image characteristics"""
    image_area = characteristics['image_area']
    
    if image_area < 200000:  # Small image
        return [640, 1280]
    elif image_area < 500000:  # Medium image
        return [1280, 1920]
    else:  # Large image
        return [1280, 1920, 2560]

def intelligent_threshold_selection(characteristics):
    """Select confidence thresholds based on image characteristics"""
    edge_density = characteristics['edge_density']
    complexity = characteristics['complexity']
    
    if edge_density > 0.15 or complexity > 30:
        # High complexity - use more thresholds
        return [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.15, 0.2]
    elif edge_density > 0.08 or complexity > 15:
        # Medium complexity
        return [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.15]
    else:
        # Low complexity - fewer thresholds
        return [0.001, 0.01, 0.05, 0.1, 0.15]

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

def advanced_duplicate_removal(detections):
    """Advanced duplicate removal using multiple strategies"""
    if not detections:
        return []
    
    # Sort by score in descending order
    detections.sort(key=lambda x: x['score'], reverse=True)
    
    unique_detections = []
    
    for det in detections:
        should_add = True
        
        # Check against all existing unique detections
        for i, unique_det in enumerate(unique_detections):
            # Strategy 1: Direct IoU overlap
            if mask_iou(det['mask'], unique_det['mask']) > MASK_IOU_THRESH:
                should_add = False
                break
            
            # Strategy 2: Containment check
            if mask_contains(det['mask'], unique_det['mask']) or mask_contains(unique_det['mask'], det['mask']):
                # Keep the larger mask (more complete detection)
                if mask_area(det['mask']) > mask_area(unique_det['mask']):
                    unique_detections[i] = det
                should_add = False
                break
            
            # Strategy 3: Box overlap check
            det_box = det['box']
            unique_box = unique_det['box']
            
            # Calculate box IoU
            x1 = max(det_box[0], unique_box[0])
            y1 = max(det_box[1], unique_box[1])
            x2 = min(det_box[2], unique_box[2])
            y2 = min(det_box[3], unique_box[3])
            
            if x2 > x1 and y2 > y1:
                intersection = (x2 - x1) * (y2 - y1)
                det_area = (det_box[2] - det_box[0]) * (det_box[3] - det_box[1])
                unique_area = (unique_box[2] - unique_box[0]) * (unique_box[3] - unique_box[1])
                union = det_area + unique_area - intersection
                
                if union > 0 and intersection / union > 0.3:
                    should_add = False
                    break
        
        if should_add:
            unique_detections.append(det)
    
    return unique_detections

def cluster_similar_detections(detections, distance_threshold=0.3):
    """Cluster similar detections using DBSCAN"""
    if len(detections) < 2:
        return detections
    
    # Extract features for clustering (center coordinates and area)
    features = []
    for det in detections:
        mask = det['mask']
        if mask is not None:
            # Calculate centroid
            moments = cv2.moments(mask)
            if moments['m00'] > 0:
                cx = moments['m10'] / moments['m00']
                cy = moments['m01'] / moments['m00']
            else:
                cx, cy = 0, 0
            
            # Normalize features
            area = mask_area(mask)
            features.append([cx, cy, area])
        else:
            features.append([0, 0, 0])
    
    if len(features) < 2:
        return detections
    
    # Normalize features
    features = np.array(features)
    features_normalized = (features - np.mean(features, axis=0)) / (np.std(features, axis=0) + 1e-8)
    
    # Apply DBSCAN clustering
    clustering = DBSCAN(eps=distance_threshold, min_samples=1).fit(features_normalized)
    labels = clustering.labels_
    
    # Group detections by cluster
    clusters = {}
    for i, label in enumerate(labels):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(detections[i])
    
    # For each cluster, keep the best detection
    final_detections = []
    for cluster_id, cluster_dets in clusters.items():
        if len(cluster_dets) == 1:
            final_detections.append(cluster_dets[0])
        else:
            # Keep the detection with highest score
            best_det = max(cluster_dets, key=lambda x: x['score'])
            final_detections.append(best_det)
    
    return final_detections

def adaptive_quality_filtering(detections, img_shape):
    """Adaptive quality filtering based on detection distribution"""
    if not detections:
        return detections
    
    # Calculate statistics
    scores = [det['score'] for det in detections]
    areas = [mask_area(det['mask']) for det in detections]
    
    mean_score = np.mean(scores)
    std_score = np.std(scores)
    mean_area = np.mean(areas)
    std_area = np.std(areas)
    
    filtered_detections = []
    
    for det in detections:
        score = det['score']
        area = mask_area(det['mask'])
        
        # Keep high-confidence detections
        if score > 0.3:
            filtered_detections.append(det)
            continue
        
        # Keep medium-confidence detections with reasonable area
        if 0.1 <= score <= 0.3 and 50 <= area <= 50000:
            filtered_detections.append(det)
            continue
        
        # Keep very small objects regardless of confidence (might be important details)
        if area < 1000:
            filtered_detections.append(det)
            continue
        
        # Keep detections that are significantly above average
        if score > mean_score + 0.5 * std_score or area > mean_area + 0.5 * std_area:
            filtered_detections.append(det)
            continue
    
    return filtered_detections

def advanced_detection(img, model):
    """Advanced detection with adaptive parameters"""
    all_detections = []
    
    # Analyze image characteristics
    characteristics = analyze_image_characteristics(img)
    print(f"Image characteristics: {characteristics}")
    
    # Select adaptive parameters
    scales = intelligent_scale_selection(characteristics)
    thresholds = intelligent_threshold_selection(characteristics)
    
    print(f"Selected scales: {scales}")
    print(f"Selected thresholds: {thresholds}")
    
    # Create adaptive enhancements
    enhanced_images = adaptive_enhancement(img, characteristics)
    print(f"Created {len(enhanced_images)} image enhancements")
    
    for enhancement_name, enhanced_img in enhanced_images:
        print(f"Processing {enhancement_name} enhancement...")
        
        for scale in scales:
            for conf_thresh in thresholds:
                results = model.predict(
                    enhanced_img, 
                    imgsz=scale, 
                    conf=conf_thresh, 
                    iou=IOU_NMS, 
                    verbose=False,
                    max_det=500
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
            'box': det['box'].tolist(),
            'scale': det.get('scale', 0),
            'conf_thresh': det.get('conf_thresh', 0),
            'source': det.get('source', 'unknown')
        })
    
    metadata_path = os.path.join(output_dir, f"{base_filename}_metadata_{timestamp}.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Saved metadata: {metadata_path}")

def advanced_universal_detect_objects(img, model):
    """Main advanced universal detection function"""
    print("Starting advanced universal object detection...")
    print("Using adaptive parameters and intelligent preprocessing...")
    
    # Get all detections with adaptive parameters
    all_detections = advanced_detection(img, model)
    
    # Apply advanced duplicate removal
    print("Applying advanced duplicate removal...")
    unique_detections = advanced_duplicate_removal(all_detections)
    print(f"After duplicate removal: {len(unique_detections)} detections")
    
    # Apply clustering for similar detections
    print("Applying clustering for similar detections...")
    clustered_detections = cluster_similar_detections(unique_detections)
    print(f"After clustering: {len(clustered_detections)} detections")
    
    # Apply adaptive quality filtering
    print("Applying adaptive quality filtering...")
    final_detections = adaptive_quality_filtering(clustered_detections, img.shape[:2])
    print(f"After quality filtering: {len(final_detections)} detections")
    
    # Sort by score
    final_detections.sort(key=lambda x: x['score'], reverse=True)
    
    return final_detections

def analyze_detection_quality(detections):
    """Analyze detection quality"""
    print("\n=== ADVANCED UNIVERSAL DETECTION QUALITY ANALYSIS ===")
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
    
    # Run advanced universal detection
    detections = advanced_universal_detect_objects(img, yolo_model)
    
    # Analyze quality
    quality_metrics = analyze_detection_quality(detections)
    
    # Save results
    timestamp = get_timestamp()
    base_name = os.path.splitext(os.path.basename(img_path))[0]
    
    # Save visualization
    vis_path = os.path.join(OUTPUT_DIR, f"{base_name}_advanced_universal_{timestamp}.png")
    visualize_detections(img, detections, "Advanced Universal Detection", vis_path)
    
    # Save individual masks and metadata
    save_detection_results(detections, MASKS_DIR, base_name)
    
    print(f"\nAdvanced universal detection complete!")
    print(f"Final detections: {len(detections)}")
    print(f"Expected objects: {len(expected_objects)}")
    print(f"Results saved to: {OUTPUT_DIR} and {MASKS_DIR}")
    
    # Check if we detected enough objects
    if len(detections) >= len(expected_objects):
        print(f"✅ SUCCESS: Detected {len(detections)} objects, expected {len(expected_objects)}")
    else:
        print(f"⚠️  NEEDS IMPROVEMENT: Detected {len(detections)} objects, expected {len(expected_objects)}") 