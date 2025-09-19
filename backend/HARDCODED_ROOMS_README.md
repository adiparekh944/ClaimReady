# Hardcoded Room System

This system provides predefined data for specific room images, bypassing the ML pipeline for faster, consistent results.

## How It Works

When an image is uploaded with one of these specific filenames:
- `svdorm.jpg` - Dorm room with assorted items, furniture, electronics, etc.
- `room3.jpg` - Living space with furniture, decor, electronics, etc.  
- `arnavroom.jpg` - Bedroom with bed frame, built-ins, decor, etc.

The system will:
1. **Detect** the hardcoded filename
2. **Skip** the YOLO + Gemini ML pipeline
3. **Return** predefined data from CSV files
4. **Flag** the response as `hardcoded: true`

## File Structure

```
backend/
├── hardcoded_data/
│   ├── svdorm_data.csv    # Dorm room data
│   ├── room3_data.csv     # Living space data
│   └── arnavroom_data.csv # Bedroom data
├── hardcoded_lookup.py   # Lookup system
├── test_hardcoded.py     # Test script
└── test_api_hardcoded.py # API test script
```

## CSV Data Format

Each CSV file contains columns:
- `code`: Unique identifier for the item
- `imageAttachment`: Which crop/scene the item belongs to
- `bbox_x1, bbox_y1, bbox_x2, bbox_y2`: Bounding box coordinates
- `name`: Item name
- `category`: Item category (Furniture, Appliances, etc.)
- `price_usd`: Estimated price in USD
- `description`: Brief description

## Usage

### Single Image API
```bash
curl -X POST http://localhost:8080/api/analyze-image \
  -F "image=@svdorm.jpg"
```

### Multiple Images API
```json
{
  "images": ["base64_image1", "base64_image2"],
  "filenames": ["svdorm.jpg", "room3.jpg"]
}
```

## Testing

### Test the lookup system:
```bash
cd backend
python test_hardcoded.py
```

### Test the API (with server running):
```bash
cd backend
python test_api_hardcoded.py
```

## Adding New Rooms

1. **Create CSV file** in `hardcoded_data/` directory
2. **Add mapping** in `hardcoded_lookup.py`:
   ```python
   self.room_mappings = {
       "svdorm.jpg": "svdorm_data.csv",
       "room3.jpg": "room3_data.csv", 
       "arnavroom.jpg": "arnavroom_data.csv",
       "newroom.jpg": "newroom_data.csv"  # Add new room
   }
   ```

## Benefits

- **Fast Response**: No ML processing time
- **Consistent Results**: Same data every time
- **Demo Ready**: Perfect for presentations
- **Fallback System**: Works when ML fails
- **Easy Testing**: Predictable outputs

## Response Format

Hardcoded responses include the same format as ML responses:
```json
{
  "status": "success",
  "items": [...],
  "objects": [...],
  "images": {...},
  "total_items": 5,
  "total_value": 2029.95,
  "hardcoded": true
}
```

The `hardcoded: true` flag indicates this was a predefined response.
