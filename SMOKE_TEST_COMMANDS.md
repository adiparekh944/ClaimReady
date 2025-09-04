# ClaimReady Producer-Verifier Pipeline Smoke Test

## 🚀 Quick Start Commands

### 1. Start Backend

```bash
cd backend
python3 geminiserver.py
# Server runs on http://localhost:8080
```

### 2. Start Frontend

```bash
cd frontend
npm run dev
# Frontend runs on http://localhost:3000
```

### 3. Test with curl

```bash
# Create test image first
python3 -c "from PIL import Image; Image.new('RGB', (400, 300), 'white').save('test_image.jpg')"

# Test API endpoint
curl -F "image=@test_image.jpg" http://localhost:8080/api/analyze-image

# Test health endpoint
curl http://localhost:8080/health

# Test pipeline endpoint
curl http://localhost:8080/test-pipeline
```

### 4. Test CLI

```bash
cd backend
python3 geminiserver.py --test-image ./test_image.jpg
```

### 5. Test Frontend UI

1. Open browser: http://localhost:3000/upload
2. Upload test image
3. Verify "Verification Score" column appears
4. Check scores display as percentages (0-100%)
5. Hover over scores to see verification notes

## 🧪 Expected Results

### Backend Response (with verification)

```json
{
  "items": [
    {
      "code": "0",
      "name": "Laptop",
      "category": "Electronics",
      "brand": "Dell",
      "price_usd": 1200.0,
      "description": "Gaming laptop",
      "verificationScore": 0.85,
      "verificationNotes": "Good visual match with clear product features"
    }
  ],
  "total_items": 1,
  "total_value": 1200.0,
  "status": "success"
}
```

### Frontend Display

- ✅ "Verification Score" column visible
- ✅ Progress bar shows 85% (green)
- ✅ Tooltip shows verification notes on hover
- ✅ Graceful fallback for missing scores

## 🔍 Verification Checklist

- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] curl request returns JSON with verificationScore
- [ ] CLI test outputs valid JSON
- [ ] Frontend displays verification column
- [ ] Hover shows verification notes
- [ ] Old payloads without verificationScore still render
