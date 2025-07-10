# Troubleshooting: No Objects Detected

## Common Issues and Solutions

### 1. **Video Quality Issues**
- **Problem**: Poor lighting, blurry video, or objects too small
- **Solution**: 
  - Ensure good lighting (natural light or bright indoor lighting)
  - Keep camera steady
  - Move closer to objects
  - Use higher resolution videos

### 2. **Object Types Not Recognized**
- **Problem**: YOLO model may not recognize specific furniture types
- **Solution**:
  - Try different angles of the same object
  - Include multiple objects in the video
  - Use common household items (chairs, tables, sofas, etc.)

### 3. **Confidence Threshold Too High**
- **Problem**: Current threshold (0.3) may still be too high for your video
- **Solution**: 
  - The diagnostic version now uses lower thresholds
  - Check the logs for detection details

### 4. **Video Format Issues**
- **Problem**: Unsupported video codec or format
- **Solution**:
  - Convert to MP4 (H.264) format
  - Ensure video is not corrupted
  - Try shorter video clips (30 seconds or less)

### 5. **Model Loading Issues**
- **Problem**: YOLO model not loading correctly
- **Solution**:
  - Check Docker logs for model download errors
  - Ensure sufficient disk space
  - Verify internet connection for model download

## Diagnostic Steps

### Step 1: Check the Logs
Look for these diagnostic messages in the backend logs:
```
=== TESTING YOLO MODEL ===
✓ YOLO model loaded successfully
✓ Model inference completed
Frame X: Y detections
Detected classes: ['chair', 'table', ...]
```

### Step 2: Test with Simple Video
1. Create a simple test video with:
   - Clear, well-lit furniture
   - Steady camera movement
   - Common household items (chair, table, sofa)
   - 10-30 seconds duration

### Step 3: Check Video Properties
The logs will show:
```
Original video: 1920x1080, 30.0 FPS, 900 frames
Processing at: 10.0 FPS (every 3 frames)
```

### Step 4: Monitor Detection Counts
Look for:
```
Frame 1: 2 detections
Detected classes: ['chair', 'table']
Detection 0: chair (conf: 0.456, track_id: 1)
COUNTED: chair (track_id: 1, frames_seen: 2)
```

## Expected Behavior

### Normal Detection Process:
1. **Model Loading**: YOLO model loads successfully
2. **Frame Processing**: Each frame is analyzed
3. **Detection**: Objects are detected with confidence scores
4. **Tracking**: Objects are tracked across frames
5. **Counting**: Objects seen in multiple frames are counted
6. **Snapshots**: Best images of objects are saved

### What to Look For:
- **Total detections > 0**: At least some objects detected
- **Tracked objects > 0**: Objects successfully tracked
- **Object counts**: Final count of unique objects
- **Best snapshots > 0**: Images saved for analysis

## Quick Fixes

### If No Detections at All:
1. **Lower confidence threshold** (already done in diagnostic version)
2. **Use larger model**: Change `yolov8n.pt` to `yolo11l.pt` for better accuracy
3. **Increase image size**: Change `model_img_size = 320` to `model_img_size = 640`

### If Some Detections but No Counting:
1. **Lower min_frames_to_count**: Change from 2 to 1
2. **Lower snapshot_confidence_threshold**: Change from 0.4 to 0.3

### If Detections but No Snapshots:
1. **Lower snapshot_confidence_threshold**: Change from 0.4 to 0.3
2. **Check Supabase connection**: Ensure storage is working

## Test Video Recommendations

### Good Test Video:
- 30-second clip
- Clear furniture (chair, table, sofa)
- Good lighting
- Steady camera movement
- Multiple objects visible

### Avoid:
- Very short videos (< 5 seconds)
- Poor lighting
- Moving camera too fast
- Objects too small or far away
- Unusual furniture types

## Debugging Commands

### Check Model:
```python
# In backend/app.py, add this to test_yolo_model():
print(f"Model classes: {model.names}")
print(f"Model device: {model.device}")
```

### Check Video Properties:
```python
# Add to process_video():
print(f"Video format: {cap.get(cv2.CAP_PROP_FORMAT)}")
print(f"Video codec: {cap.get(cv2.CAP_PROP_FOURCC)}")
```

### Test with Different Thresholds:
```python
# Try these confidence thresholds:
confidence_threshold = 0.1  # Very low
confidence_threshold = 0.2  # Low
confidence_threshold = 0.3  # Current diagnostic
confidence_threshold = 0.5  # Medium
confidence_threshold = 0.7  # High
```

## Common Error Messages

### "No such file or directory" for video:
- Check video file path
- Ensure video file exists
- Verify file permissions

### "Could not open video file":
- Check video format (use MP4)
- Verify video is not corrupted
- Try different video file

### "YOLO model test failed":
- Check internet connection
- Verify disk space
- Check Docker logs for download errors

### "No detections in any frame":
- Try different video
- Lower confidence threshold
- Use larger YOLO model
- Check video quality and lighting 