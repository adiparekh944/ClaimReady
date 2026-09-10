<p align="center">
  <img src="frontend/public/logowhite.png" alt="ClaimReady Logo" width="250"/>
</p>

<h1 align="center">ClaimReady: Smart Home Inventory & Valuation 📸🏠</h1>

<p align="center">
  Effortlessly turn photos and videos of your home into a secure, AI-powered digital inventory with intelligent valuations.
</p>

---

## 🚀 Overview
ClaimReady transforms your home photos and videos into a comprehensive digital inventory with accurate valuations. Whether for **insurance claims, moving, or organization**, ClaimReady makes documenting and valuing your belongings simple and fast.

---

## ⚙️ How It Works
1. **Smart Detection** – Upload photos or videos of your home. Our AI (YOLO v11) automatically detects belongings, saving hours of manual documentation.  
2. **Intelligent Valuation** – Items are analyzed by **Google Gemini AI**, combining image understanding and market data for accurate replacement values.  
3. **Multi-File Support** – Upload multiple images or videos at once for full coverage.  
4. **Unified Results** – ClaimReady merges everything into a clean, organized digital inventory.  
5. **Secure Storage** – Your data is safely stored with **Supabase**, always accessible and protected.  

---

## 🌟 Key Features
### 📸 Photo & Video Upload
- Multiple formats supported (JPG, PNG, MP4, MOV, etc.)  
- Drag-and-drop interface  
- Batch processing  

### 🤖 AI-Powered Detection
- YOLO v11 object detection  
- Automatic categorization & identification  
- Deduplication to avoid overcounting  

### 💰 Smart Valuation
- Google Gemini AI price estimates  
- Market-aware replacement values  
- Condition & brand recognition  

### 📊 Comprehensive Results
- Individual item details  
- Total home inventory value  
- Unified report from all uploads  

---

## ☑️ Problem We Solve
Homeowners and renters struggle with:  
- **Tedious documentation** of belongings  
- **Insurance prep** without complete valuations  
- **Moving & organization** logistics  
- **Unknown replacement values** until it’s too late  

ClaimReady automates the entire process—from detection to valuation—in minutes.

---

## 🛠️ Tech Stack
**Frontend**  
- Next.js 14 (TypeScript)  
- Tailwind CSS  
- Framer Motion  
- Custom Fonts (Black Future, Kumbh Sans)  

**Backend**  
- Python Flask API  
- Ultralytics YOLO11 (segmentation, class-agnostic proposals)  
- OpenCLIP ViT-B-32 (appearance embeddings for deduplication and re-ID)  
- Google Gemini 2.5 Flash (open-vocabulary identification and valuation)  
- Supabase (data storage & auth)  

---

## 🔬 Computer Vision Architecture

The perception stack lives in [`backend/vision/`](backend/vision) and is
documented in full in
[docs/computer_vision_pipeline.md](docs/computer_vision_pipeline.md).

### The core idea: detection and identification are separate jobs

YOLO11 runs **class-agnostic** here — `agnostic_nms=True`, and its predicted
class labels are discarded. The reason is that the checkpoint's label set is
COCO's 80 categories (`chair`, `couch`, `tv`), which cannot distinguish a $40
folding chair from a $1,200 office chair and has no category at all for most of
a real household's contents.

So the detector answers only **"is there an object here, and where"**, and an
open-vocabulary multimodal model (Gemini 2.5 Flash) handles **what it is and
what it costs**. That split is what licenses very low confidence thresholds
(0.01 primary, 0.005 secondary): a false positive costs one extra crop for the
identification stage to reject, while a false negative is an item missing from
someone's claim. The resulting flood of redundant boxes is paid down by fusion
and deduplication rather than by raising the threshold.

CLIP embeddings appear below, and their role is deliberately narrow: they
answer *"are these two crops the same physical object?"* They do not classify,
name, or price anything.

### Image pipeline

```
image
  → quality gate            brightness / contrast / Laplacian variance
                            (enhanced pass only if a defect is measured)
  → multi-scale YOLO11-seg  FAST [640] · BALANCED [640,960] · ACCURATE [+1280]
                            + low-confidence secondary pass
                            + tiled pass (ACCURATE, >8MP, or >25 small objects)
  → coarse IoU pre-fusion   weighted box fusion on unambiguous overlap
  → proposal cap            before the expensive per-crop stage
  → CLIP embeddings         batched; one (N,D) matrix, similarity = E @ Eᵀ
  → deduplication           IoU · containment · centre distance · size ratio
                            · mask IoU · CLIP cosine → union-find clusters
  → crops → Gemini          items tagged "proposal" or "scene_recovery"
```

### Video pipeline

The YOLO tracker handles frame-to-frame continuity; an **inventory memory bank**
handles identity across gaps using CLIP descriptors, so an object that loses its
tracker ID through occlusion or a camera pan does not become a duplicate
inventory entry. Items visible in the same frame are never merged — a physical
constraint, not a threshold. Best-frame selection scores detector confidence,
box area, sharpness and distance from the frame edge.

### Operating modes

| Mode | Scales | Tiling | Masks | Embeddings | Intent |
| --- | --- | --- | --- | --- | --- |
| `FAST` | 640 | no | no | no | lowest latency |
| `BALANCED` | 640, 960 | on trigger | yes | yes | interactive default |
| `ACCURATE` | 640, 960, 1280 | always | yes | yes | maximum recall, batch |

Set with `CR_VISION_MODE`. Every threshold in `vision/config.py` is overridable
via a `CR_VISION_*` environment variable, and `GET /api/vision-config` reports
what a running instance resolved to.

### Benchmarks

```bash
# ablation over an image set (no annotations needed for counts and latency)
python -m benchmarks.run_cv_benchmark --from-video backend/testtt.mp4 \
    --configs A_baseline B_multiscale_wbf C_embeddings D_full

# tracker-only vs. appearance re-identification
python -m benchmarks.run_video_benchmark --video backend/testtt.mp4

# unit tests (no model weights downloaded)
python -m pytest
```

Measured results, including the per-stage latency breakdown and the cases where
a feature demonstrably did **not** help, are recorded in
[docs/benchmark_results.md](docs/benchmark_results.md). Detection accuracy
(precision, recall, mAP) is **not** reported because this repository ships no
annotated dataset; `benchmarks/evaluate.py --make-template` generates a
skeleton for adding one.

---

## ❤️ Why ClaimReady?
- **Effortless** – Just upload photos/videos, get a full inventory  
- **Accurate** – AI-powered detection + valuations  
- **Scalable** – Works for small apartments to large homes  
- **Secure** – Supabase-powered backend  

---

## 🗺️ Future Roadmap
- 📱 Native iOS + Android apps  
- 🏦 Direct insurance provider integrations  
- 📊 Advanced analytics & insights  
- 🎤 Voice assistant queries  
- 📑 Export options (PDF, CSV, integrations)  

---

<p align="center">
  <b>ClaimReady</b> – Making home inventory effortless, accurate, and secure. 🏠✨
</p>
