import sys
import os
from ultralytics import YOLO
import cv2
from collections import defaultdict
import json
import shutil
from FurniturePriceEstimator import FurniturePriceEstimator
from supabase import create_client, Client
import uuid
from datetime import datetime
from dotenv import load_dotenv
import numpy as np # Added for test_yolo_model

# Load environment variables from .env file
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials. Please check your .env file.")

supabase: Client = create_client(
    SUPABASE_URL, 
    SUPABASE_KEY
)

def test_yolo_model():
    """Test function to verify YOLO model is working correctly"""
    print("=== TESTING YOLO MODEL ===")
    try:
        # Test model loading
        model = YOLO('yolov8n.pt')
        print("✓ YOLO model loaded successfully")
        
        # Create a simple test image (white rectangle on black background)
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(test_image, (100, 100), (300, 300), (255, 255, 255), -1)
        
        # Run detection
        results = model(test_image, conf=0.1)  # Very low confidence for testing
        
        print(f"✓ Model inference completed")
        print(f"Results type: {type(results)}")
        print(f"Number of results: {len(results)}")
        
        if len(results) > 0 and results[0].boxes is not None:
            print(f"✓ Detections found: {len(results[0].boxes)}")
            if hasattr(results[0].boxes, 'cls') and results[0].boxes.cls is not None:
                cls_ids = results[0].boxes.cls.cpu().numpy().astype(int)
                class_names = results[0].names
                detected_classes = [class_names[cls_id] for cls_id in cls_ids]
                print(f"✓ Detected classes: {detected_classes}")
        else:
            print("⚠ No detections in test image (this is normal for a simple test)")
        
        print("✓ YOLO model test completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ YOLO model test failed: {str(e)}")
        return False

def process_video(video_path, job_id, db, show_display, fast_mode=False):
    print(f"process_video: {video_path}")
    print(f"Fast mode: {fast_mode}")

    # DIAGNOSTIC: Test YOLO model first
    if not test_yolo_model():
        print("ERROR: YOLO model test failed. Cannot proceed with video processing.")
        return

    # Configuration variables that can be imported from other files
    hide_display = not show_display  # Set to True to hide bounding boxes, labels, and inventory display
    hide_display = True #was false 
    # Initialize FurniturePriceEstimator only if not in fast mode
    price_estimator = None
    if not fast_mode:
        price_estimator = FurniturePriceEstimator()

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file '{video_path}'.")
        print("Tips:")
        print(" - Try converting your video to .mp4 (H.264) format.")
        print(" - Check permissions and file integrity.")
        print(" - Try a different video file.")
        sys.exit(1)

    # REVERT: Use original large YOLO model
    model = YOLO('yolo11l.pt')
    model_img_size = 640  # REVERT: Use default 640

    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # REVERT: Process every frame
    frame_skip = 1
    new_fps = fps / frame_skip

    print(f"Original video: {width}x{height}, {fps} FPS, {total_frames} frames")
    print(f"Processing at: {new_fps:.1f} FPS (every {frame_skip} frames)")
    print(f"Using YOLOv8l model with {model_img_size}x{model_img_size} input size")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('fullOutputVideo.mp4', fourcc, fps, (width, height))

    object_counts = defaultdict(int)
    tracked_objects = {}
    track_history = {}
    min_frames_to_count = 3  # REVERT: Original value
    max_consecutive_misses = 5
    confidence_threshold = 0.55  # REVERT: Original value
    iou_threshold = 0.45
    snapshot_confidence_threshold = 0.55  # REVERT: Original value
    best_snapshots = {}
    excluded_classes = ['person']
    item_metadata = {}

    def calculate_iou(box1, box2):
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0
        area_i = (x2_i - x1_i) * (y2_i - y1_i)
        return area_i / (area1 + area2 - area_i)

    frame_count = 0
    processed_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        print(f"frame_count: {frame_count}")
        frame_count += 1
        if (frame_count - 1) % frame_skip != 0:
            continue
        processed_count += 1
        if processed_count % 10 == 0:
            progress = (frame_count / total_frames) * 100
            print(f"Processing: {progress:.1f}% (frame {frame_count}/{total_frames})")
        results = model.track(
            frame, 
            persist=True, 
            conf=confidence_threshold, 
            iou=iou_threshold, 
            imgsz=model_img_size
        )
        current_tracks = set()
        if results[0].boxes is not None and hasattr(results[0].boxes, 'id') and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            cls_ids = results[0].boxes.cls.cpu().numpy().astype(int)
            confs = results[0].boxes.conf.cpu().numpy()
            class_names = results[0].names
            for i, (box, track_id, cls_id, conf) in enumerate(zip(boxes, track_ids, cls_ids, confs)):
                class_name = class_names[cls_id]
                if class_name in excluded_classes:
                    continue
                current_tracks.add(track_id)
                if track_id not in track_history:
                    track_history[track_id] = {
                        'frames_seen': 0,
                        'consecutive_misses': 0,
                        'class_counts': defaultdict(int),
                        'counted': False,
                        'box_history': []
                    }
                track_history[track_id]['frames_seen'] += 1
                track_history[track_id]['consecutive_misses'] = 0
                track_history[track_id]['class_counts'][class_name] += 1
                track_history[track_id]['box_history'].append(box)
                if len(track_history[track_id]['box_history']) > 10:
                    track_history[track_id]['box_history'] = track_history[track_id]['box_history'][-10:]
                most_common_class = max(track_history[track_id]['class_counts'].items(), key=lambda x: x[1])[0]
                if track_history[track_id]['frames_seen'] >= min_frames_to_count and not track_history[track_id]['counted']:
                    track_history[track_id]['counted'] = True
                    tracked_objects[track_id] = most_common_class
                    object_counts[most_common_class] += 1
                    item_id = f"{most_common_class}_{object_counts[most_common_class]}"
                    item_metadata[item_id] = {
                        "class": most_common_class,
                        "track_id": int(track_id),
                        "confidence": float(conf),
                        "first_seen_frame": frame_count,
                        "snapshot_path": None,
                        "estimated_value": None
                    }
                if (track_id not in best_snapshots or conf > best_snapshots[track_id]["conf"]) and \
                conf >= snapshot_confidence_threshold and \
                track_history[track_id]['frames_seen'] >= min_frames_to_count:
                    x1, y1, x2, y2 = box
                    margin_x = int((x2 - x1) * 0.1)
                    margin_y = int((y2 - y1) * 0.1)
                    x1_margin = max(0, x1 - margin_x)
                    y1_margin = max(0, y1 - margin_y)
                    x2_margin = min(width, x2 + margin_x)
                    y2_margin = min(height, y2 + margin_y)
                    object_snapshot = frame[y1_margin:y2_margin, x1_margin:x2_margin].copy()
                    if object_snapshot.size > 0:
                        best_snapshots[track_id] = {
                            "conf": conf,
                            "saved": False,
                            "class": most_common_class,
                            "snapshot": object_snapshot,
                            "frame_number": frame_count
                        }
                if not hide_display:
                    color = (0, 255, 0)
                    if track_history[track_id]['frames_seen'] < min_frames_to_count:
                        color = (0, 165, 255)
                    elif track_history[track_id]['counted']:
                        color = (0, 255, 0)
                    x1, y1, x2, y2 = box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    label = f"{most_common_class} #{track_id} {conf:.2f} ({track_history[track_id]['frames_seen']})"
                    cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        tracks_to_remove = []
        for track_id in track_history:
            if track_id not in current_tracks:
                track_history[track_id]['consecutive_misses'] += 1
                if track_history[track_id]['consecutive_misses'] > max_consecutive_misses:
                    tracks_to_remove.append(track_id)
        for track_id in tracks_to_remove:
            del track_history[track_id]
        if not hide_display:
            y_pos = 30
            cv2.putText(frame, f"Frame: {frame_count}", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            y_pos += 30
            cv2.putText(frame, "Items Inventory:", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            y_pos += 30
            for cls, count in sorted(object_counts.items()):
                cv2.putText(frame, f"{cls}: {count}", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                y_pos += 30
            cv2.imshow('Insurance Item Tracking', frame)
            out.write(frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    max_items_for_pricing = 10
    print("\nUploading best snapshots of detected items to Supabase...")
    items_processed = 0
    for track_id, snapshot_info in best_snapshots.items():
        if track_id in tracked_objects and not snapshot_info["saved"] and items_processed < max_items_for_pricing:
            class_name = snapshot_info["class"]
            item_count = sum(1 for t_id, cls in tracked_objects.items() if cls == class_name and t_id <= track_id)
            try:
                public_url = upload_snapshot_to_supabase(
                    snapshot_info["snapshot"],
                    class_name,
                    track_id,
                    snapshot_info['conf'],
                    snapshot_info['frame_number'],
                    item_count,
                    job_id
                )
                snapshot_info["saved"] = True
                snapshot_info["public_url"] = public_url
                if not fast_mode and price_estimator:
                    try:
                        _, buffer = cv2.imencode('.jpg', snapshot_info["snapshot"])
                        if buffer is None:
                            raise ValueError("Failed to encode image to JPEG format")
                        image_bytes = buffer.tobytes()
                        name, price = price_estimator.analyze_item_with_gemini(image_bytes)
                        snapshot_info["estimated_name"] = name
                        snapshot_info["estimated_price"] = price
                    except Exception as e:
                        print(f"Error estimating price for {class_name} (ID: {track_id}): {str(e)}")
                        snapshot_info["estimated_name"] = class_name
                        snapshot_info["estimated_price"] = None
                else:
                    snapshot_info["estimated_name"] = class_name
                    snapshot_info["estimated_price"] = None
                item_id = f"{class_name}_{item_count}"
                if item_id in item_metadata:
                    item_metadata[item_id]["public_url"] = public_url
                    item_metadata[item_id]["best_confidence"] = float(snapshot_info["conf"])
                    item_metadata[item_id]["snapshot_frame"] = int(snapshot_info["frame_number"])
                    item_metadata[item_id]["estimated_name"] = snapshot_info["estimated_name"]
                    item_metadata[item_id]["estimated_price"] = snapshot_info["estimated_price"]
                print(f"Uploaded snapshot of {class_name} (ID: {track_id}) to Supabase")
                print(f"Public URL: {public_url}")
                if not fast_mode and snapshot_info["estimated_price"] is not None:
                    print(f"Estimated price: ${snapshot_info['estimated_price']:,.2f} ({snapshot_info['estimated_name']})")
                elif fast_mode:
                    print(f"Fast mode: Skipped price estimation for {class_name}")
                items_processed += 1
            except Exception as e:
                print(f"Error processing snapshot for {class_name} (ID: {track_id}): {str(e)}")
                continue
    filtered_metadata = {}
    for item_id, data in item_metadata.items():
        if data.get("public_url") is not None:
            filtered_metadata[item_id] = data
    print("\nFinal Items Inventory:")
    snapshot_count = 0
    class_counts = defaultdict(int)
    total_value = 0.0
    for item_id, data in filtered_metadata.items():
        class_name = data["class"]
        class_counts[class_name] += 1
        snapshot_count += 1
        if data.get("estimated_price") is not None:
            total_value += float(data["estimated_price"] or 0)
    for class_name, count in sorted(class_counts.items()):
        items = [item for item in filtered_metadata.values() if item["class"] == class_name]
        valid_prices = [float(item.get("estimated_price", 0)) for item in items if item.get("estimated_price") is not None]
        avg_price = sum(valid_prices) / len(valid_prices) if valid_prices else 0
        print(f"{class_name}: {count} items")
        for item in items:
            price = item.get("estimated_price")
            if price is not None:
                print(f"  - {item['estimated_name']}: ${float(price):,.2f}")
            else:
                print(f"  - {item['estimated_name']}: Price not available")
    print(f"\nTotal unique items with snapshots: {snapshot_count}")
    if not fast_mode:
        print(f"Total estimated value: ${total_value:,.2f}")
    else:
        print(f"Fast mode: Price estimation skipped")
    print(f"Snapshots uploaded: {snapshot_count}")
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    db.complete_job(job_id, total_value, len(filtered_metadata), filtered_metadata)
    return

def upload_snapshot_to_supabase(snapshot, class_name, track_id, conf, frame_number, item_count, job_id):
    """Upload a snapshot to Supabase storage and return the public URL."""
    try:
        # Convert OpenCV image to bytes
        _, buffer = cv2.imencode('.jpg', snapshot)
        if buffer is None:
            raise ValueError("Failed to encode image to JPEG format")
            
        file_data = buffer.tobytes()
        
        # Generate unique filename
        unique_prefix = f"{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:7]}"
        snapshot_filename = f"{class_name}_{item_count}_id{track_id}_conf{conf:.2f}_frame{frame_number}.jpg"
        unique_filename = f"{unique_prefix}-{snapshot_filename}"
        
        # Create safe path structure
        formatted_date = datetime.now().strftime("%Y%m%d")
        file_path = f"{formatted_date}/{unique_filename}"
        
        # Upload to Supabase Storage
        bucket_name = "file-upload"
        try:
            storage_response = supabase.storage.from_(bucket_name).upload(
                file_path,
                file_data,
                {
                    "cache-control": "3600",
                    "content-type": "image/jpeg"
                }
            )
        except Exception as e:
            raise Exception(f"Failed to upload to Supabase storage: {str(e)}")
        
        # Get the public URL
        try:
            public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
        except Exception as e:
            raise Exception(f"Failed to get public URL: {str(e)}")
        
        # Save file metadata to database
        try:
            table_response = supabase.table('file_uploads').insert({
                'user_id': "66274d9c-6ece-4eeb-a8ed-19051a8a2103",  # Placeholder user ID
                'file_name': unique_filename,
                'original_name': snapshot_filename,
                'file_size': len(file_data),
                'file_type': 'image/jpeg',
                'file_path': file_path,
                'public_url': public_url,
                'data_type': 'photo',
                'job_id': job_id
            }).execute()
        except Exception as e:
            raise Exception(f"Failed to save metadata to database: {str(e)}")
        
        return public_url
        
    except Exception as e:
        print(f"Error uploading snapshot to Supabase: {str(e)}")
        raise

def process_image(image_path, job_id, db, show_display=False):
    """
    Process a single image to detect objects and estimate their values.
    Similar to process_video but optimized for single image processing.
    """
    print(f"process_image: {image_path}")

    # Configuration variables
    hide_display = not show_display
    hide_display = True  # Set to True to hide bounding boxes and labels
    
    # Initialize FurniturePriceEstimator
    price_estimator = FurniturePriceEstimator()

    # Load the image
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"Error: Could not load image file '{image_path}'.")
        return None

    # Get image properties
    height, width = frame.shape[:2]
    print(f"Image: {width}x{height}")

    # Load YOLO model
    model = YOLO('yolo11l.pt')

    # Configuration for image processing
    confidence_threshold = 0.55
    snapshot_confidence_threshold = 0.55
    
    # Classes to exclude (don't track these)
    excluded_classes = ['person']

    # Dictionary to store unique object counts
    object_counts = defaultdict(int)
    detected_objects = {}

    # Metadata for items (to be used with Gemini API)
    item_metadata = {}

    # Run YOLOv8 detection on the image
    results = model(
        frame, 
        conf=confidence_threshold, 
        imgsz=640
    )
    
    # Process detections
    if results[0].boxes is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
        cls_ids = results[0].boxes.cls.cpu().numpy().astype(int)
        confs = results[0].boxes.conf.cpu().numpy()
        
        # Get class names
        class_names = results[0].names
        
        # Process each detection
        for i, (box, cls_id, conf) in enumerate(zip(boxes, cls_ids, confs)):
            class_name = class_names[cls_id]
            
            # Skip excluded classes (like person)
            if class_name in excluded_classes:
                continue
            
            # Count the object
            object_counts[class_name] += 1
            object_id = f"{class_name}_{object_counts[class_name]}"
            detected_objects[object_id] = class_name
            
            # Initialize item metadata
            item_metadata[object_id] = {
                "class": class_name,
                "confidence": float(conf),
                "snapshot_path": None,
                "estimated_value": None,
                "estimated_name": None
            }
            
            # Extract the object region with a small margin
            x1, y1, x2, y2 = box
            # Add margin (10% of width/height)
            margin_x = int((x2 - x1) * 0.1)
            margin_y = int((y2 - y1) * 0.1)
            # Ensure coordinates are within frame boundaries
            x1_margin = max(0, x1 - margin_x)
            y1_margin = max(0, y1 - margin_y)
            x2_margin = min(width, x2 + margin_x)
            y2_margin = min(height, y2 + margin_y)
            
            # Extract the object snapshot
            object_snapshot = frame[y1_margin:y2_margin, x1_margin:x2_margin].copy()
            
            # Only proceed if the snapshot is not empty and confidence is high enough
            if object_snapshot.size > 0 and conf >= snapshot_confidence_threshold:
                try:
                    # Upload snapshot to Supabase
                    public_url = upload_snapshot_to_supabase(
                        object_snapshot,
                        class_name,
                        i,  # Use index as track_id for images
                        conf,
                        1,  # Frame number is always 1 for images
                        object_counts[class_name],
                        job_id
                    )
                    
                    # Estimate price for the item using in-memory image data
                    try:
                        # Convert OpenCV image to bytes
                        _, buffer = cv2.imencode('.jpg', object_snapshot)
                        if buffer is None:
                            raise ValueError("Failed to encode image to JPEG format")
                        image_bytes = buffer.tobytes()
                        
                        name, price = price_estimator.analyze_item_with_gemini(image_bytes)
                        
                        # Update metadata
                        item_metadata[object_id]["public_url"] = public_url
                        item_metadata[object_id]["estimated_name"] = name
                        item_metadata[object_id]["estimated_price"] = price
                        item_metadata[object_id]["best_confidence"] = float(conf)
                        
                        print(f"Detected {class_name} -> {name}: ${price:,.2f}")
                        
                    except Exception as e:
                        print(f"Error estimating price for {class_name}: {str(e)}")
                        item_metadata[object_id]["public_url"] = public_url
                        item_metadata[object_id]["estimated_name"] = class_name
                        item_metadata[object_id]["estimated_price"] = None
                        item_metadata[object_id]["best_confidence"] = float(conf)
                        
                except Exception as e:
                    print(f"Error processing snapshot for {class_name}: {str(e)}")
                    continue
            
            # Draw bounding box if display is enabled
            if not hide_display:
                color = (0, 255, 0)  # Green for detected objects
                x1, y1, x2, y2 = box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Display class name and confidence
                label = f"{class_name} {conf:.2f}"
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Display object counts on the image if display is enabled
        if not hide_display:
            y_pos = 30
            cv2.putText(frame, "Detected Items:", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            y_pos += 30
            
            for cls, count in sorted(object_counts.items()):
                cv2.putText(frame, f"{cls}: {count}", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                y_pos += 30
            
            # Show the image
            cv2.imshow('Image Object Detection', frame)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    # Filter metadata to only include items with snapshots
    filtered_metadata = {}
    for item_id, data in item_metadata.items():
        if data.get("public_url") is not None:
            filtered_metadata[item_id] = data

    # Print final inventory
    print("\nFinal Items Inventory:")
    snapshot_count = 0
    class_counts = defaultdict(int)
    total_value = 0.0

    # Count only items with snapshots
    for item_id, data in filtered_metadata.items():
        class_name = data["class"]
        class_counts[class_name] += 1
        snapshot_count += 1
        if data.get("estimated_price") is not None:
            total_value += float(data["estimated_price"] or 0)

    # Print counts by class with prices
    for class_name, count in sorted(class_counts.items()):
        items = [item for item in filtered_metadata.values() if item["class"] == class_name]
        print(f"{class_name}: {count} items")
        for item in items:
            price = item.get("estimated_price")
            if price is not None:
                print(f"  - {item['estimated_name']}: ${float(price):,.2f}")
            else:
                print(f"  - {item['estimated_name']}: Price not available")

    print(f"\nTotal unique items with snapshots: {snapshot_count}")
    print(f"Total estimated value: ${total_value:,.2f}")
    print(f"Snapshots uploaded: {snapshot_count}")

    # Update job on supabase
    db.complete_job(job_id, total_value, len(filtered_metadata), filtered_metadata)

    return filtered_metadata
