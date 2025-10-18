# Frontend Hardcoded Room System

This system provides predefined data for specific room images, bypassing the backend ML pipeline for faster, consistent results.

## How It Works

When an image is uploaded with one of these specific filenames:
- `sv-dorm.jpg` - Dorm room with assorted items, furniture, electronics, etc.
- `room3.jpg` - Living space with furniture, decor, electronics, etc.  
- `arnav-hotel.jpeg` - Bedroom with bed frame, built-ins, decor, etc.

The frontend will:
1. **Detect** the hardcoded filename before making any backend calls
2. **Return** predefined data instantly (no network request)
3. **Skip** the backend ML pipeline entirely
4. **Flag** the response as `hardcoded: true`

## File Structure

```
frontend/src/
├── lib/
│   └── hardcodedRooms.ts        # Hardcoded room data and logic
├── components/
│   └── HardcodedRoomDemo.tsx    # Demo component
├── app/
│   ├── upload/
│   │   └── page.tsx             # Updated upload page with hardcoded logic
│   └── test-hardcoded/
│       └── page.tsx             # Test page for hardcoded functionality
```

## Usage

### In Upload Page
The upload page automatically checks for hardcoded rooms:

```typescript
// Check for hardcoded rooms first
if (files.length === 1) {
  const filename = files[0].name;
  if (isHardcodedRoom(filename)) {
    const hardcodedResult = getHardcodedResponse(filename);
    // Use hardcoded data instead of calling backend
    return;
  }
}
// Only call backend if not hardcoded
```

### Direct Usage
```typescript
import { isHardcodedRoom, getHardcodedResponse } from '@/lib/hardcodedRooms';

// Check if filename is hardcoded
const isHardcoded = isHardcodedRoom('sv-dorm.jpg'); // true

// Get hardcoded data
const result = getHardcodedResponse('sv-dorm.jpg');
// Returns: { items: [...], objects: [...], images: {...}, hardcoded: true, room: 'sv-dorm.jpg' }
```

## Data Structure

Each hardcoded room contains items with:
- `code`: Unique identifier
- `imageAttachment`: Which crop/scene (crop0, crop1, scene, etc.)
- `bbox`: Bounding box coordinates [x1, y1, x2, y2]
- `name`: Item name
- `category`: Item category (Furniture, Electronic, Decor, etc.)
- `price_usd`: Price in USD
- `description`: Brief description

## Testing

### Test Page
Visit `/test-hardcoded` to see the demo component in action.

### Manual Testing
1. Upload an image named `sv-dorm.jpg`, `room3.jpg`, or `arnav-hotel.jpeg`
2. Check browser console for "🏠 Hardcoded room detected" message
3. Verify instant response without backend call

## Benefits

- **⚡ Instant Response**: No network latency or ML processing time
- **🎯 Consistent Results**: Same data every time
- **🎪 Demo Ready**: Perfect for presentations and demos
- **🛡️ Fallback System**: Works when backend is down
- **💰 Cost Effective**: No ML API calls for hardcoded rooms
- **🔧 Easy to Extend**: Add new rooms by updating the data object

## Adding New Rooms

1. **Add room data** in `hardcodedRooms.ts`:
   ```typescript
   const hardcodedRooms: Record<string, HardcodedItem[]> = {
     "sv-dorm.jpg": [...],
     "room3.jpg": [...],
     "arnav-hotel.jpeg": [...],
     "new-room.jpg": [...] // Add new room
   };
   ```

2. **Test the new room** using the demo component

## Response Format

Hardcoded responses match the backend format:
```json
{
  "items": [...],
  "objects": [...],
  "images": {...},
  "hardcoded": true,
  "room": "sv-dorm.jpg"
}
```

The `hardcoded: true` flag indicates this was a predefined response from the frontend.
