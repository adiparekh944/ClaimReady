"""Legacy Supabase job pipeline: video and single-image inventory extraction.

This module backs `api.py`, which is the older job-based API. The frontend
currently calls `geminiserver.py` instead (see docs/cv_upgrade_plan.md for the
deployment audit), so this path is retained for compatibility rather than being
the primary route.

The video path here was upgraded to use `vision.tracking.VideoInventoryTracker`,
which adds appearance-based re-identification on top of the YOLO tracker so that
an object losing its tracker ID does not become a duplicate inventory entry.
Unlike the image pipeline in `geminiserver.py`, this path deliberately keeps
YOLO's class labels, because its inventory keys and pricing prior are built from
them.
"""

import os
import sys
import uuid
from collections import defaultdict
from datetime import datetime

import cv2
from dotenv import load_dotenv
from supabase import Client, create_client
from ultralytics import YOLO

from FurniturePriceEstimator import FurniturePriceEstimator
from vision.config import load_config
from vision.tracking import VideoInventoryTracker

# Load environment variables from .env file
load_dotenv()

# Supabase configuration.
#
# These were previously hardcoded in this file, including a service_role key
# that bypasses row-level security. That key is in git history and should be
# rotated. Credentials now come from the environment only.
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_SERVICE_KEY "
        "in the environment or backend/.env"
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Detector weights for the video path. This is a detection checkpoint, not a
# segmentation one, because the video path uses boxes and class labels but no
# masks.
VIDEO_MODEL_PATH = os.environ.get("VIDEO_MODEL_PATH", "yolo11l.pt")

# Frames are sampled down to this rate. Objects persist across many frames, so
# processing every frame of a 30 FPS clip adds compute without adding
# information.
VIDEO_TARGET_FPS = float(os.environ.get("VIDEO_TARGET_FPS", 20.0))


def process_video(video_path, job_id, db, show_display=False):
    """Build a de-duplicated inventory from a video and record it in Supabase.

    Identity comes from `vision.association.InventoryMemoryBank` rather than
    raw tracker IDs. The tracker handles frame-to-frame continuity; CLIP
    appearance descriptors handle identity across occlusions and re-entries, so
    panning away from a sofa and back does not count it twice.

    The returned metadata shape is unchanged from the original implementation:
    a dict keyed by `"<class>_<n>"` whose values carry `class`, `track_id`,
    `confidence`, `first_seen_frame`, `public_url`, `best_confidence`,
    `snapshot_frame`, `estimated_name` and `estimated_price`.

    Args:
        video_path: Path or URL accepted by `cv2.VideoCapture`.
        job_id: Supabase job to update.
        db: `SupaDB` instance.
        show_display: Accepted for signature compatibility. Rendering windows
            was already disabled unconditionally in the original code and does
            not work in a headless container, so it is ignored.
    """
    print(f"process_video: {video_path}")
    price_estimator = FurniturePriceEstimator()

    config = load_config()
    tracker = VideoInventoryTracker(config, model_path=VIDEO_MODEL_PATH)
    result = tracker.process_video(video_path, target_fps=VIDEO_TARGET_FPS)

    association = result.association
    print(
        f"Tracked {result.frames_processed} frames: "
        f"{association.get('generated_track_ids')} tracker IDs collapsed into "
        f"{result.confirmed_count} confirmed items "
        f"({association.get('reid_events')} re-identification events, "
        f"{association.get('id_switches_absorbed')} ID switches absorbed)"
    )

    # Upload the best crop per item and price it.
    print("\nUploading best snapshots of detected items to Supabase...")
    item_metadata = {}
    class_counts = defaultdict(int)

    for item in result.items:
        if item.best_crop is None or item.best_crop.size == 0:
            # An item with no usable crop cannot be priced or displayed, so it
            # is dropped rather than recorded without an image.
            print(f"Skipping item {item.item_id} ({item.dominant_label}): no usable crop")
            continue

        class_name = item.dominant_label or "object"
        class_counts[class_name] += 1
        item_count = class_counts[class_name]
        item_id = f"{class_name}_{item_count}"
        primary_track_id = item.track_ids[0] if item.track_ids else item.item_id

        try:
            public_url = upload_snapshot_to_supabase(
                item.best_crop,
                class_name,
                primary_track_id,
                item.best_confidence,
                item.best_frame,
                item_count,
                job_id,
            )
        except Exception as e:
            print(f"Error uploading snapshot for {item_id}: {e}")
            continue

        estimated_name, estimated_price = class_name, None
        try:
            ok, buffer = cv2.imencode(".jpg", item.best_crop)
            if not ok or buffer is None:
                raise ValueError("Failed to encode crop to JPEG")
            estimated_name, estimated_price = price_estimator.analyze_item_with_gemini(buffer.tobytes())
        except Exception as e:
            print(f"Error estimating price for {item_id}: {e}")

        item_metadata[item_id] = {
            "class": class_name,
            "track_id": int(primary_track_id),
            "confidence": float(item.best_confidence),
            "first_seen_frame": int(item.first_seen_frame),
            "public_url": public_url,
            "best_confidence": float(item.best_confidence),
            "snapshot_frame": int(item.best_frame),
            "estimated_name": estimated_name,
            "estimated_price": estimated_price,
            # Additive provenance: how many tracker IDs this single physical
            # item was seen under, and how often appearance recovered it.
            "track_ids": [int(t) for t in item.track_ids],
            "reid_events": int(item.reid_events),
            "frames_seen": int(item.frames_seen),
        }

        print(f"Uploaded snapshot of {item_id} -> {public_url}")
        if estimated_price is not None:
            print(f"Estimated price: ${float(estimated_price):,.2f} ({estimated_name})")

    total_value = sum(
        float(data["estimated_price"] or 0)
        for data in item_metadata.values()
        if data.get("estimated_price") is not None
    )

    print("\nFinal Items Inventory:")
    for class_name, count in sorted(class_counts.items()):
        entries = [d for d in item_metadata.values() if d["class"] == class_name]
        if not entries:
            continue
        print(f"{class_name}: {len(entries)} items")
        for data in entries:
            price = data.get("estimated_price")
            if price is not None:
                print(f"  - {data['estimated_name']}: ${float(price):,.2f}")
            else:
                print(f"  - {data['estimated_name']}: Price not available")

    print(f"\nTotal unique items with snapshots: {len(item_metadata)}")
    print(f"Total estimated value: ${total_value:,.2f}")

    db.complete_job(job_id, total_value, len(item_metadata), item_metadata)
    return


def upload_snapshot_to_supabase(
    snapshot, class_name, track_id, conf, frame_number, item_count, job_id, user_id=None
):
    """Upload a snapshot to Supabase storage and return the public URL.

    Args:
        user_id: Owner recorded on the `file_uploads` row. Previously this
            function referenced an undefined `user_id` global, so the metadata
            insert raised `NameError` and every upload failed at the last step.
            It is now an explicit optional parameter.
    """
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
                'user_id': user_id,  # Use the user_id from the request, not a placeholder
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
    """Detect objects in one image and estimate their values.

    Legacy, class-based path. This is deliberately *not* routed through
    `vision.pipeline.VisionPipeline`: it keys its inventory by YOLO class name
    (`"chair_1"`, `"chair_2"`), which the class-agnostic pipeline cannot
    provide because it discards labels by design.

    The class-agnostic pipeline plus multimodal identification, which is
    strictly better for inventory, is reached through
    `geminiserver.py:/api/analyze-image` — the route the frontend actually
    calls. This function remains only so `api.py`'s job-based flow keeps
    working.
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
