# JSON Response Examples

## ✅ Successful Response (with verification)

```json
{
  "items": [
    {
      "code": "0",
      "name": "Gaming Laptop",
      "category": "Electronics",
      "brand": "Dell",
      "condition": "Good",
      "price_usd": 1200.0,
      "description": "High-performance gaming laptop with RTX graphics",
      "verificationScore": 0.85,
      "verificationNotes": "Good visual match with clear laptop features visible",
      "overallScore": 0.83,
      "bbox": [100, 100, 300, 200],
      "source_image": 0
    },
    {
      "code": "1",
      "name": "Office Chair",
      "category": "Furniture",
      "brand": "Herman Miller",
      "condition": "Excellent",
      "price_usd": 450.0,
      "description": "Ergonomic office chair with lumbar support",
      "verificationScore": 0.92,
      "verificationNotes": "Excellent match - chair clearly visible with distinctive features",
      "overallScore": 0.89,
      "bbox": [50, 150, 250, 350],
      "source_image": 0
    }
  ],
  "total_items": 2,
  "total_value": 1650.0,
  "images": {
    "0": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
  },
  "status": "success"
}
```

## ✅ Legacy Response (without verification - graceful fallback)

```json
{
  "items": [
    {
      "code": "0",
      "name": "Coffee Table",
      "category": "Furniture",
      "brand": "IKEA",
      "condition": "Good",
      "price_usd": 150.0,
      "description": "Modern wooden coffee table",
      "bbox": [200, 200, 400, 300],
      "source_image": 0
    }
  ],
  "total_items": 1,
  "total_value": 150.0,
  "images": {
    "0": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
  },
  "status": "success"
}
```

## ❌ Error Response (bad MIME type)

```json
{
  "status": "error",
  "error": "Invalid file type. Allowed types: image/jpeg, image/jpg, image/png, image/bmp, image/tiff, image/webp, image/gif",
  "items": [],
  "total_items": 0,
  "total_value": 0
}
```

## ❌ Error Response (file too large)

```json
{
  "status": "error",
  "error": "File too large. Maximum size: 10MB",
  "items": [],
  "total_items": 0,
  "total_value": 0
}
```

## ❌ Error Response (timeout)

```json
{
  "status": "error",
  "error": "Processing timeout. Please try with a smaller image or try again later.",
  "items": [],
  "total_items": 0,
  "total_value": 0
}
```

## 🔍 Frontend Parsing Logic

The frontend handles both response types gracefully:

```typescript
// In upload/page.tsx - response parsing
const result = await response.json();

// Check for verification fields
const itemsWithVerification = result.items.filter(
  (item: any) => item.verificationScore !== undefined
);

// Log verification data
if (itemsWithVerification.length > 0) {
  console.log("🔍 Sample verification data:", {
    name: itemsWithVerification[0].name,
    verificationScore: itemsWithVerification[0].verificationScore,
    verificationNotes: itemsWithVerification[0].verificationNotes,
  });
}
```

## 🎨 Frontend Display Logic

```typescript
// In ItemTable.tsx - verification score display
{
  item.verificationScore !== undefined ? (
    <div className="flex items-center space-x-2">
      <div className="flex-1">
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${
              item.verificationScore >= 0.8
                ? "bg-green-500"
                : item.verificationScore >= 0.6
                ? "bg-yellow-500"
                : item.verificationScore >= 0.4
                ? "bg-orange-500"
                : "bg-red-500"
            }`}
            style={{ width: `${item.verificationScore * 100}%` }}
          ></div>
        </div>
        <div className="text-xs text-gray-600 mt-1">
          {Math.round(item.verificationScore * 100)}%
        </div>
      </div>
      {item.verificationNotes && (
        <div
          className="text-gray-400 cursor-help"
          title={item.verificationNotes}
        >
          ℹ️
        </div>
      )}
    </div>
  ) : (
    <span className="text-gray-400">—</span>
  );
}
```

## 📊 Verification Score Ranges

- **0.9-1.0**: Excellent match (Green) - High confidence
- **0.7-0.8**: Good match (Yellow) - Some uncertainty
- **0.5-0.6**: Moderate match (Orange) - Significant uncertainty
- **0.3-0.4**: Poor match (Red) - Low confidence
- **0.0-0.2**: Very poor match (Red) - No match
