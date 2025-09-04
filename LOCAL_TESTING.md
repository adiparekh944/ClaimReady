# Local Testing Guide

## Backend Testing

### Start Backend

```bash
cd backend
python3 geminiserver.py
```

### Health Check

```bash
curl http://localhost:8080/health
```

Expected: `{"status": "ok"}`

### Image Analysis

```bash
curl -F "image=@./samples/test.jpg" http://localhost:8080/api/analyze-image
```

**Expected JSON Response:**
Each returned item contains the usual producer fields PLUS (optionally):

```json
{
  "items": [
    {
      "code": "0",
      "name": "MacBook Pro",
      "category": "Electronics",
      "brand": "Apple",
      "condition": "Good",
      "price_usd": 2000.0,
      "description": "15-inch MacBook Pro laptop",
      "nullify": false,
      "source_image": 0,
      "namePriceScore": 0.85,
      "namePriceNotes": "Price seems reasonable for a MacBook Pro, name matches visible Apple logo"
    }
  ],
  "total_items": 1,
  "images": {
    "0": "data:image/jpeg;base64,..."
  }
}
```

## Frontend Testing

### Start Frontend

```bash
cd frontend
npm run dev
```

### Test Upload Page

1. Navigate to `/upload`
2. Add an image file
3. Confirm the following in the results table:
   - **New "Name/Price Score" column** is present
   - **Score display**: Shows percentages (e.g., "85%") when `namePriceScore` is available
   - **Color coding**:
     - Green (≥80%): High confidence
     - Yellow (≥60%): Medium confidence
     - Orange (≥40%): Low confidence
     - Red (<40%): Very low confidence
   - **Missing data**: Shows "—" when `namePriceScore` is absent
   - **Tooltip**: Hover over score to see `namePriceNotes` details

## Negative Test Cases

### No File Upload

```bash
curl -X POST http://localhost:8080/api/analyze-image
```

Expected: `400` JSON error

### Non-Image File

```bash
curl -F "image=@./test.txt" http://localhost:8080/api/analyze-image
```

Expected: `400` JSON error

### Oversized Image (>10MB)

```bash
curl -F "image=@./large_image.jpg" http://localhost:8080/api/analyze-image
```

Expected: `400` JSON error

### Verifier JSON Parsing Errors

When the verifier returns invalid JSON twice:

- `namePriceScore` field is omitted
- `namePriceNotes` field shows `"verifier_error_invalid_json"`

## Verification Checklist

- [ ] Backend starts without errors
- [ ] Health endpoint returns OK
- [ ] Image analysis returns items with verifier fields
- [ ] Frontend displays new "Name/Price Score" column
- [ ] Score percentages display correctly with color coding
- [ ] Tooltips show `namePriceNotes` on hover
- [ ] Missing scores show "—" placeholder
- [ ] Error cases return appropriate HTTP status codes
- [ ] Backward compatibility maintained for old payloads
