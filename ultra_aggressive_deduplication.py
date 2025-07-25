import os
import time
import cv2
import numpy as np
from ultralytics import YOLO
from collections import defaultdict

# Paths
MODEL_PATH = 'yolo11n-seg.pt'
IMAGE_PATH = 'C:/Users/Arnav/Downloads/Room3.jpg'
OUTPUT_DIR = 'yoloimprvoedoutput'
OUTPUT_IMAGE = os.path.join(OUTPUT_DIR, 'Room3_ultra_deduplicated_output.png')

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# More lenient filtering parameters
UNWANTED_CLASSES = {'person', 'car', 'truck', 'bus', 'train', 'motorcycle', 'bicycle', 'airplane', 'boat'}
MIN_OBJECT_AREA = 200  # Lower minimum for small objects
MAX_OBJECT_AREA = 150000  # Higher maximum for large furniture
MIN_ASPECT_RATIO = 0.05  # More lenient aspect ratio
MAX_ASPECT_RATIO = 15.0  # More lenient aspect ratio
MAX_IMAGE_COVERAGE = 0.5  # Allow up to 50% image coverage

def create_image_variants(image):
    """Create different image variants for ensemble detection"""
    variants = []
    
    # Original image
    variants.append(('original', image))
    
    # Contrast enhancement
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    l = clahe.apply(l)
    enhanced_lab = cv2.merge([l, a, b])
    enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    variants.append(('contrast_enhanced', enhanced_bgr))
    
    # Edge enhancement
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    edge_enhanced = cv2.filter2D(image, -1, kernel)
    variants.append(('edge_enhanced', edge_enhanced))
    
    # Noise reduction
    denoised = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
    variants.append(('denoised', denoised))
    
    # Brightness adjustment
    brightened = cv2.convertScaleAbs(image, alpha=1.2, beta=30)
    variants.append(('brightened', brightened))
    
    # Gamma correction for better furniture detection
    gamma = 1.3
    gamma_corrected = np.power(image/255.0, gamma) * 255.0
    gamma_corrected = gamma_corrected.astype(np.uint8)
    variants.append(('gamma_corrected', gamma_corrected))
    
    return variants

def run_ensemble_detection(model, image_variants, scales, conf_thresholds):
    """Run detection on multiple image variants with different scales and confidences"""
    all_detections = []
    
    for variant_name, variant_image in image_variants:
        print(f"Processing {variant_name} variant...")
        
        for scale in scales:
            for conf in conf_thresholds:
                # Resize image
                h, w = variant_image.shape[:2]
                new_h, new_w = int(h * scale), int(w * scale)
                resized_img = cv2.resize(variant_image, (new_w, new_h))
                
                # Run inference
                results = model(resized_img, conf=conf, verbose=False)
                
                # Scale back the detections
                for result in results:
                    if result.boxes is not None:
                        for i, box in enumerate(result.boxes.xyxy):
                            # Scale back to original image size
                            scaled_box = box.cpu().numpy() / scale
                            confidence = result.boxes.conf[i].cpu().numpy()
                            class_id = result.boxes.cls[i].cpu().numpy()
                            class_name = result.names[int(class_id)]
                            
                            all_detections.append({
                                'bbox': scaled_box,
                                'confidence': confidence,
                                'class': class_name,
                                'scale': scale,
                                'conf_threshold': conf,
                                'variant': variant_name
                            })
    
    return all_detections

def balanced_filter_detections(detections, img_shape):
    """More lenient filtering that preserves blended objects"""
    filtered_detections = []
    img_height, img_width = img_shape[:2]
    img_area = img_height * img_width
    
    for det in detections:
        bbox = det['bbox']
        class_name = det['class']
        confidence = det['confidence']
        
        # Skip unwanted classes
        if class_name in UNWANTED_CLASSES:
            continue
        
        # Calculate object properties
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        area = width * height
        aspect_ratio = width / height if height > 0 else float('inf')
        
        # More lenient size filtering
        if area < MIN_OBJECT_AREA or area > MAX_OBJECT_AREA:
            continue
        
        # More lenient aspect ratio filtering
        if aspect_ratio < MIN_ASPECT_RATIO or aspect_ratio > MAX_ASPECT_RATIO:
            continue
        
        # More lenient coverage filtering
        object_coverage = area / img_area
        if object_coverage > MAX_IMAGE_COVERAGE:
            continue
        
        # Special handling for furniture classes - be more lenient
        if class_name in ['dining table', 'chair', 'couch', 'tv', 'vase', 'book', 'clock']:
            # Allow lower confidence for furniture
            if confidence < 0.03:  # Very low threshold for furniture
                continue
        else:
            # For other objects, use slightly higher threshold
            if confidence < 0.05:
                continue
        
        # Keep the detection
        filtered_detections.append(det)
    
    return filtered_detections

def ultra_aggressive_non_max_suppression(detections, iou_threshold=0.2):
    """Ultra-aggressive NMS to remove all duplicates"""
    if not detections:
        return []
    
    # Group by class
    class_groups = defaultdict(list)
    for det in detections:
        class_groups[det['class']].append(det)
    
    final_detections = []
    
    for class_name, class_dets in class_groups.items():
        # Sort by weighted score
        for det in class_dets:
            # Give bonus for certain variants and furniture classes
            variant_bonus = 0.0
            if det['variant'] in ['contrast_enhanced', 'edge_enhanced', 'gamma_corrected']:
                variant_bonus = 0.15  # Higher bonus for good variants
            
            # Extra bonus for furniture classes
            if class_name in ['dining table', 'chair', 'couch', 'tv']:
                variant_bonus += 0.1
            
            det['weighted_score'] = det['confidence'] + variant_bonus
        
        class_dets.sort(key=lambda x: x['weighted_score'], reverse=True)
        
        kept = []
        for det in class_dets:
            should_keep = True
            
            for kept_det in kept:
                # Calculate IoU
                iou = calculate_iou(det['bbox'], kept_det['bbox'])
                
                # Use ultra-aggressive IoU threshold
                if iou > iou_threshold:
                    should_keep = False
                    break
                
                # Additional check: if centers are very close, consider it a duplicate
                center_distance = calculate_center_distance(det['bbox'], kept_det['bbox'])
                if center_distance < 50:  # If centers are within 50 pixels
                    should_keep = False
                    break
            
            if should_keep:
                kept.append(det)
        
        final_detections.extend(kept)
    
    return final_detections

def calculate_iou(box1, box2):
    """Calculate IoU between two bounding boxes"""
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2
    
    # Calculate intersection
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)
    
    if x2_i <= x1_i or y2_i <= y1_i:
        return 0.0
    
    intersection = (x2_i - x1_i) * (y2_i - y1_i)
    
    # Calculate union
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0.0

def calculate_center_distance(box1, box2):
    """Calculate distance between centers of two bounding boxes"""
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2
    
    center1_x = (x1_1 + x2_1) / 2
    center1_y = (y1_1 + y2_1) / 2
    center2_x = (x1_2 + x2_2) / 2
    center2_y = (y1_2 + y2_2) / 2
    
    distance = np.sqrt((center1_x - center2_x)**2 + (center1_y - center2_y)**2)
    return distance

def draw_ultra_deduplicated_detections(image, detections):
    """Draw ultra-deduplicated detections with different colors based on confidence and class"""
    result_image = image.copy()
    
    for detection in detections:
        bbox = detection['bbox']
        confidence = detection['confidence']
        class_name = detection['class']
        variant = detection['variant']
        
        x1, y1, x2, y2 = map(int, bbox)
        
        # Color based on class and confidence
        if class_name in ['dining table', 'chair', 'couch', 'tv']:
            color = (0, 255, 0)  # Green for furniture
        elif confidence > 0.7:
            color = (255, 255, 0)  # Yellow for high confidence
        elif confidence > 0.4:
            color = (0, 255, 255)  # Cyan for medium confidence
        else:
            color = (255, 0, 255)  # Magenta for low confidence
        
        # Draw bounding box
        cv2.rectangle(result_image, (x1, y1), (x2, y2), color, 2)
        
        # Draw label
        label = f"{class_name}: {confidence:.2f}"
        cv2.putText(result_image, label, (x1, y1-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
    return result_image

def main():
    print("Loading YOLO model...")
    model = YOLO(MODEL_PATH)
    
    print("Reading image...")
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        raise FileNotFoundError(f'Could not load image: {IMAGE_PATH}')
    
    print("Creating image variants...")
    image_variants = create_image_variants(img)
    
    # More comprehensive parameters
    scales = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
    conf_thresholds = [0.03, 0.05, 0.1, 0.15, 0.2, 0.25]  # Lower thresholds
    
    print(f"Running ensemble detection with ultra-aggressive deduplication...")
    start_time = time.time()
    
    # Run ensemble detection
    all_detections = run_ensemble_detection(model, image_variants, scales, conf_thresholds)
    
    print(f"Found {len(all_detections)} raw detections")
    
    # Apply balanced filtering
    filtered_detections = balanced_filter_detections(all_detections, img.shape)
    print(f"After filtering: {len(filtered_detections)} detections")
    
    # Apply ultra-aggressive NMS
    final_detections = ultra_aggressive_non_max_suppression(filtered_detections, iou_threshold=0.2)
    
    total_time = time.time() - start_time
    
    print("Drawing results...")
    result_image = draw_ultra_deduplicated_detections(img, final_detections)
    
    # Save result
    cv2.imwrite(OUTPUT_IMAGE, result_image)
    
    # Print results
    print(f"\n=== ULTRA-AGGRESSIVE DEDUPLICATION DETECTION RESULTS ===")
    print(f"Total time: {total_time:.2f}s")
    print(f"Raw detections: {len(all_detections)}")
    print(f"After filtering: {len(filtered_detections)}")
    print(f"Final detections after ultra-aggressive NMS: {len(final_detections)}")
    print(f"Results saved to: {OUTPUT_IMAGE}")
    
    # Print detection details
    print("\n=== DETECTION DETAILS ===")
    for i, detection in enumerate(final_detections):
        class_name = detection['class']
        confidence = detection['confidence']
        variant = detection['variant']
        bbox = detection['bbox']
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        print(f"{i+1}. {class_name}: {confidence:.3f} ({variant}) - Area: {area:.0f} at {bbox}")
    
    # Count by class
    class_counts = defaultdict(int)
    for det in final_detections:
        class_counts[det['class']] += 1
    
    print("\n=== DETECTION SUMMARY BY CLASS ===")
    for class_name, count in sorted(class_counts.items()):
        print(f"{class_name}: {count}")

if __name__ == "__main__":
    main() 