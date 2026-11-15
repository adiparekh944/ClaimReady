# ClaimReady Image Analysis API

The ClaimReady API accepts a room or household-item image and returns a structured inventory of detected items with estimated replacement values.

## Base URL

```text
https://YOUR-CLAIMREADY-API-HOST
```

Replace the placeholder with the production URL supplied with your API key.

## Authentication

Every analysis request requires an API key. Send it as a Bearer token:

```http
Authorization: Bearer YOUR_API_KEY
```

Keep this key on your server. Do not embed it in public browser JavaScript, mobile application source, or a public repository.

## Analyze an image

```http
POST /v1/analyze
Content-Type: multipart/form-data
Authorization: Bearer YOUR_API_KEY
```

The multipart form must contain exactly one field named `image`.

### Supported input

- JPEG, PNG, WebP, GIF, or BMP
- Maximum request size: 10 MB
- Maximum decoded image size: 40 million pixels
- One image per request

### cURL

```bash
curl --request POST \
  --url "https://YOUR-CLAIMREADY-API-HOST/v1/analyze" \
  --header "Authorization: Bearer YOUR_API_KEY" \
  --form "image=@/path/to/room.jpg"
```

### Python

```python
import requests

url = "https://YOUR-CLAIMREADY-API-HOST/v1/analyze"
headers = {"Authorization": "Bearer YOUR_API_KEY"}

with open("room.jpg", "rb") as image_file:
    response = requests.post(
        url,
        headers=headers,
        files={"image": ("room.jpg", image_file, "image/jpeg")},
        timeout=300,
    )

response.raise_for_status()
result = response.json()
print(result["items"])
```

### Node.js

This example requires Node.js 20 or newer.

```javascript
import { open } from "node:fs/promises";

const image = await open("room.jpg", "r");
const form = new FormData();
form.append("image", new Blob([await image.readFile()], { type: "image/jpeg" }), "room.jpg");

const response = await fetch("https://YOUR-CLAIMREADY-API-HOST/v1/analyze", {
  method: "POST",
  headers: { Authorization: "Bearer YOUR_API_KEY" },
  body: form,
});

const result = await response.json();
if (!response.ok) throw new Error(JSON.stringify(result));
console.log(result.items);
```

## Successful response

```json
{
  "status": "success",
  "total_items": 2,
  "total_value": 1299.99,
  "items": [
    {
      "code": "0",
      "imageAttachment": "0",
      "bbox": [120, 80, 740, 610],
      "name": "Wood dining table",
      "category": "furniture",
      "price_usd": 850,
      "description": "Large rectangular wood dining table"
    },
    {
      "code": "1",
      "imageAttachment": "1",
      "bbox": [760, 140, 1040, 690],
      "name": "Upholstered dining chair",
      "category": "furniture",
      "price_usd": 449.99,
      "description": "Padded high-back dining chair"
    }
  ],
  "images": {
    "0": "data:image/jpeg;base64,...",
    "1": "data:image/jpeg;base64,..."
  }
}
```

`bbox` uses `[left, top, right, bottom]` pixel coordinates. `images` maps item codes to Base64-encoded image crops. Prices are AI-generated estimates and should be reviewed before they are used in an insurance claim, appraisal, or purchasing decision.

## Errors

Errors return a non-2xx HTTP status and a JSON body:

```json
{
  "status": "error",
  "error": {
    "code": "unauthorized",
    "message": "A valid API key is required."
  },
  "items": []
}
```

| Status | Meaning |
| --- | --- |
| `400` | Missing image, empty filename, or invalid image data |
| `401` | Missing or invalid API key |
| `413` | Request or decoded image exceeds the configured limit |
| `415` | Unsupported image format |
| `500` | Analysis failed; provide the returned `error_id` when requesting support |
| `503` | The server's API authentication is not configured |

## Health check

```http
GET /health
```

The health endpoint does not require authentication and returns:

```json
{"status": "ok"}
```

## Operational notes

- Analysis is synchronous and can take several seconds or longer depending on image complexity and server load.
- Use a client timeout of at least 300 seconds.
- Retry temporary `500` responses with exponential backoff. Do not automatically retry `400`, `401`, `413`, or `415` responses.
- Send the original image whenever possible. Heavy compression, blur, darkness, or occlusion can reduce detection quality.

