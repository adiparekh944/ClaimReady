import os
import time
import cv2
import numpy as np
from ultralytics import YOLO
import torch
from transformers import pipeline
from PIL import Image

# Paths
MODEL_PATH = 'yolo11n-seg.pt'
IMAGE_PATH = 'C:/Users/Arnav/Downloads/Room3.jpg'
OUTPUT_DIR = 'yoloimprvoedoutput'
OUTPUT_IMAGE = os.path.join(OUTPUT_DIR, 'Room3_depth_enhanced_output.png')

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_depth_estimator():
    """Load MiDaS depth estimation model"""
    try:
        # Use MiDaS for depth estimation
        depth_estimator = pipeline("depth-estimation", model="Intel/dpt-large")
        return depth_estimator
    except Exception as e:
        print(f"Could not load depth estimator: {e}")
        return None

def get_depth_map(image, depth_estimator):
    """Get depth map from RGB image"""
    if depth_estimator is None:
        return None
    
    # Convert BGR to RGB and then to PIL Image
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb_image)
    
    # Get depth prediction
    depth_result = depth_estimator(pil_image)
    depth_map = depth_result['depth']
    
    # Convert PIL image to numpy array and normalize
    depth_map = np.array(depth_map)
    depth_map = ((depth_map - depth_map.min()) / (depth_map.max() - depth_map.min()) * 255).astype(np.uint8)
    
    return depth_map

def find_depth_based_objects(depth_map, yolo_detections, img_shape):
    """Find potential missed objects based on depth discontinuities"""
    if depth_map is None:
        return []
    
    height, width = depth_map.shape
    potential_objects = []
    
    # Find depth discontinuities (edges in depth map)
    depth_edges = cv2.Canny(depth_map, 50, 150)
    
    # Find contours in depth edges
    contours, _ = cv2.findContours(depth_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours based on size and depth characteristics
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 500 or area > 50000:  # Filter by size
            continue
            
        # Get bounding box
        x, y, w, h = cv2.boundingRect(contour)
        
        # Check if this region overlaps significantly with existing YOLO detections
        overlaps_with_existing = False
        for detection in yolo_detections:
            if hasattr(detection, 'boxes') and detection.boxes is not None:
                for box in detection.boxes.xyxy:
                    box_x1, box_y1, box_x2, box_y2 = box.cpu().numpy()
                    # Check overlap
                    if (x < box_x2 and x + w > box_x1 and 
                        y < box_y2 and y + h > box_y1):
                        overlap_area = min(w, box_x2 - x) * min(h, box_y2 - y)
                        if overlap_area > 0.5 * w * h:  # More than 50% overlap
                            overlaps_with_existing = True
                            break
                if overlaps_with_existing:
                    break
        
        if not overlaps_with_existing:
            # Calculate average depth in this region
            roi_depth = depth_map[y:y+h, x:x+w]
            avg_depth = np.mean(roi_depth)
            
            # Add as potential object
            potential_objects.append({
                'bbox': [x, y, x+w, y+h],
                'confidence': 0.3,  # Medium confidence for depth-based detection
                'class': 'unknown_object',
                'depth_score': avg_depth,
                'area': area
            })
    
    return potential_objects

def combine_detections(yolo_results, depth_objects):
    """Combine YOLO detections with depth-based detections"""
    combined_detections = []
    
    # Add YOLO detections
    for result in yolo_results:
        if result.boxes is not None:
            for i, box in enumerate(result.boxes.xyxy):
                confidence = result.boxes.conf[i].cpu().numpy()
                class_id = result.boxes.cls[i].cpu().numpy()
                class_name = result.names[int(class_id)]
                
                combined_detections.append({
                    'bbox': box.cpu().numpy(),
                    'confidence': confidence,
                    'class': class_name,
                    'source': 'yolo'
                })
    
    # Add depth-based detections
    for obj in depth_objects:
        combined_detections.append({
            'bbox': obj['bbox'],
            'confidence': obj['confidence'],
            'class': obj['class'],
            'source': 'depth',
            'depth_score': obj['depth_score']
        })
    
    return combined_detections

def draw_combined_detections(image, detections):
    """Draw all detections on the image with different colors for different sources"""
    result_image = image.copy()
    
    for detection in detections:
        bbox = detection['bbox']
        confidence = detection['confidence']
        class_name = detection['class']
        source = detection.get('source', 'unknown')
        
        x1, y1, x2, y2 = map(int, bbox)
        
        # Different colors for different sources
        if source == 'yolo':
            color = (0, 255, 0)  # Green for YOLO
            thickness = 2
        else:  # depth
            color = (255, 0, 255)  # Magenta for depth-based
            thickness = 2
        
        # Draw bounding box
        cv2.rectangle(result_image, (x1, y1), (x2, y2), color, thickness)
        
        # Draw label
        label = f"{class_name}: {confidence:.2f}"
        cv2.putText(result_image, label, (x1, y1-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    return result_image

def main():
    print("Loading YOLO model...")
    model = YOLO(MODEL_PATH)
    
    print("Loading depth estimator...")
    depth_estimator = load_depth_estimator()
    
    print("Reading image...")
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        raise FileNotFoundError(f'Could not load image: {IMAGE_PATH}')
    
    print("Running YOLO inference...")
    start_time = time.time()
    yolo_results = model(img, conf=0.1, verbose=False)  # Lower confidence threshold
    yolo_time = time.time() - start_time
    
    print("Getting depth map...")
    depth_start = time.time()
    depth_map = get_depth_map(img, depth_estimator)
    depth_time = time.time() - depth_start
    
    print("Finding depth-based objects...")
    depth_objects = find_depth_based_objects(depth_map, yolo_results, img.shape)
    
    print("Combining detections...")
    combined_detections = combine_detections(yolo_results, depth_objects)
    
    print("Drawing results...")
    result_image = draw_combined_detections(img, combined_detections)
    
    # Save result
    cv2.imwrite(OUTPUT_IMAGE, result_image)
    
    total_time = time.time() - start_time
    
    # Print results
    print(f"\n=== DEPTH-ENHANCED DETECTION RESULTS ===")
    print(f"YOLO inference time: {yolo_time:.2f}s")
    print(f"Depth estimation time: {depth_time:.2f}s")
    print(f"Total time: {total_time:.2f}s")
    print(f"YOLO detections: {len([d for d in combined_detections if d['source'] == 'yolo'])}")
    print(f"Depth-based detections: {len([d for d in combined_detections if d['source'] == 'depth'])}")
    print(f"Total detections: {len(combined_detections)}")
    print(f"Results saved to: {OUTPUT_IMAGE}")
    
    # Print detection details
    print("\n=== DETECTION DETAILS ===")
    for i, detection in enumerate(combined_detections):
        source = detection['source']
        class_name = detection['class']
        confidence = detection['confidence']
        bbox = detection['bbox']
        print(f"{i+1}. {class_name} ({source}): {confidence:.3f} at {bbox}")

if __name__ == "__main__":
    main() 