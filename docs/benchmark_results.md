# Measured benchmark results

Every number in this file came out of a run on the machine and dataset
described below. Nothing here is estimated, extrapolated, or carried over from
a paper. Raw JSON lives in `benchmarks/results/`, which is gitignored because
the per-proposal detail runs to megabytes.

**Reproduce with:**

```bash
python -m benchmarks.run_cv_benchmark \
    --from-video backend/testtt.mp4 --frame-interval 24 \
    --model yolo11x-seg.pt \
    --configs A_baseline B_multiscale_wbf C_embeddings D_full \
    --output benchmarks/results/main_benchmark.json
```

## Environment

| | |
| --- | --- |
| Platform | macOS 15.7.7, arm64 (Apple Silicon) |
| Compute | MPS available; **no CUDA** |
| torch | 2.14.0 |
| ultralytics | 8.4.146 |
| Detector weights | `yolo11x-seg.pt` (the production checkpoint) |
| Appearance encoder | OpenCLIP `ViT-B-32`, `laion2b_s34b_b79k`, 512-d |

## Dataset and its limitations

31 frames sampled every 24th frame from `backend/testtt.mp4`, a handheld
720x1280 walkthrough of a dorm room — the only video in the repository.

**This is a small, homogeneous corpus from a single room.** Treat every figure
below as directional rather than a general characterization. It is also
**unannotated**, so no precision, recall or mAP figure appears anywhere in this
document.

## 1. Main ablation

Each configuration adds one thing to the previous, so the deltas isolate
individual contributions.

| Config | raw | final | reduction | mean s | p50 s | p90 s | img/s | tiled | small obj | peak RSS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `A_baseline` | 1030 | 483 | 53.1% | 0.703 | 0.683 | 0.775 | 1.416 | 0/31 | 437 | 1214 MB |
| `B_multiscale_wbf` | 2013 | 557 | 72.3% | 1.864 | 1.648 | 2.538 | 0.536 | 10/31 | 591 | 1306 MB |
| `C_embeddings` | 2013 | 543 | 73.0% | 2.851 | 2.437 | 4.139 | 0.350 | 10/31 | 591 | 1339 MB |
| `D_full` | 2986 | 639 | 78.6% | 5.673 | 5.421 | 6.533 | 0.176 | 31/31 | 761 | 1831 MB |

`peak_gpu_mb` is `None` throughout: only CUDA exposes a reliable peak-memory
counter, and this machine has none. Reporting a number would have meant
inventing one.

### What each step actually bought

**A → B (multi-scale + weighted box fusion).** Raw proposals nearly doubled,
1030 → 2013 (+189.9% at the D_full end of the sweep), yet final proposals rose
only 483 → 557 (+15.3%). Reduction ratio went 53.1% → 72.3%. Read together
these say the second scale surfaced a large number of additional candidates
and fusion absorbed most of them as redundant rather than passing them
downstream. Cost: 0.70 s → 1.86 s.

**B → C (CLIP appearance in the dedup decision).** Final proposals fell
557 → 543, i.e. **14 fewer** across 31 images. Those merges are attributable:
9–12 `iou+clip`, 1 `containment+clip`, 1 `fragment_union`. Every one is a pair
that geometry alone left separate and appearance resolved. Cost: 1.86 s →
2.85 s, of which 0.30 s is embedding.

This is a real but modest effect. It is **not** evidence that the 14 merges
were correct — that needs labels.

**C → D (third scale + tiling + masks).** Raw 2013 → 2986, final 543 → 639,
reduction 73.0% → 78.6%. Small-object proposals rose 591 → 761. Cost: 2.85 s →
5.67 s. Tiling ran on all 31 images because ACCURATE forces it.

The most striking figure here is the merge breakdown: **47 `mask_overlap`
merges**, far more than any appearance clause produced. Segmentation masks are
the single largest contributor to deduplication decisions, which retrospectively
justifies computing them — the original pipeline generated these masks and
discarded them unused.

### Merge reasons by configuration

| Config | `mask_overlap` | `iou+clip` | `containment+clip` | `fragment_union` |
| --- | --- | --- | --- | --- |
| `A_baseline` | — | — | — | — |
| `B_multiscale_wbf` | — | — | — | — |
| `C_embeddings` | — | 12 | 1 | 1 |
| `D_full` | 47 | — | 1 | 3 |

`A` and `B` are blank because they are geometry-only: `A` uses greedy
suppression, which discards rather than merging, and `B` has neither masks nor
embeddings, so only clause 1 can fire (recorded as plain `iou`, folded into the
count reduction).

Note that `D_full` shows no `iou+clip` merges. With masks enabled, clause 2
(`mask_overlap`) is evaluated before clause 3 and claims those pairs first.

## 2. Latency breakdown

Mean seconds per image, per stage.

| Stage | `A_baseline` | `B_multiscale` | `C_embeddings` | `D_full` |
| --- | --- | --- | --- | --- |
| detection | 0.7031 | 1.8635 | 2.5494 | **5.2107** |
| embedding | — | — | 0.3005 | 0.3712 |
| deduplication | 0.0002 | 0.0001 | 0.0004 | 0.0816 |
| crops for embedding | — | — | 0.0000 | 0.0079 |
| prefusion | 0.0000 | 0.0005 | 0.0006 | 0.0009 |
| similarity (`E @ E.T`) | — | — | 0.0002 | 0.0003 |
| proposal cap | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| final crops | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **total** | **0.7034** | **1.8642** | **2.8511** | **5.6726** |

**Detection is 92% of D_full and over 99% of A_baseline.** Everything the
upgrade added downstream of the detector — fusion, capping, similarity,
deduplication — sums to under 0.09 s even in the heaviest configuration. The
0.0003 s similarity figure is the vectorized `E @ E.T`; the alternative of
embedding each pair independently would have been O(N²) encoder calls.

Two consequences worth stating plainly:

1. Optimizing the fusion or dedup code would be pointless. Any meaningful
   latency work belongs in the detector: fewer scales, smaller weights, or
   batching the scale passes.
2. Request latency is dominated by the **Gemini call**, not by perception, so
   these perception-stage numbers overstate the user-visible impact of mode
   choice.

## 3. Embedding crop mode (answers the §6 question)

Run separately on 34 frames from the same video:

```bash
python -m benchmarks.run_cv_benchmark \
    --images benchmarks/results/frames/testtt --model yolo11x-seg.pt \
    --configs F_bbox_crops E_masked_crops G_both_crops
```

| Config | crop mode | raw | final | mean s | embed s | appearance-driven merges |
| --- | --- | --- | --- | --- | --- | --- |
| `F_bbox_crops` | `bbox` | 2078 | 522 | 2.922 | 0.2510 | 11 |
| `E_masked_crops` | `masked` | 2078 | 527 | 3.037 | 0.2499 | **6** |
| `G_both_crops` | `both` | 2078 | 519 | 2.928 | 0.3760 | **14** |

*(appearance-driven = `iou+clip` + `containment+clip` + `fragment_union`;
`mask_overlap` was 50 in all three and is excluded because it does not depend
on the crop mode)*

**Masking the background made things worse, not better.** Masked-only crops
produced roughly half the appearance-driven merges of bbox crops (6 vs 11) and
were the slowest of the three. The plausible mechanism: zeroing the background
pushes a crop away from CLIP's training distribution — natural photographs, not
objects on flat black — so genuinely similar objects score *lower* against each
other, and the similarity threshold stops being reached.

`both` produced the most appearance-driven merges (14) at essentially bbox-mode
latency (2.928 s vs 2.922 s), despite a higher embedding cost, because it needs
two encoder passes but the extra time is absorbed elsewhere.

**Action taken:** ACCURATE mode's default was changed from `MASKED` to `BOTH`
on the strength of this measurement. The original `MASKED` default was a guess.

**Caveat.** The spread in final counts is 519–527, about 1.5% of ~520, over 34
images. And fewer final proposals is *not* automatically better — it is equally
consistent with over-merging. What is solid is the merge-count direction and
the mechanism; the ranking should be re-tested on labelled data before being
treated as settled.

## 4. Video association

```bash
python -m benchmarks.run_video_benchmark \
    --video backend/testtt.mp4 --model yolo11l.pt --target-fps 10
```

242 frames processed from the full clip.

| Metric | tracker IDs only | with re-identification |
| --- | --- | --- |
| frames processed | 242 | 242 |
| tracker IDs generated | 19 | 19 |
| inventory identities | 20 | 20 |
| confirmed identities | 17 | 17 |
| re-id attempts with a non-empty gallery | 0 | 16 |
| **re-id events** | 0 | **0** |
| ID switches absorbed | 0 | 0 |
| wall clock | 39.3 s | 42.2 s |

**Re-identification fired zero times.** This is reported rather than tuned
away, and the instrumentation exists to explain why:

```
re-id best-match similarity over 16 attempts (threshold 0.90)
  min 0.625   p50 0.742   p90 0.816   max 0.835
  attempts that would match at:
    >= 0.70: 10    >= 0.75: 7    >= 0.80: 4
    >= 0.85: 0     >= 0.90: 0    >= 0.95: 0
```

The mechanism ran — 16 attempts had candidates to compare against — but the
best match never exceeded 0.835 against a 0.90 threshold.

Two explanations fit equally well and the data cannot separate them:

1. 0.90 is too strict for handheld, motion-blurred phone footage.
2. This clip genuinely contains no re-entries. The camera walks *forward*
   through rooms, so objects leave and mostly do not return.

Lowering the threshold to 0.80 would manufacture 4 merges, but there is no
labelled evidence they are the same objects rather than four distinct
lookalikes, and a wrong merge deletes an inventory item. So the threshold was
left alone and the distribution is now recorded on every run — because a
threshold that never fires is otherwise indistinguishable from a broken
feature, since both report "0 re-id events".

One incidental finding: **20 inventory identities from 19 tracker IDs.** More
identities than IDs means the tracker reused at least one ID for a different
object after the original went stale. That is direct evidence of the ID churn
the memory bank is designed to handle, even though appearance did not clear the
bar to correct it here.

Correctness metrics (identity inflation, duplicate entries) require a
hand-counted true object count; pass `--true-object-count N` to compute them.

## 5. What is not measured

| Metric | Status | Blocker |
| --- | --- | --- |
| precision / recall / F1 | **unavailable** | no ground-truth boxes |
| mAP@0.5, mAP@0.5:0.95 | **unavailable** | no ground-truth boxes |
| small-object recall | **unavailable** | no ground-truth boxes |
| duplicate precision / recall / F1 | **unavailable** | no `duplicate_groups` annotations |
| video identity inflation | **unavailable** | no hand-counted object totals |
| peak GPU memory | **unavailable** | no CUDA device on this machine |

The framework computes all of these; the labels do not exist. To add them:

```bash
python -m benchmarks.evaluate --results benchmarks/results/main_benchmark.json \
    --make-template benchmarks/data/annotations.json
# fill in the boxes, then
python -m benchmarks.evaluate --results benchmarks/results/main_benchmark.json \
    --annotations benchmarks/data/annotations.json --output benchmarks/results/eval.json
python -m benchmarks.resume_metrics --results benchmarks/results/main_benchmark.json \
    --evaluation benchmarks/results/eval.json
```

Until then, **the proposal-count and latency figures above quantify redundancy
removal and cost, not correctness.** A higher reduction ratio means more
proposals were collapsed; whether the survivors are the right ones is a
separate question this dataset cannot answer.
