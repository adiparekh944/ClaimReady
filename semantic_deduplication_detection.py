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
OUTPUT_IMAGE = os.path.join(OUTPUT_DIR, 'Room3_semantic_deduplicated_output.png')

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Object categories and their properties
OBJECT_CATEGORIES = {
    'furniture': {
        'classes': ['dining table', 'chair', 'couch', 'tv'],
        'min_area': 5000,
        'max_area': 100000,
        'max_count_per_room': 10,
        'spatial_constraints': {
            'dining table': {'max_count': 3, 'min_distance': 100},
            'chair': {'max_count': 8, 'min_distance': 80},
            'couch': {'max_count': 3, 'min_distance': 150},
            'tv': {'max_count': 2, 'min_distance': 200}
        }
    },
    'small_objects': {
        'classes': ['vase', 'book', 'clock', 'cup', 'keyboard', 'laptop'],
        'min_area': 200,
        'max_area': 5000,
        'max_count_per_room': 20,
        'spatial_constraints': {
            'vase': {'max_count': 5, 'min_distance': 50},
            'book': {'max_count': 10, 'min_distance': 30},
            'clock': {'max_count': 3, 'min_distance': 100},
            'cup': {'max_count': 3, 'min_distance': 40},
            'keyboard': {'max_count': 2, 'min_distance': 60},
            'laptop': {'max_count': 2, 'min_distance': 80}
        }
    },
    'animals': {
        'classes': ['cat', 'dog'],
        'min_area': 500,
        'max_area': 10000,
        'max_count_per_room': 3,
        'spatial_constraints': {
            'cat': {'max_count': 2, 'min_distance': 100},
            'dog': {'max_count': 2, 'min_distance': 100}
        }
    }
}

# More lenient filtering parameters
UNWANTED_CLASSES = {'person', 'car', 'truck', 'bus', 'train', 'motorcycle', 'bicycle', 'airplane', 'boat'}
MIN_OBJECT_AREA = 200
MAX_OBJECT_AREA = 150000
MIN_ASPECT_RATIO = 0.05
MAX_ASPECT_RATIO = 15.0
MAX_IMAGE_COVERAGE = 0.5

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

def get_object_category(class_name):
    """Get the category of an object based on its class name"""
    for category, properties in OBJECT_CATEGORIES.items():
        if class_name in properties['classes']:
            return category
    return 'other'

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

def calculate_distance(center1, center2):
    """Calculate Euclidean distance between two centers"""
    return np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)

def semantic_non_max_suppression(detections):
    """Semantic NMS that understands object context and relationships"""
    if not detections:
        return []
    
    # Group by category first, then by class
    category_groups = defaultdict(lambda: defaultdict(list))
    for det in detections:
        category = get_object_category(det['class'])
        category_groups[category][det['class']].append(det)
    
    final_detections = []
    
    for category, class_groups in category_groups.items():
        category_props = OBJECT_CATEGORIES.get(category, {})
        
        for class_name, class_dets in class_groups.items():
            print(f"Processing {class_name} in category {category}...")
            
            # Sort by weighted score
            for det in class_dets:
                # Give bonus for certain variants and furniture classes
                variant_bonus = 0.0
                if det['variant'] in ['contrast_enhanced', 'edge_enhanced', 'gamma_corrected']:
                    variant_bonus = 0.15
                
                # Extra bonus for furniture classes
                if det['class'] in ['dining table', 'chair', 'couch', 'tv']:
                    variant_bonus += 0.1
                
                det['weighted_score'] = det['confidence'] + variant_bonus
            
            class_dets.sort(key=lambda x: x['weighted_score'], reverse=True)
            
            # Apply semantic constraints
            kept = []
            class_constraints = category_props.get('spatial_constraints', {}).get(class_name, {})
            max_count = class_constraints.get('max_count', 5)
            min_distance = class_constraints.get('min_distance', 50)
            
            for det in class_dets:
                if len(kept) >= max_count:
                    break
                
                should_keep = True
                det_center = calculate_bbox_center(det['bbox'])
                det_area = calculate_bbox_area(det['bbox'])
                
                # Check against kept detections of the same class
                for kept_det in kept:
                    kept_center = calculate_bbox_center(kept_det['bbox'])
                    kept_area = calculate_bbox_area(kept_det['bbox'])
                    
                    # Calculate distance
                    distance = calculate_distance(det_center, kept_center)
                    
                    # Check if too close
                    if distance < min_distance:
                        should_keep = False
                        break
                    
                    # Check if areas are too similar (likely same object)
                    area_ratio = min(det_area, kept_area) / max(det_area, kept_area)
                    if area_ratio > 0.8 and distance < min_distance * 1.5:
                        should_keep = False
                        break
                
                # Check against other classes in the same category
                for other_class, other_dets in class_groups.items():
                    if other_class == class_name:
                        continue
                    
                    for other_det in other_dets:
                        other_center = calculate_bbox_center(other_det['bbox'])
                        distance = calculate_distance(det_center, other_center)
                        
                        # If very close to different class object, might be misclassification
                        if distance < min_distance * 0.5:
                            # Check if this detection has lower confidence
                            if det['confidence'] < other_det['confidence']:
                                should_keep = False
                                break
                
                if should_keep:
                    kept.append(det)
            
            final_detections.extend(kept)
    
    return final_detections

def draw_semantic_detections(image, detections):
    """Draw semantic detections with different colors based on category and confidence"""
    result_image = image.copy()
    
    for detection in detections:
        bbox = detection['bbox']
        confidence = detection['confidence']
        class_name = detection['class']
        category = get_object_category(class_name)
        
        x1, y1, x2, y2 = map(int, bbox)
        
        # Color based on category and confidence
        if category == 'furniture':
            color = (0, 255, 0)  # Green for furniture
        elif category == 'small_objects':
            if confidence > 0.7:
                color = (255, 255, 0)  # Yellow for high confidence small objects
            else:
                color = (0, 255, 255)  # Cyan for medium confidence small objects
        elif category == 'animals':
            color = (255, 0, 255)  # Magenta for animals
        else:
            color = (255, 0, 0)  # Red for other
        
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
    conf_thresholds = [0.03, 0.05, 0.1, 0.15, 0.2, 0.25]
    
    print(f"Running ensemble detection with semantic deduplication...")
    start_time = time.time()
    
    # Run ensemble detection
    all_detections = run_ensemble_detection(model, image_variants, scales, conf_thresholds)
    
    print(f"Found {len(all_detections)} raw detections")
    
    # Apply balanced filtering
    filtered_detections = balanced_filter_detections(all_detections, img.shape)
    print(f"After filtering: {len(filtered_detections)} detections")
    
    # Apply semantic NMS
    final_detections = semantic_non_max_suppression(filtered_detections)
    
    total_time = time.time() - start_time
    
    print("Drawing results...")
    result_image = draw_semantic_detections(img, final_detections)
    
    # Save result
    cv2.imwrite(OUTPUT_IMAGE, result_image)
    
    # Print results
    print(f"\n=== SEMANTIC DEDUPLICATION DETECTION RESULTS ===")
    print(f"Total time: {total_time:.2f}s")
    print(f"Raw detections: {len(all_detections)}")
    print(f"After filtering: {len(filtered_detections)}")
    print(f"Final detections after semantic NMS: {len(final_detections)}")
    print(f"Results saved to: {OUTPUT_IMAGE}")
    
    # Print detection details
    print("\n=== DETECTION DETAILS ===")
    for i, detection in enumerate(final_detections):
        class_name = detection['class']
        confidence = detection['confidence']
        category = get_object_category(class_name)
        bbox = detection['bbox']
        area = calculate_bbox_area(bbox)
        print(f"{i+1}. {class_name} ({category}): {confidence:.3f} - Area: {area:.0f} at {bbox}")
    
    # Count by class
    class_counts = defaultdict(int)
    for det in final_detections:
        class_counts[det['class']] += 1
    
    print("\n=== DETECTION SUMMARY BY CLASS ===")
    for class_name, count in sorted(class_counts.items()):
        print(f"{class_name}: {count}")
    
    # Count by category
    category_counts = defaultdict(int)
    for det in final_detections:
        category = get_object_category(det['class'])
        category_counts[category] += 1
    
    print("\n=== DETECTION SUMMARY BY CATEGORY ===")
    for category, count in sorted(category_counts.items()):
        print(f"{category}: {count}")

if __name__ == "__main__":
    main() 