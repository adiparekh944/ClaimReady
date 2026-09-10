# Computer Vision Upgrade Plan

This document is the output of a repository audit performed before any code was
changed. It records what the perception stack actually does today, which parts of
it are reachable at runtime, and what the upgrade will replace.

## 1. Audit: entrypoints and runtime paths

### 1.1 Which server is actually production?

There are three Flask applications in `backend/`, and they do not agree with each
other:

| File | Endpoints | Detection approach | Reachable? |
| --- | --- | --- | --- |
| `geminiserver.py` | `/api/analyze-image`, `/api/analyze-multiple-images`, `/health` | class-agnostic YOLO11-seg + Gemini | **yes — this is production** |
| `api.py` | `/api/process-image`, `/api/process-video`, `/api/create-job`, `/api/upload-and-process`, `/health` | delegates to `app.py` | legacy / Supabase job flow |
| `app.py` | not a server; exports `process_video`, `process_image` | COCO-class YOLO11-l + tracking | imported by `api.py` only |
| `appLocal.py` | not a server | COCO-class YOLO11-l + tracking | orphaned local copy of `app.py` |

The deciding evidence is the frontend. `frontend/src/app/upload/page.tsx`,
`frontend/src/app/test/page.tsx`, and `frontend/src/app/debug/page.tsx` all call
`${NEXT_PUBLIC_BACKEND_URL}/api/analyze-image` and
`/api/analyze-multiple-images`. Those routes exist **only** in
`geminiserver.py`. `backend/Dockerfile` agrees: its final line is
`CMD ["python", "geminiserver.py"]`.

`render.yaml` disagrees — it declares `startCommand: cd backend && python api.py`
and `healthCheckPath: /health`. Both servers expose `/health`, so the Render
health check would pass while serving an API the frontend never calls. This is
tracked as a deployment inconsistency in Phase 19; it will be documented and
reconciled, not silently switched.

### 1.2 Live image path (`geminiserver.py`)

```
POST /api/analyze-image  (multipart, field "image")
  -> cv2.imdecode
  -> detect_fast(img, YOLO_MODEL)
       -> diagnostic_detection(img, model)
            -> run_detection_test(conf=CONF_THRESH=0.01)   # pass 1
            -> run_detection_test(conf=0.005)              # pass 2
            -> fast_merging(all_boxes)                     # greedy IoU union
            -> fast_deduplication(boxes)                   # greedy IoU suppress
  -> dynamic_padding + get_clamped_padded_box  -> crops
  -> analyze_scene_with_gemini(scene@768px, crops@384px)
  -> jsonify(items, total_items, images)
```

Model: `yolo11x-seg.pt`, loaded once at import (`YOLO_MODEL` module global).
`SCALES = [640]`, so despite multi-scale machinery existing in the file, only a
single resolution is ever used. `agnostic_nms=True` and the class labels are
discarded — YOLO is a pure objectness proposer and Gemini does all semantic
identification.

### 1.3 Live video path (`app.py` via `api.py`)

```
process_video(path, job_id, db, show_display)
  -> cv2.VideoCapture, downsample to <=20 FPS
  -> YOLO("yolo11l.pt").track(persist=True, conf=0.55, iou=0.45)
  -> per-track_id history: frames_seen / consecutive_misses / class_counts
  -> count an item once frames_seen >= 3 (min_frames_to_count)
  -> forget a track after 5 consecutive misses
  -> keep highest-confidence crop per track_id  (best_snapshots)
  -> upload_snapshot_to_supabase -> FurniturePriceEstimator.analyze_item_with_gemini
```

Here class labels *are* used, `person` is excluded, and identity comes purely
from the tracker's `track_id`. There is no appearance model, so a track ID switch
creates a duplicate inventory entry, and an object revisited after panning away
is counted twice.

### 1.4 API contract that must not break

Per-item shape consumed by the frontend (`frontend/src/lib/hardcodedRooms.ts`
defines the same interface for its mock data):

```ts
{ code: string, imageAttachment: string, bbox: [number,number,number,number],
  name: string, category: string, price_usd: number, description: string }
```

- `/api/analyze-image` returns `{ items, total_items, images }`
- `/api/analyze-multiple-images` returns `{ status, items, objects, images, total_items, total_value }`

`images` maps `code -> data:image/jpeg;base64,...`. Any new fields must be
additive.

## 2. Audit: dead vs live CV code

### 2.1 Dead code inside the production server (`geminiserver.py`)

Defined but never called from any reachable path:

| Function | Notes |
| --- | --- |
| `yolo_multi_test_detection` | **would crash if called** — references `CONF_THRESH_LOW` and `FEATURE_SIM_THRESH`, neither of which is defined in this file |
| `peg_dedup` | CLIP-embedding dedup; the only real use of `embed_boxes_clip` |
| `embed_boxes_clip`, `get_clip_model` | OpenCLIP loader, unreachable |
| `extract_backbone_features` | YOLO backbone feature extraction, unreachable |
| `detect_with_sahi`, `_get_sahi_model` | SAHI tiled inference, unreachable |
| `aggressive_cluster_merging(_parallel)` | shadowed by `fast_merging` via `USE_FAST_MERGING = True` |
| `smart_deduplication(_parallel)` | shadowed by `fast_deduplication` |
| `is_duplicate_detection` | only called by the dead `yolo_multi_test_detection` |
| `combine_similar_boxes` | only called by the dead `yolo_multi_test_detection` |
| `calculate_mask_overlap(_parallel)`, `process_box_chunk` | only used by the shadowed merge/dedup variants |
| `to_grayscale_3ch`, `edge_overlay_canny` | transforms for the dead multi-test path |
| `expand_box` | edge-snapping box expansion, unreachable |
| `calculate_overlap_opacity` | unreachable |

So the production detector uses exactly four of these functions:
`run_detection_test`, `diagnostic_detection`, `fast_merging`,
`fast_deduplication`. Everything else is inert. Notably, **masks are collected
but never used** — `run_detection_test` returns them, `diagnostic_detection`
threads them through, and `detect_fast` drops them on the floor.

### 2.2 Fully orphaned module

`backend/yolo_oscf_v7.py` is 1,731 lines and **nothing imports it**. Its
algorithms were copy-pasted into `geminiserver.py` rather than imported. It
contains genuinely useful ideas that never reached production: multi-scale
inference at 640/1280/1920, CLAHE preprocessing, Canny-edge-density "busy area"
tiling, Weighted Box Fusion, Bhattacharyya color-histogram dedup, perceptual
hashing of masks, and a transform-voting scheme. It also has Windows-absolute
hardcoded paths (`C:\Users\Arnav\Downloads\Room3.jpg`) confirming it was a
single-developer scratchpad.

### 2.3 Existing tests

`test_*.py` at the repo root and in `backend/` are integration scripts that
`requests.post` against a running server. They are not unit tests, have no
assertions usable by a runner, and there is no pytest config, no CI workflow, and
no test dependency declared. Effectively: **no test coverage of CV logic**.

### 2.4 Configuration constants (currently scattered)

`geminiserver.py` module level: `YOLO_MODEL_PATH`, `YOLO_CONF`, `YOLO_IMGSZ`,
`CROP_PAD_FRAC`, `SCALES`, `IOU_NMS`, `MASK_THRESH`, `CONF_THRESH`, `NUM_CORES`,
`USE_FAST_MERGING`, `SKIP_MASK_PROCESSING`, `SHOW_IMAGE_POPUP`. Plus magic
numbers inline in `fast_merging` (0.4/0.2/0.1 IoU, 50000/10000 px area) and
`fast_deduplication` (0.5/0.6/0.7 IoU, 100000/10000 px area), and `0.005` as a
literal second-pass confidence. `app.py` has its own separate copies
(`confidence_threshold = 0.55`, `min_frames_to_count = 3`, etc.).

### 2.5 Secret hygiene problem found during audit

`geminiserver.py` line 93 contains a hardcoded Gemini API key as the default
value of `os.environ.get("GEMINI_API_KEY", ...)`, and `backend/Dockerfile` has a
second key in a commented-out `ENV` line. These are already committed to history
so this upgrade cannot un-leak them, but new code will not read or propagate
them, and the plan recommends rotation. No new secrets will be committed.

## 3. Proposed architecture

A new `vision/` package becomes the single home for perception. The Flask servers
become thin transport layers over it.

```
input image
  │
  ├─ preprocessing.py    quality gate (brightness / contrast / Laplacian blur)
  │                      -> optional CLAHE / gamma / unsharp enhanced pass
  │
  ├─ detector.py         multi-scale class-agnostic YOLO11-seg
  │                      scales per mode: FAST [640] / BALANCED [640,960] /
  │                      ACCURATE [640,960,1280]
  │                      + proposals.py  tiled pass (ACCURATE or density trigger)
  │                      all boxes projected back to original coordinates
  │
  ├─ segmentation.py     masks resized to original frame, mask area,
  │                      bbox occupancy, mask IoU, masked crop extraction
  │
  ├─ fusion (proposals.py)  hybrid rule:
  │                          high IoU              -> weighted box fusion
  │                          strong containment    -> confidence-aware pick/fuse
  │                          low-IoU fragments     -> union if embedding agrees
  │
  ├─ embeddings.py       OpenCLIP, batched, inference_mode, L2-normalized
  │                      one NxD matrix -> vectorized E @ E.T similarity
  │
  ├─ deduplication.py    geometric + semantic scoring, union-find clustering,
  │                      canonical proposal per cluster, merge_reason recorded
  │
  └─ crops -> Gemini (unchanged)  + source label "proposal" | "scene_recovery"
```

Video gains `tracking.py` + `association.py`: a memory bank keyed by inventory
identity rather than raw `track_id`, with CLIP re-identification so a new tracker
ID for a previously seen object maps back to the same item.

Supporting modules: `config.py` (single `VisionConfig` dataclass, env-overridable),
`metrics.py` (IoU/precision/recall/F1/mAP, duplicate-F1, ID-switch counting),
`visualization.py` (per-stage debug renders).

### 3.1 Modes

| Mode | Scales | Tiling | Masks | Embeddings | Intent |
| --- | --- | --- | --- | --- | --- |
| FAST | [640] | no | no | no | preserve today's latency profile |
| BALANCED | [640, 960] | no | yes | yes | interactive default |
| ACCURATE | [640, 960, 1280] | yes | yes | yes | maximum recall, offline/batch |

FAST must remain behaviourally close to the current pipeline so there is always a
low-latency escape hatch.

## 4. Expected computational tradeoffs

Stated as expectations to be *measured*, not as claims:

- **Multi-scale**: cost is roughly linear in the number of scales for the YOLO
  stage. BALANCED should be ~2x the detector cost of FAST; ACCURATE ~3x plus the
  tiled pass. Expected benefit is small-object recall.
- **Tiling**: cost scales with tile count, which grows quadratically as tile size
  shrinks relative to the image. This is why it is gated behind ACCURATE mode or
  a megapixel/density trigger rather than always on.
- **Embeddings**: one extra forward pass over N crops. Batched and capped by
  `max_proposals`, this should be a fixed modest cost rather than a per-pair one.
  The naive alternative (embedding each pair independently) is O(N^2) forward
  passes and is explicitly avoided.
- **Dedup**: pairwise scoring is O(N^2) in *arithmetic* but vectorized as matrix
  ops; the Python-level loop is only over the union-find merges.
- **Preprocessing**: adds a second detector pass, so it is gated on a measured
  quality score instead of running unconditionally.

The dominant end-to-end cost today is the Gemini call, not YOLO. Detector work
that improves proposal quality without increasing crop count may therefore be
close to latency-neutral overall — but this must be confirmed by the benchmark
before any such statement is made.

## 5. Benchmark strategy

`benchmarks/run_cv_benchmark.py` runs named configurations over an image
directory and records raw/final proposal counts and a per-stage latency
breakdown. `benchmarks/evaluate.py` computes detection metrics against COCO-style
annotations if the user supplies them, plus duplicate-precision/recall/F1 for the
dedup task. `benchmarks/resume_metrics.py` derives deltas between configurations.

The repository ships **no annotated dataset**. Counting and latency metrics work
without annotations; precision/recall/mAP require the user to add labels, and the
tooling will report them as unavailable rather than fabricating them.

Ablations: `A` IoU-only baseline, `B` multi-scale + WBF, `C` B + embeddings,
`D` full pipeline.

## 6. Files that will change

**New**

```
vision/{__init__,config,detector,segmentation,proposals,embeddings,
        deduplication,tracking,association,preprocessing,metrics,visualization}.py
benchmarks/{run_cv_benchmark,evaluate,resume_metrics}.py
tests/test_*.py                     unit tests, mocked inference
docs/cv_upgrade_plan.md             this file
docs/computer_vision_pipeline.md    architecture writeup
```

**Modified**

```
backend/geminiserver.py    detector internals -> VisionPipeline; adds source labels
backend/app.py             video path -> tracking/association memory bank
backend/requirements.txt   pin what the vision package needs
render.yaml                entrypoint reconciliation (Phase 19)
README.md                  CV architecture section
.gitignore                 artifacts/, model weights, venv
```

**Removed / deprecated**

```
backend/yolo_oscf_v7.py    orphaned; ideas migrated into vision/, then deleted
geminiserver.py dead fns   listed in 2.1, removed or replaced by vision/ equivalents
```

## 7. Constraints held throughout

1. The two live endpoints keep their request and response shapes; new fields are
   additive only.
2. FAST mode remains available and remains the low-latency option.
3. No feature ships as an uncalled function. Every algorithm is either on a
   configurable path in the live pipeline or exercised by the benchmark.
4. No performance number is written into docs, README, or code unless it came
   out of an actual benchmark run on this machine.
