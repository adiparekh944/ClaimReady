import os
import time
import cv2
import numpy as np
from ultralytics import YOLO
from collections import defaultdict

# Paths
MODEL_PATH = 'yolo11n-seg.pt'
IMAGE_PATH = 'C:/Users/Arnav/Downloads/IMG_4025.jpg'
OUTPUT_DIR = 'yoloimprvoedoutput'
OUTPUT_IMAGE = os.path.join(OUTPUT_DIR, 'IMG_4025_enhanced_output.png')

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# More lenient parameters to catch major objects
MIN_OBJECT_AREA = 100  # Lower to catch smaller objects
MAX_OBJECT_AREA = 200000  # Higher to catch large furniture
MIN_ASPECT_RATIO = 0.02  # More lenient
MAX_ASPECT_RATIO = 20.0  # More lenient
MAX_IMAGE_COVERAGE = 0.7  # Allow larger objects
MIN_CONFIDENCE = 0.01  # Much lower to catch blended objects

def create_enhanced_variants(image):
    """Create more image variants to catch blended objects"""
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
    
    # Edge enhancement for furniture detection
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    edge_enhanced = cv2.filter2D(image, -1, kernel)
    variants.append(('edge_enhanced', edge_enhanced))
    
    # Brightness adjustment
    brightened = cv2.convertScaleAbs(image, alpha=1.3, beta=40)
    variants.append(('brightened', brightened))
    
    # Gamma correction for better furniture detection
    gamma = 1.4
    gamma_corrected = np.power(image/255.0, gamma) * 255.0
    gamma_corrected = gamma_corrected.astype(np.uint8)
    variants.append(('gamma_corrected', gamma_corrected))
    
    # Noise reduction for cleaner detection
    denoised = cv2.fastNlMeansDenoisingColored(image, None, 8, 8, 7, 21)
    variants.append(('denoised', denoised))
    
    return variants

def run_enhanced_ensemble_detection(model, image_variants, scales, conf_thresholds):
    """Enhanced ensemble detection with more aggressive parameters"""
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
                    if result.boxes is not None and result.masks is not None:
                        for i, box in enumerate(result.boxes.xyxy):
                            # Scale back to original image size
                            scaled_box = box.cpu().numpy() / scale
                            confidence = result.boxes.conf[i].cpu().numpy()
                            class_id = result.boxes.cls[i].cpu().numpy()
                            class_name = result.names[int(class_id)]
                            
                            # Get mask and scale it back
                            mask = result.masks.data[i].cpu().numpy()
                            mask = cv2.resize(mask, (w, h))
                            mask = (mask > 0.5).astype(np.uint8)
                            
                            all_detections.append({
                                'bbox': scaled_box,
                                'mask': mask,
                                'confidence': confidence,
                                'class': class_name,
                                'scale': scale,
                                'conf_threshold': conf,
                                'variant': variant_name
                            })
    
    return all_detections

def enhanced_filter_detections(detections, img_shape):
    """Enhanced filtering that preserves major objects"""
    filtered_detections = []
    img_height, img_width = img_shape[:2]
    img_area = img_height * img_width
    
    for det in detections:
        bbox = det['bbox']
        confidence = det['confidence']
        class_name = det['class']
        
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
        
        # Very low confidence threshold to catch blended objects
        if confidence < MIN_CONFIDENCE:
            continue
        
        # Keep the detection
        filtered_detections.append(det)
    
    return filtered_detections

def calculate_bbox_center(bbox):
    """Calculate the center point of a bounding box"""
    x1, y1, x2, y2 = bbox
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    return (center_x, center_y)

def calculate_bbox_area(bbox):
    """Calculate the area of a bounding box"""
    x1, y1, x2, y2 = bbox
    return (x2 - x1) * (y2 - y1)

def calculate_mask_area(mask):
    """Calculate the area of a mask"""
    return np.sum(mask)

def calculate_mask_overlap(mask1, mask2):
    """Calculate overlap between two masks"""
    if mask1 is None or mask2 is None:
        return 0.0
    
    # Ensure masks are same size
    if mask1.shape != mask2.shape:
        return 0.0
    
    intersection = np.logical_and(mask1, mask2)
    union = np.logical_or(mask1, mask2)
    
    intersection_area = np.sum(intersection)
    union_area = np.sum(union)
    
    if union_area == 0:
        return 0.0
    
    return intersection_area / union_area

def calculate_distance(center1, center2):
    """Calculate Euclidean distance between two centers"""
    return np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)

def enhanced_mask_nms(detections):
    """Enhanced mask-based NMS with better handling of major objects"""
    if not detections:
        return []
    
    # Group by class
    class_groups = defaultdict(list)
    for det in detections:
        class_groups[det['class']].append(det)
    
    final_detections = []
    
    for class_name, class_dets in class_groups.items():
        print(f"Processing {class_name} with enhanced mask analysis...")
        
        # Sort by confidence
        class_dets.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Adaptive parameters based on detection statistics
        if len(class_dets) > 0:
            areas = [calculate_bbox_area(det['bbox']) for det in class_dets]
            avg_area = np.mean(areas)
            
            # More lenient thresholds for major objects
            if class_name in ['chair', 'dining table', 'couch', 'tv', 'desk']:
                min_distance = max(30, min(150, avg_area ** 0.5 * 0.15))
                mask_overlap_threshold = 0.35
                max_count = min(8, len(class_dets))
            else:
                min_distance = max(15, min(80, avg_area ** 0.5 * 0.1))
                mask_overlap_threshold = 0.4
                max_count = min(6, len(class_dets))
        else:
            min_distance = 40
            mask_overlap_threshold = 0.4
            max_count = 5
        
        kept = []
        
        for det in class_dets:
            if len(kept) >= max_count:
                break
            
            should_keep = True
            det_center = calculate_bbox_center(det['bbox'])
            det_mask = det['mask']
            
            # Check against kept detections of the same class
            for kept_det in kept:
                kept_center = calculate_bbox_center(kept_det['bbox'])
                kept_mask = kept_det['mask']
                
                # Calculate distance
                distance = calculate_distance(det_center, kept_center)
                
                # Check if too close
                if distance < min_distance:
                    should_keep = False
                    break
                
                # Check mask overlap
                mask_overlap = calculate_mask_overlap(det_mask, kept_mask)
                if mask_overlap > mask_overlap_threshold:
                    should_keep = False
                    break
            
            if should_keep:
                kept.append(det)
        
        final_detections.extend(kept)
    
    return final_detections

def draw_enhanced_detections(image, detections):
    """Draw detections with enhanced color coding"""
    result_image = image.copy()
    
    for detection in detections:
        bbox = detection['bbox']
        confidence = detection['confidence']
        class_name = detection['class']
        
        x1, y1, x2, y2 = map(int, bbox)
        
        # Enhanced color coding
        if confidence > 0.7:
            color = (0, 255, 0)  # Green for high confidence
        elif confidence > 0.4:
            color = (255, 255, 0)  # Yellow for medium confidence
        elif confidence > 0.1:
            color = (0, 255, 255)  # Cyan for low confidence
        else:
            color = (255, 0, 255)  # Magenta for very low confidence
        
        # Draw bounding box
        cv2.rectangle(result_image, (x1, y1), (x2, y2), color, 2)
        
        # Draw label
        label = f"{class_name}: {confidence:.3f}"
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
    
    print("Creating enhanced image variants...")
    image_variants = create_enhanced_variants(img)
    
    # More comprehensive parameters
    scales = [0.5, 0.75, 1.0, 1.25, 1.5]  # More scales
    conf_thresholds = [0.01, 0.03, 0.05, 0.1, 0.15, 0.2]  # Lower thresholds
    
    print(f"Running enhanced adaptive detection...")
    start_time = time.time()
    
    # Run enhanced ensemble detection
    all_detections = run_enhanced_ensemble_detection(model, image_variants, scales, conf_thresholds)
    
    print(f"Found {len(all_detections)} raw detections")
    
    # Apply enhanced filtering
    filtered_detections = enhanced_filter_detections(all_detections, img.shape)
    print(f"After filtering: {len(filtered_detections)} detections")
    
    # Apply enhanced mask NMS
    final_detections = enhanced_mask_nms(filtered_detections)
    
    total_time = time.time() - start_time
    
    print("Drawing results...")
    result_image = draw_enhanced_detections(img, final_detections)
    
    # Save result
    cv2.imwrite(OUTPUT_IMAGE, result_image)
    
    # Print results
    print(f"\n=== ENHANCED ADAPTIVE DETECTION RESULTS ===")
    print(f"Total time: {total_time:.2f}s")
    print(f"Raw detections: {len(all_detections)}")
    print(f"After filtering: {len(filtered_detections)}")
    print(f"Final detections: {len(final_detections)}")
    print(f"Results saved to: {OUTPUT_IMAGE}")
    
    # Print detection details
    print("\n=== DETECTION DETAILS ===")
    for i, detection in enumerate(final_detections):
        class_name = detection['class']
        confidence = detection['confidence']
        bbox = detection['bbox']
        area = calculate_bbox_area(bbox)
        mask_area = calculate_mask_area(detection['mask']) if detection['mask'] is not None else 0
        print(f"{i+1}. {class_name}: {confidence:.3f} - Area: {area:.0f}, Mask: {mask_area:.0f}")
    
    # Count by class
    class_counts = defaultdict(int)
    for det in final_detections:
        class_counts[det['class']] += 1
    
    print("\n=== DETECTION SUMMARY ===")
    for class_name, count in sorted(class_counts.items()):
        print(f"{class_name}: {count}")

if __name__ == "__main__":
    main() 