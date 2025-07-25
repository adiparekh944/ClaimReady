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
OUTPUT_IMAGE = os.path.join(OUTPUT_DIR, 'Room3_filtered_ensemble_output.png')

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Define unwanted classes and size thresholds
UNWANTED_CLASSES = {'person', 'car', 'truck', 'bus', 'train', 'motorcycle', 'bicycle', 'airplane', 'boat'}
MIN_OBJECT_AREA = 500  # Minimum area in pixels
MAX_OBJECT_AREA = 100000  # Maximum area in pixels (prevents entire room detection)
MIN_ASPECT_RATIO = 0.1  # Minimum width/height ratio
MAX_ASPECT_RATIO = 10.0  # Maximum width/height ratio

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

def filter_detections(detections, img_shape):
    """Filter out unwanted detections based on size, class, and aspect ratio"""
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
        
        # Skip if too small or too large
        if area < MIN_OBJECT_AREA or area > MAX_OBJECT_AREA:
            continue
        
        # Skip if aspect ratio is extreme (likely wall/floor)
        if aspect_ratio < MIN_ASPECT_RATIO or aspect_ratio > MAX_ASPECT_RATIO:
            continue
        
        # Skip if object covers too much of the image (likely background)
        object_coverage = area / img_area
        if object_coverage > 0.3:  # Skip if object covers more than 30% of image
            continue
        
        # Skip very low confidence detections for certain classes
        if confidence < 0.05 and class_name in ['dining table', 'chair', 'couch']:
            continue
        
        # Keep the detection
        filtered_detections.append(det)
    
    return filtered_detections

def weighted_non_max_suppression(detections, iou_threshold=0.4):
    """Weighted NMS that considers variant quality and confidence"""
    if not detections:
        return []
    
    # Group by class
    class_groups = defaultdict(list)
    for det in detections:
        class_groups[det['class']].append(det)
    
    final_detections = []
    
    for class_name, class_dets in class_groups.items():
        # Sort by weighted score (confidence + variant bonus)
        for det in class_dets:
            # Give bonus for certain variants that work well for furniture
            variant_bonus = 0.0
            if det['variant'] in ['contrast_enhanced', 'edge_enhanced']:
                variant_bonus = 0.1
            det['weighted_score'] = det['confidence'] + variant_bonus
        
        class_dets.sort(key=lambda x: x['weighted_score'], reverse=True)
        
        kept = []
        for det in class_dets:
            should_keep = True
            
            for kept_det in kept:
                # Calculate IoU
                iou = calculate_iou(det['bbox'], kept_det['bbox'])
                if iou > iou_threshold:
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

def draw_filtered_detections(image, detections):
    """Draw filtered detections with different colors based on confidence"""
    result_image = image.copy()
    
    for detection in detections:
        bbox = detection['bbox']
        confidence = detection['confidence']
        class_name = detection['class']
        variant = detection['variant']
        
        x1, y1, x2, y2 = map(int, bbox)
        
        # Color based on confidence
        if confidence > 0.7:
            color = (0, 255, 0)  # Green for high confidence
        elif confidence > 0.4:
            color = (255, 255, 0)  # Yellow for medium confidence
        else:
            color = (0, 255, 255)  # Cyan for low confidence
        
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
    
    # Multi-scale and multi-confidence parameters (reduced for speed)
    scales = [0.5, 0.75, 1.0, 1.25, 1.5]
    conf_thresholds = [0.05, 0.1, 0.15, 0.2]
    
    print(f"Running filtered ensemble detection...")
    start_time = time.time()
    
    # Run ensemble detection
    all_detections = run_ensemble_detection(model, image_variants, scales, conf_thresholds)
    
    print(f"Found {len(all_detections)} raw detections")
    
    # Filter out unwanted detections
    filtered_detections = filter_detections(all_detections, img.shape)
    print(f"After filtering: {len(filtered_detections)} detections")
    
    # Apply weighted NMS
    final_detections = weighted_non_max_suppression(filtered_detections, iou_threshold=0.4)
    
    total_time = time.time() - start_time
    
    print("Drawing results...")
    result_image = draw_filtered_detections(img, final_detections)
    
    # Save result
    cv2.imwrite(OUTPUT_IMAGE, result_image)
    
    # Print results
    print(f"\n=== FILTERED ENSEMBLE DETECTION RESULTS ===")
    print(f"Total time: {total_time:.2f}s")
    print(f"Raw detections: {len(all_detections)}")
    print(f"After filtering: {len(filtered_detections)}")
    print(f"Final detections after NMS: {len(final_detections)}")
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