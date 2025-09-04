# LangChain Gemini Verifier Implementation

## Overview

Successfully implemented a LangChain Gemini "verifier" that scores NAME + PRICE plausibility using the SAME image input (no augmentation). The verifier adds two optional fields to each item before returning:

- `namePriceScore`: number (0.0–1.0)
- `namePriceNotes`: string

## Implementation Details

### 1. LangChain Setup

- **Location**: `backend/geminiserver.py` lines 109-147
- **Dependencies**: Added `langchain>=0.1.0` and `langchain-google-genai>=1.0.0` to `requirements.txt`
- **Graceful Fallback**: If LangChain is not available, the verifier gracefully falls back to adding null fields

### 2. Verifier Chain Configuration

- **Model**: Uses the same Gemini model as the producer (`GEMINI_MODEL`)
- **Temperature**: 0.1 (low for consistent scoring)
- **Max Output Tokens**: 1024
- **Prompt Template**: Strict JSON-only evaluator that judges name and price plausibility

### 3. Verifier Prompt

The verifier uses a carefully crafted prompt that:

- Takes producer prediction fields: `{title, brand, model, price_usd}`
- Evaluates visual consistency based on visible cues (silhouette, materials, logos/text)
- Considers typical price ranges (new/used)
- Returns strict JSON: `{"namePriceScore": <0.0-1.0>, "namePriceNotes": "<short rationale>"}`

### 4. Core Functions

#### `verify_item_name_price(item, image_bytes)`

- **Location**: `backend/geminiserver.py` lines 1366-1446
- **Purpose**: Verifies a single item's name and price plausibility
- **Input**: Item object and original image bytes
- **Output**: Item object with added `namePriceScore` and `namePriceNotes` fields
- **Error Handling**: Robust JSON parsing with fallback to null values on errors

#### Integration in `analyze_image` endpoint

- **Location**: `backend/geminiserver.py` lines 1831-1848
- **Process**:
  1. Producer chain runs first (existing functionality)
  2. For each item, verifier chain runs with same image bytes
  3. Verifier results are merged into each item
  4. Response includes both producer fields and verifier fields

### 5. JSON Guards and Validation

- **JSON Parsing**: Handles markdown code blocks and extra text
- **Score Clamping**: Ensures `namePriceScore` is within [0.0, 1.0] range
- **Error Fallback**: Sets `namePriceScore = null` and `namePriceNotes = "verifier_error_*"` on failures
- **Retry Logic**: Attempts to extract JSON using regex if initial parsing fails

### 6. Orchestration Flow

```
image → producer_chain(image_bytes) → P (existing output)
image + P.{title/name, brand, model, price_usd} → verifier_chain(image_bytes) → {namePriceScore, namePriceNotes}
For each item in P, attach these two fields and return
```

### 7. Constraints Met

- ✅ **Same image bytes**: Verifier uses original image, no resizing/jitter
- ✅ **No schema changes**: Producer schema unchanged, verifier adds optional fields
- ✅ **Local-only**: No database writes, works entirely locally
- ✅ **Graceful degradation**: Works even when LangChain/credentials unavailable
- ✅ **JSON-only output**: Strict JSON parsing with error handling

## Testing

### Test Script: `backend/test_verifier.py`

- Verifies function structure and availability
- Tests graceful handling of missing credentials
- Confirms required fields are added to items
- Validates endpoint integration

### Test Results

```
🎉 All tests passed! Verifier implementation is correct.
```

## Usage

The verifier automatically runs when:

1. LangChain is available (`LANGCHAIN_AVAILABLE = True`)
2. Verifier chain is initialized (`VERIFIER_CHAIN is not None`)
3. Google API credentials are properly configured

When verifier is unavailable, items will have:

```json
{
  "namePriceScore": null,
  "namePriceNotes": "verifier_unavailable"
}
```

When verifier is available, items will have:

```json
{
  "namePriceScore": 0.85,
  "namePriceNotes": "Price seems reasonable for a MacBook Pro, name matches visible Apple logo"
}
```

## Files Modified

- `backend/geminiserver.py` - Main implementation
- `backend/requirements.txt` - Added LangChain dependencies
- `backend/test_verifier.py` - Test script (new)
- `backend/VERIFIER_IMPLEMENTATION.md` - This documentation (new)
