# ClaimReady Computer Vision Pipeline

## Contents

1. [Why YOLO is class-agnostic here](#1-why-yolo-is-class-agnostic-here)
2. [Why an open-vocabulary model does the identification](#2-why-an-open-vocabulary-model-does-the-identification)
3. [Architecture](#3-architecture)
4. [Multi-scale proposal generation](#4-multi-scale-proposal-generation)
5. [Weighted Box Fusion](#5-weighted-box-fusion)
6. [Segmentation-aware filtering](#6-segmentation-aware-filtering)
7. [CLIP appearance embeddings](#7-clip-appearance-embeddings)
8. [Geometric and semantic deduplication](#8-geometric-and-semantic-deduplication)
9. [Tiled small-object detection](#9-tiled-small-object-detection)
10. [Quality-gated preprocessing](#10-quality-gated-preprocessing)
11. [Video tracking and visual re-identification](#11-video-tracking-and-visual-re-identification)
12. [Benchmark architecture](#12-benchmark-architecture)
13. [Latency and accuracy tradeoffs](#13-latency-and-accuracy-tradeoffs)
14. [Configuration](#14-configuration)
15. [Known weaknesses](#15-known-weaknesses)

---

## 1. Why YOLO is class-agnostic here

Every detector pass runs with `agnostic_nms=True` and the predicted class
labels are **discarded**. That is unusual enough to need justifying.

The checkpoint is trained on COCO, whose 80 categories are `chair`, `couch`,
`tv`, `laptop`, `vase`, and so on. For an insurance inventory that label set is
close to useless in both directions:

- **Too coarse where it matters.** "chair" does not distinguish a $40 folding
  chair from a $1,200 Herman Miller Aeron. Replacement value is the entire
  point of the product, and the label carries almost none of the information
  that determines it.
- **Absent where it matters.** A room contains phone chargers, textbooks,
  cosmetics, bedding, board games, kitchen utensils. COCO has no category for
  most of a real household's contents, so a label-driven pipeline simply cannot
  see them.

So the detector is used for the one thing it is genuinely good at:
**localization**. It answers "is there an object here, and where", and nothing
else.

This split is what licenses the very low confidence thresholds. The primary
pass runs at 0.01 and a secondary pass at 0.005, versus a typical 0.25. The
asymmetry of costs justifies it:

- a **false positive** costs one extra crop for the identification stage to
  reject, and
- a **false negative** is an item missing from someone's insurance claim.

Recall is therefore worth buying at the expense of precision. The cost of that
choice — an explosion of overlapping, redundant boxes — is paid down by the
fusion and deduplication stages rather than by raising the threshold.

## 2. Why an open-vocabulary model does the identification

Naming and pricing go to Gemini 2.5 Flash, which receives the full scene at
768px plus every surviving crop at 384px, each tagged with a code and its pixel
box, and returns structured JSON.

A multimodal model is the right tool because the task is genuinely
open-vocabulary and knowledge-intensive: it requires reading brand text off a
box, recognizing a specific furniture line, and knowing roughly what that line
costs. No fixed-label detector can do that, and training one would need a
labelled dataset of household goods with prices that does not exist.

**What the vision stack does not do.** CLIP embeddings appear later in this
document and it is worth being precise about their role: they answer *"are
these two crops the same physical object?"* and nothing more. They do not
classify, name, or price. CLIP has no concept of "Herman Miller Aeron". Using
embedding similarity for identification would be an unfounded claim; using it
for identity matching is exactly what the representation supports.

The prompt also permits Gemini to add items it sees in the wide shot that no
crop covered. Those come back marked `imageAttachment: "scene"` and are
labelled `source: "scene_recovery"` in the response, while crop-derived items
are `source: "proposal"`. That distinction exists so detector recall stays
measurable: an item only the scene view caught is one the proposal stage missed.

## 3. Architecture

```
                                  IMAGE PATH
                          (backend/geminiserver.py)

  upload
    │
    ▼
  ┌───────────────────────────────────────────────────────────────────┐
  │ 1. QUALITY ASSESSMENT              vision/preprocessing.py       │
  │    brightness · contrast · Laplacian variance                    │
  │    → enhanced variant ONLY if a measured defect is present       │
  └───────────────────────────────────────────────────────────────────┘
    │
    ▼
  ┌───────────────────────────────────────────────────────────────────┐
  │ 2. CLASS-AGNOSTIC DETECTION             vision/detector.py       │
  │                                                                   │
  │    scales:   FAST [640]  BALANCED [640,960]  ACCURATE [+1280]    │
  │    + secondary pass at conf 0.005                                │
  │    + enhanced pass          (only if step 1 produced one)        │
  │    + tiled pass             (ACCURATE, or >8MP, or >25 small)    │
  │                                                                   │
  │    boxes: already in original coords (Ultralytics)               │
  │    masks: un-letterboxed here          → project_mask()          │
  └───────────────────────────────────────────────────────────────────┘
    │  raw proposals (hundreds)
    ▼
  ┌───────────────────────────────────────────────────────────────────┐
  │ 3. COARSE IoU PRE-FUSION                  vision/fusion.py       │
  │    cluster on IoU >= 0.55 → weighted box fusion                  │
  │    (unambiguous agreement; needs no appearance model)            │
  └───────────────────────────────────────────────────────────────────┘
    │
    ▼
  ┌───────────────────────────────────────────────────────────────────┐
  │ 4. PROPOSAL CAP                        vision/proposals.py       │
  │    keep top-N by confidence, BEFORE the expensive stage          │
  └───────────────────────────────────────────────────────────────────┘
    │
    ▼
  ┌───────────────────────────────────────────────────────────────────┐
  │ 5. APPEARANCE EMBEDDINGS              vision/embeddings.py       │
  │    OpenCLIP ViT-B-32, batched, inference_mode, L2-normalized     │
  │    N crops → (N,D) matrix → S = E @ E.T   (one matmul)           │
  │    crop mode: bbox | masked | both                               │
  └───────────────────────────────────────────────────────────────────┘
    │
    ▼
  ┌───────────────────────────────────────────────────────────────────┐
  │ 6. DEDUPLICATION                   vision/deduplication.py       │
  │    signals: IoU · IoS · containment · centre dist · size ratio   │
  │             · mask IoU · CLIP cosine                             │
  │    5-clause rule → union-find clusters → fuse each cluster       │
  │    every merge records WHY (merge_reason)                        │
  └───────────────────────────────────────────────────────────────────┘
    │  final proposals (tens)
    ▼
  ┌───────────────────────────────────────────────────────────────────┐
  │ 7. CROP EXTRACTION + GEMINI                                      │
  │    size-dependent padding → scene@768 + crops@384 → JSON items   │
  │    source: "proposal" | "scene_recovery"                         │
  └───────────────────────────────────────────────────────────────────┘
    │
    ▼
  {items, total_items, images, detection}


                                  VIDEO PATH
                     (backend/app.py → vision/tracking.py)

  video
    │
    ▼
  frame sampling to ~20 FPS
    │
    ▼
  ┌───────────────────────────────────────────────────────────────────┐
  │ YOLO TRACKER (class labels KEPT here)      vision/tracking.py    │
  │ frame-to-frame continuity via motion + overlap                   │
  └───────────────────────────────────────────────────────────────────┘
    │  track_id, box, conf, label
    ▼
  ┌───────────────────────────────────────────────────────────────────┐
  │ INVENTORY MEMORY BANK                   vision/association.py    │
  │                                                                   │
  │  1. known track_id?          → same item          (cheap)        │
  │  2. CLIP descriptor match?   → re-identify        (survives gaps)│
  │  3. otherwise               → new identity                       │
  │                                                                   │
  │  guards: coexisting items never merge (physical constraint)      │
  │          hysteresis: >=3 frames to confirm, 5 to forget          │
  │  best crop per item: conf + area + sharpness + centrality        │
  └───────────────────────────────────────────────────────────────────┘
    │
    ▼
  upload best crop → price → Supabase
```

The `vision` package lives at `backend/vision/` so it falls inside the Docker
build context; see [docs/deployment.md](deployment.md).

## 4. Multi-scale proposal generation

A single 640px pass downsamples a 4000px-wide photo by more than 6x. An object
occupying 40 pixels in the original occupies about 6 at inference, below the
resolution at which the detector can resolve it. Additional passes at 960px and
1280px give small objects more pixels to be found in.

Cost is roughly linear in the number of scales, which is why the scale list is
per-mode rather than always maximal.

**Coordinate handling.** Two cases, handled differently because Ultralytics
treats them differently:

*Boxes* come back already mapped to original-image coordinates regardless of
`imgsz`. Verified empirically against a non-square input, so full-frame
multi-scale passes need no projection.

*Masks* do **not**. `masks.data` is at the letterboxed network resolution: an
854x480 image at `imgsz=640` yields a 384x640 mask whose content occupies only
rows 12..372, the rest being symmetric padding. Resizing that array straight to
the original shape stretches the padding into the image.
`detector.project_mask` recovers the scale from the mask's own dimensions,
crops the padding, then resizes.

Measured against Ultralytics' own polygon output as the reference:

| Method | Mask IoU vs. polygon reference |
| --- | --- |
| un-letterbox, then resize | 0.987 – 0.998 |
| naive direct resize | 0.928 – 0.987 |

*(measured on a 854x480 synthetic input at imgsz 640/960/1280)*

Tile detections are the one place the pipeline projects coordinates itself: a
tile is a genuine crop, so its boxes are translated by the tile origin and its
masks are pasted into a full-frame canvas at that origin.

## 5. Weighted Box Fusion

The original pipeline merged overlapping boxes by taking their **outer union**
and keeping the maximum confidence. That is the wrong operator in the common
case. When two passes localize one object slightly differently, the union is
strictly larger than either estimate, so repeated merges inflate boxes outward
and drag background into the crop that gets sent for identification.

Weighted Box Fusion (Solovyev et al., 2019) instead averages coordinates
weighted by confidence:

```
fused_coord = Σ(score_i · coord_i) / Σ(score_i)
fused_score = mean(score_i)
```

The mean — not the max — is the WBF convention: it rewards agreement between
passes and stops one stray high-confidence box from dominating a cluster of
weak ones. Averaging also cannot inflate a box beyond its members, which is the
property union merging lacks.

Union is still correct for **fragments**: a low-confidence pass that fires on a
sectional sofa's two halves separately produces boxes whose average covers
neither. So three operators exist, selected per cluster:

| Operator | When | Reason recorded |
| --- | --- | --- |
| `weighted_box_fusion` | members agree on location | `wbf` |
| `union_fusion` | members are fragments of one object | `fragment_union` |
| `select_by_confidence` | members are nested; any average fits neither | `containment` |

A cluster matched for several reasons resolves by priority: union dominates
(averaging fragments loses the object), then nesting, then averaging. Resolving
per cluster rather than per pair keeps the outcome independent of the order
pairs were visited.

## 6. Segmentation-aware filtering

The production model is already a segmentation checkpoint. The original code
collected masks in `run_detection_test`, threaded them through
`diagnostic_detection`, and then dropped them in `detect_fast` — every mask was
paid for and none was used. Three uses now:

**Mask IoU as a dedup signal.** Two boxes can overlap heavily while their masks
barely intersect. A lamp standing in front of a bookshelf is the canonical
case: box IoU says "same thing", mask IoU correctly says "two things". The
inverse also occurs — an L-shaped sofa's box overlaps poorly with a second
view's box while the masks agree.

**Mask occupancy as a quality gate.** Ultralytics returns a mask for every
detection whether or not it is any good. A mask covering less than
`min_mask_occupancy` (default 5%) of its own box is usually a failed
segmentation rather than a genuinely thin object, so it is flagged
`mask_trusted = False` and deduplication ignores its mask evidence.

**Masked crops for embeddings.** A bounding-box crop of a small object on a
patterned rug is mostly rug, and its CLIP embedding describes the rug. Setting
background pixels to a constant focuses the embedding on the object.
`embedding_crop_mode` selects `bbox`, `masked`, or `both` — the last averages
the two L2-normalized vectors and renormalizes, keeping dimensionality fixed
and the two views equally weighted, which concatenation would not do without
rescaling each half and thereby invalidating the configured thresholds.

Which crop mode is better is an empirical question, so it is a benchmark
configuration (`E_masked_crops` vs `F_bbox_crops` vs `G_both_crops`) rather
than an assertion.

## 7. CLIP appearance embeddings

**Model:** OpenCLIP `ViT-B-32`, `laion2b_s34b_b79k` weights, 512-dimensional.

Chosen because `open-clip-torch` was already declared in
`backend/requirements.txt`, so it adds no dependency. SigLIP would score
slightly better on fine-grained retrieval but requires `transformers`, a much
heavier install for a container already carrying torch and ultralytics.
`ViT-B-32` is the cheapest useful variant at 49 tokens per 224x224 crop;
`ViT-B-16` quadruples token count without changing merge decisions at these
thresholds.

**The cost argument.** Similarity is needed for every *pair* of proposals, but
embeddings are computed once per *crop*:

```
E = encoder(crops)          # (N, D), rows L2-normalized
S = E @ E.T                 # (N, N) — this IS cosine similarity
```

Because rows are unit length, the Gram matrix is exactly cosine similarity, so
no per-pair normalization is needed. The naive alternative — embedding each
pair independently — costs O(N²) forward passes; at N=300 that is 89,700
encoder calls instead of 300. A unit test asserts the encoder sees exactly one
crop per proposal, so this property cannot silently regress.

Implementation details that matter: `torch.inference_mode()`, batching at
`embedding_batch_size`, normalization performed on-device before the host copy,
CUDA → MPS → CPU device selection, module-level model caching under a lock so
concurrent Flask threads load the weights once, and zero rows for crops that
fail to preprocess (a zero row scores 0 against everything, which is the
correct "no evidence" answer, whereas NaN would poison every comparison).

## 8. Geometric and semantic deduplication

The original pipeline decided duplication from box IoU with size-dependent
thresholds. That fails in both directions on real inventory photos.

*False merges.* A lamp in front of a bookshelf has high box IoU. A phone on a
desk is almost fully contained in the desk's box. Geometry cannot tell either
from a genuine duplicate.

*Missed merges.* The same sofa detected at 640px and 960px can land at IoU 0.45
— below any safe threshold — while clearly being one object.

Seven signals are computed as vectorized matrices, then a five-clause rule is
applied per candidate pair. First match wins; every clause records why.

| # | Condition | Reason | Rationale |
| --- | --- | --- | --- |
| 1 | `iou ≥ 0.60` | `iou` | Unambiguous. Geometry alone decides. |
| 2 | `mask_iou ≥ 0.55` | `mask_overlap` | Pixel agreement beats box agreement; not fooled by two objects sharing a region. |
| 3 | `iou ≥ 0.30` **and** `cos ≥ 0.92` **and** `size_ratio ≥ 0.45` | `iou+clip` | Partial overlap corroborated by appearance. Size guard stops a small object being absorbed into a much larger lookalike. |
| 4 | `containment ≥ 0.80` **and** `cos ≥ 0.95` | `containment+clip` | Nesting is the most dangerous case — nearly everything in a room is inside some larger box — so it needs the strict threshold. |
| 5 | `iou ≥ 0.10` **and** `cos ≥ 0.92` **and** `centre_dist ≤ 0.70` | `fragment_union` | Adjacent fragments of one object. |

Anything else stays separate. The rule is deliberately asymmetric in risk:
over-merging silently deletes an inventory item and its value, while
under-merging leaves a duplicate proposal the identification stage usually
reconciles. **When uncertain, keep both.**

**Why appearance alone is never sufficient.** A pair must have some geometric
or mask relationship to be considered at all. Two identical dining chairs
across the room have cosine ~1.0 and would collapse into one item otherwise.
What actually protects that case is the IoU floor: distinct adjacent objects do
not overlap, so they never reach any clause. This is asserted by a unit test.

**Clustering.** Matched pairs are unioned into connected components, so the
partition does not depend on the order pairs were examined — the original
greedy suppression kept whichever box sorted first and could split a chain of
overlapping fragments arbitrarily. Transitivity is intentional: if A matches B
and B matches C, all three are one item even if A and C were never compared.
The centre-distance and size guards in clauses 3–5 prevent that from chaining
across a row of similar objects.

**A calibration note.** On solid-colour synthetic patches, CLIP cosine
similarity between a red and a blue square measured 0.911 — flat colour fields
are out of distribution and all embed near each other. The 0.92 default sits
just above that, but the thresholds have **not** been calibrated against
labelled duplicate pairs from real inventory photos, because no such labels
exist in this repository. They are defensible defaults, not tuned optima.
`benchmarks/evaluate.py` computes duplicate precision/recall/F1 once
`duplicate_groups` annotations are supplied.

## 9. Tiled small-object detection

Implemented directly in `vision/detector.py` (`plan_tiles` +
`_run_tiled_pass`) rather than via SAHI. SAHI was already a declared
dependency but its `detect_with_sahi` function was unreachable, so it was a
large unused install; it has been removed from `requirements.txt`.

A tile is a real crop, so an object occupying 40px of a 4000px-wide photo
occupies 40px of a 768px tile — roughly 10x effective magnification versus the
full-frame pass. That is the mechanism by which tiling improves small-object
recall.

**Overlap is load-bearing.** An object straddling a tile boundary is cut in
half in both tiles and may be detected in neither. At 25% overlap, any object
smaller than a quarter of a tile lies wholly inside at least one tile. Edge
tiles are shifted inward so the last row and column are fully covered rather
than running past the image bounds. Property tests assert full pixel coverage
and in-bounds tiles across several aspect ratios.

**Degradation.** When the layout would exceed `max_tiles`, tile size grows
until it fits — degrading toward fewer, larger tiles rather than dropping
regions, which would lose recall in whichever part of the image came last. A
test asserts coverage still reaches 100% under an aggressive cap.

**Triggers.** Always in ACCURATE; otherwise when the image exceeds
`tiling_megapixel_threshold` (8 MP) or when more than
`tiling_density_threshold` (25) proposals are already *small*, meaning below
`small_object_area_frac` (1%) of the frame.

Keying the density trigger to small-object count rather than total proposal
count was a correction made during development: at a 0.005 confidence
threshold the raw total is high on every image and says nothing about whether
tiling would help. The first implementation tiled a 0.9 MP frame because its
raw count crossed 60.

## 10. Quality-gated preprocessing

The orphaned `yolo_oscf_v7.py` ran CLAHE, grayscale, gamma and Canny-overlay
passes on *every* image, then voted across them — multiplying detector cost by
the number of transforms whether or not any helped. That is likely why it never
reached production.

The logic here is inverted: measure first, and generate an enhanced variant
only when a specific measured defect suggests the detector is handicapped. A
well-exposed sharp photo — the common case — costs nothing extra and takes
exactly one pass.

| Statistic | Definition | Detects |
| --- | --- | --- |
| brightness | mean luminance | under/over-exposure |
| contrast | luminance std. dev. | washed-out, hazy frames |
| blur | variance of the Laplacian | soft focus, motion blur |

Enhancements applied to the single variant: **CLAHE** on the L channel in LAB
space (local equalization, so a dark corner brightens without blowing out a
sunlit window; chrominance untouched so the colour information embeddings rely
on is preserved), **gamma** via a 256-entry LUT, and **unsharp masking**.

Blur is recorded but is **not** an enhancement trigger. No filter recovers
detail that motion blur destroyed — sharpening amplifies surviving edges but
invents nothing — so spending a second detector pass on it is not justified by
anything measurable. The score is still useful: it explains recall in benchmark
results and is reused as a crop-quality term for video best-frame selection.

Because no enhancement resizes or warps the frame, detections from both passes
are in identical coordinates and need no inverse mapping — unlike the flip and
rotate transforms in the old code, which required per-transform coordinate
math and were a source of bugs.

## 11. Video tracking and visual re-identification

The original video path used the tracker's `track_id` directly as the inventory
identity. That makes inventory correctness entirely dependent on tracker
continuity, and motion-model trackers break continuity routinely:

- **Occlusion.** Someone walks in front of the sofa; the track dies and the
  sofa gets a fresh ID and a second inventory entry.
- **Re-entry.** The user pans across a room and pans back. The old track
  expired, so every item is counted twice.
- **Fast motion.** A handheld pan moves objects far between frames, IoU
  association fails, and the ID switches mid-object.

Each of these *inflates* the claim, which is worse than missing an item: it
makes the total indefensible.

**The fix is an identity layer above the tracker.** Each inventory item keeps a
CLIP descriptor — the running mean of its observed crop embeddings,
renormalized to unit length — and a new tracker ID is matched against the
gallery before being admitted as a new object. The tracker keeps doing what it
is good at (cheap, precise frame-to-frame continuity) while identity across
longer gaps is decided by appearance, which survives occlusion. This is the
standard tracking-by-appearance arrangement of DeepSORT and its descendants,
applied to inventory identity rather than per-frame association.

A running mean beats keeping the first or best embedding: it averages out
viewpoint and lighting variation, so matching improves as an object is seen
from more angles.

**Guards against the opposite failure.** Appearance matching creates duplicates
in the other direction — a pair of matching dining chairs looks identical to
CLIP. Two guards:

1. A high similarity threshold (`reid_similarity_threshold`, default 0.90).
2. **Items currently visible in the same frame never merge.** Two things
   visible simultaneously cannot be one object. This is a physical
   impossibility constraint, not a tunable, and it is what makes appearance
   matching safe to use at all.

**Embedding cost control.** A CLIP pass on every detection in every frame would
dominate runtime — a 30-second clip at 20 FPS with 10 objects per frame is
6,000 crops. Embeddings are computed only for detections that need an identity
decision (an unrecognized tracker ID, or a periodic refresh every 15 frames so
the descriptor keeps improving), and all crops needing one in a given frame go
through the encoder as a single batch.

**Best-frame selection.** The crop kept as an item's thumbnail is chosen by a
weighted score, not by confidence alone:

| Term | Weight | Transform | Why |
| --- | --- | --- | --- |
| detector confidence | 0.40 | — | |
| area fraction | 0.25 | `sqrt` | Raw area is dominated by a few huge objects; without the root, every item's best frame is whichever one the camera got closest to, however blurred. |
| sharpness | 0.25 | `v / (v + threshold)` | Saturating rather than a hard cutoff, so a slightly soft crop is penalized rather than disqualified — useful when every frame of an object is soft. |
| centrality | 0.10 | — | Objects at the frame border are usually clipped, and a clipped crop is a poor thumbnail even at high confidence. |

**Measured outcome on the one video in this repository.** Re-identification
fired **zero** times. The mechanism ran — 16 attempts had a non-empty gallery —
but the best-match cosine similarity peaked at 0.835 against a 0.90 threshold:

```
re-id best-match similarity over 16 attempts (threshold 0.90)
  min 0.625   p50 0.742   p90 0.816   max 0.835
  would match at:  >=0.70: 10   >=0.75: 7   >=0.80: 4   >=0.85: 0   >=0.90: 0
```

This is reported rather than tuned away. Lowering the threshold to 0.80 would
produce four merges, but there is no labelled evidence that those four are the
same objects rather than four distinct lookalikes, and a wrong merge deletes an
item. The similarity distribution and threshold sweep are now recorded on every
run precisely so this stays visible: a threshold that never fires is otherwise
indistinguishable from a broken feature, since both show "0 re-id events".

The mechanism itself is verified by unit tests that construct a genuine
re-entry (same descriptor, new tracker ID, after the old track expired) and
assert a single identity results, plus the adversarial case (identical
descriptors coexisting in one frame) and assert two identities result.

## 12. Benchmark architecture

```
benchmarks/
  run_cv_benchmark.py     ablation over an image directory
  evaluate.py             scores results against ground truth
  resume_metrics.py       derives deltas between configurations
  run_video_benchmark.py  tracker-only vs. re-identification
```

**Ablation configurations**, each isolating one change:

| Config | Description | Isolates |
| --- | --- | --- |
| `A_baseline` | single scale, greedy IoU suppression, no fusion/masks/appearance | the control (the original algorithm) |
| `B_multiscale_wbf` | multi-scale + weighted box fusion, geometry only | multi-scale + WBF |
| `C_embeddings` | B + CLIP appearance in the dedup decision | appearance |
| `D_full` | ACCURATE scales + tiling + masks + embeddings | tiling + third scale |

Optional: `E_masked_crops` / `F_bbox_crops` / `G_both_crops` answer the crop-mode
question from §6; `H_fast` runs FAST through the enhanced code path.

`A_baseline` runs `VisionPipeline.process_baseline`, which is the *actual*
original algorithm (two low-confidence single-scale passes, then greedy
suppression) rather than an approximation of it. `fusion.greedy_iou_suppression`
is retained solely so the control is honest.

**Metric tiers.** The framework separates what it can measure from what it
cannot, and never fabricates the latter:

- *No labels needed* — raw and final proposal counts, per-image means,
  reduction ratio, per-stage latency, throughput, peak RSS, merge-reason
  counts, tiled-image count, small-object counts, and every video association
  counter. Always reported.
- *Labels required* — precision, recall, F1, mAP@0.5, mAP@0.5:0.95,
  small-object recall, duplicate precision/recall/F1. Reported only when an
  annotation file is supplied.

**This repository ships no annotated dataset.** `evaluate.py` exits with a
message explaining exactly how to add one rather than emitting numbers, and
`--make-template` generates a pre-populated skeleton so only the boxes need
filling in. `resume_metrics.py` emits `null` plus a `reason` string for every
label-dependent metric and warns when the sample size is under 25 images.

Because the repository contains a room video but no image corpus,
`--from-video` samples frames into a benchmark set from what is actually here.

## 13. Latency and accuracy tradeoffs

| Mode | Scales | Tiling | Masks | Embeddings | Intent |
| --- | --- | --- | --- | --- | --- |
| `FAST` | 640 | no | no | no | preserves the original latency profile |
| `BALANCED` | 640, 960 | on trigger | yes | yes | interactive default |
| `ACCURATE` | 640, 960, 1280 | always | yes | yes | maximum recall; batch/offline |

Expected costs, stated as the shape of the tradeoff:

- **Multi-scale** — roughly linear in scale count for the detector stage.
- **Tiling** — grows with tile count, which grows quadratically as tile size
  shrinks relative to the image. Hence the gating.
- **Embeddings** — one extra forward pass over N crops, capped by
  `max_proposals`, so a bounded fixed cost rather than a per-pair one.
- **Deduplication** — O(N²) in arithmetic but vectorized as matrix ops; the
  Python-level loop runs only over pairs with some geometric relationship.
- **Preprocessing** — a whole extra detector pass, hence the quality gate.

**Where the time actually goes.** Detector inference dominates the perception
stage by roughly two orders of magnitude over everything downstream. Fusion,
capping and deduplication are sub-millisecond at realistic proposal counts.
Embedding is the only other non-trivial cost.

Note also that end-to-end request latency is dominated by the **Gemini call**,
not by perception. Detector work that improves proposal quality without
increasing crop count is therefore closer to latency-neutral overall than the
perception-stage numbers alone suggest.

Measured figures live in `benchmarks/results/`. See the accompanying report for
the numbers obtained on this machine; they are not restated here so that this
document cannot drift out of sync with the measurements.

**Performance measures implemented:** models loaded once per process and cached
at module level under a lock; `VisionPipeline.warmup()` called before the
server binds its port (cold-loading CLIP alone measured ~35 s); batched
embedding; `torch.inference_mode()`; on-device normalization; vectorized
similarity and geometry; proposal caps before per-crop work; candidate-pair
prefiltering so the Python loop stays well below N²; and `StageTimer`
instrumentation on every stage, surfaced in the API response's `detection`
block and in benchmark output.

## 14. Configuration

Every threshold lives on the `VisionConfig` dataclass in `vision/config.py`.
There are no magic numbers elsewhere in the package. The dataclass is frozen,
so a pipeline cannot be reconfigured mid-request; `with_overrides()` derives
variants, which is how the benchmark builds its ablations.

Any field is overridable from the environment with a `CR_VISION_` prefix:

```bash
CR_VISION_MODE=BALANCED
CR_VISION_MAX_PROPOSALS=200
CR_VISION_EMBEDDING_SIMILARITY_THRESHOLD=0.94
CR_VISION_SCALES="640 960"
CR_VISION_ENABLE_TILING=true
```

Precedence, lowest to highest: mode preset → environment → explicit keyword
argument. Environment sits below explicit arguments so tests and benchmarks
stay deterministic regardless of the shell, and above presets so production can
retune a deployed build. Unknown or malformed variables are logged and ignored
rather than raising, so a stray variable cannot prevent the server starting.

`GET /api/vision-config` returns the resolved configuration of a running
instance.

## 15. Known weaknesses

Stated plainly, because each is a real limitation rather than a rough edge.

1. **No annotated dataset, so no accuracy measurement.** Every precision,
   recall and mAP number is unavailable. Proposal counts and latency are
   measured; detection *quality* is not. This is the single biggest gap.

2. **Deduplication thresholds are uncalibrated.** The values in §8 are
   reasoned defaults, not optima. Calibrating them needs labelled duplicate
   pairs from real inventory photos.

3. **Re-identification never fired on the available footage.** §11 gives the
   distribution. Whether 0.90 is too strict or the video simply contains no
   re-entries cannot be settled without labels.

4. **Fragment union is the most speculative clause.** It is off in FAST, and
   its firing count is reported separately rather than folded into a total, but
   it has not been validated against ground truth.

5. **Small-object recall improvement from tiling is unquantified.** The
   mechanism is sound and the tile coverage is tested, but "improves
   small-object recall" is an argument from resolution, not a measurement.

6. **Benchmark corpus is small and homogeneous.** Frames sampled from one
   video of one room. Conclusions drawn from it should be treated as
   directional.

7. **Masks are stored full-frame.** Simplifies mask IoU to a direct array
   operation, but costs roughly 0.9 MB per mask on a 1280x720 frame. Bounded by
   `max_proposals`, and `pre_dedup_proposals` retention is gated behind the
   debug flag, but it is real memory pressure in ACCURATE mode on large images.

8. **CPU-only deployment restricts the default mode.** The container defaults
   to FAST because BALANCED's CLIP pass is slow without a GPU, so the shipped
   default does not exercise the appearance-based work.

9. **Still running the Flask development server.** `gunicorn` is installed but
   unused; worker count needs sizing against per-worker model memory, which has
   not been measured.

10. **The legacy `api.py` / `app.py` path remains.** Its `process_image` is
    still class-based and does not use the pipeline, because its inventory keys
    are built from COCO labels. Documented in `docs/deployment.md`; the
    frontend does not call it.
