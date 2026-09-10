"""Segmentation mask handling.

The production model is already a segmentation checkpoint (``yolo11x-seg.pt``),
and the original pipeline collected masks in ``run_detection_test``, threaded
them through ``diagnostic_detection``, and then dropped them in ``detect_fast``.
Every mask was paid for and none was used. This module puts them to work.

Three uses:

1. **Mask IoU as a dedup signal.** Two boxes can overlap heavily while their
   masks barely intersect — think of a lamp standing in front of a bookshelf.
   Box IoU says "same thing"; mask IoU correctly says "two things". Conversely
   an L-shaped sofa and its own bounding box overlap poorly with a second view's
   box while the masks agree.

2. **Mask occupancy as a mask-quality gate.** Ultralytics returns a mask for
   every detection whether or not it is any good. A mask covering a tiny
   fraction of its own box is usually a failed segmentation, not a genuinely
   thin object, so it is marked untrustworthy rather than believed.

3. **Masked crops for embeddings.** A bounding-box crop of a small object on a
   patterned rug is mostly rug, and a CLIP embedding of it describes the rug.
   Zeroing the background focuses the embedding on the object.

Mask coordinate handling
------------------------
Ultralytics returns masks at the network's input resolution, not the original
image resolution, and multi-scale inference means different passes return
different mask sizes. Masks are therefore resized to full original-image
dimensions on ingest. Storing them full-frame costs memory but makes mask IoU a
direct array operation rather than a coordinate-alignment problem — and the
proposal cap bounds how many are ever held at once.
"""

from __future__ import annotations

import logging
from typing import Sequence

import cv2
import numpy as np

from .config import VisionConfig
from .proposals import Proposal

logger = logging.getLogger(__name__)


def resize_mask(mask: np.ndarray, width: int, height: int, threshold: float = 0.5) -> np.ndarray:
    """Resize a float or binary mask to ``(height, width)`` and binarize.

    Uses linear interpolation then thresholds, rather than nearest-neighbour, so
    that upsampling a coarse network-resolution mask produces smooth object
    boundaries instead of blocky stair-steps.
    """
    if mask.ndim != 2:
        raise ValueError(f"expected a 2-D mask, got shape {mask.shape}")

    if mask.shape == (height, width):
        resized = mask.astype(np.float32, copy=False)
    else:
        resized = cv2.resize(
            mask.astype(np.float32, copy=False),
            (width, height),
            interpolation=cv2.INTER_LINEAR,
        )
    return (resized > threshold).astype(np.uint8)


def mask_area(mask: "np.ndarray | None") -> float:
    if mask is None:
        return 0.0
    return float(np.count_nonzero(mask))


def mask_iou(mask_a: "np.ndarray | None", mask_b: "np.ndarray | None") -> float:
    """Intersection over union of two binary masks.

    Returns 0.0 when either mask is missing, so a caller can treat "no mask
    evidence" and "masks disagree" identically without a separate branch. The
    pipeline never *requires* mask agreement to merge; it only uses it as
    additional supporting evidence.
    """
    if mask_a is None or mask_b is None:
        return 0.0
    if mask_a.shape != mask_b.shape:
        raise ValueError(f"mask shapes differ: {mask_a.shape} vs {mask_b.shape}")

    a = mask_a.astype(bool, copy=False)
    b = mask_b.astype(bool, copy=False)
    intersection = float(np.count_nonzero(a & b))
    if intersection == 0.0:
        return 0.0
    union = float(np.count_nonzero(a | b))
    return intersection / union if union > 0.0 else 0.0


def mask_containment(inner: "np.ndarray | None", outer: "np.ndarray | None") -> float:
    """Fraction of ``inner``'s pixels that fall inside ``outer``."""
    if inner is None or outer is None:
        return 0.0
    if inner.shape != outer.shape:
        raise ValueError(f"mask shapes differ: {inner.shape} vs {outer.shape}")

    a = inner.astype(bool, copy=False)
    inner_area = float(np.count_nonzero(a))
    if inner_area == 0.0:
        return 0.0
    return float(np.count_nonzero(a & outer.astype(bool, copy=False))) / inner_area


def bbox_occupancy(mask: "np.ndarray | None", bbox: Sequence[float]) -> float:
    """Fraction of the bounding box covered by the mask.

    Computed over the box region only, not the whole frame, so a small object's
    score is not diluted by image size.
    """
    if mask is None:
        return 0.0
    x1, y1, x2, y2 = (int(round(v)) for v in bbox[:4])
    height, width = mask.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(width, x2), min(height, y2)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    region = mask[y1:y2, x1:x2]
    box_pixels = region.size
    if box_pixels == 0:
        return 0.0
    return float(np.count_nonzero(region)) / float(box_pixels)


def pairwise_mask_iou(masks: Sequence["np.ndarray | None"]) -> np.ndarray:
    """``(N, N)`` mask-IoU matrix, computed only for pairs that can overlap.

    Mask IoU cannot be expressed as a single dense matrix product the way box
    IoU can, so this flattens each mask to a packed bit array and uses
    ``np.bitwise_and`` over pairs. Pairs where either mask is missing stay 0.

    The loop is over pairs, but each iteration is a vectorized bitwise op over
    packed bytes rather than per-pixel Python work. Callers should restrict
    input to post-cap proposals; this is the most expensive geometric signal.
    """
    count = len(masks)
    result = np.zeros((count, count), dtype=np.float64)
    if count == 0:
        return result

    # Pack to bits: an ~8x memory reduction and a matching speedup on the
    # bitwise ops, which dominate here.
    packed: list["np.ndarray | None"] = []
    areas = np.zeros(count, dtype=np.float64)
    for idx, mask in enumerate(masks):
        if mask is None:
            packed.append(None)
            continue
        flat = np.packbits(mask.astype(bool, copy=False).reshape(-1))
        packed.append(flat)
        areas[idx] = float(np.count_nonzero(mask))

    valid = [i for i, p in enumerate(packed) if p is not None and areas[i] > 0]
    for pos, i in enumerate(valid):
        result[i, i] = 1.0
        for j in valid[pos + 1 :]:
            pi, pj = packed[i], packed[j]
            if pi.shape != pj.shape:
                raise ValueError("all masks must share the same shape")
            intersection = float(np.unpackbits(pi & pj).sum())
            if intersection == 0.0:
                continue
            union = areas[i] + areas[j] - intersection
            value = intersection / union if union > 0.0 else 0.0
            result[i, j] = value
            result[j, i] = value
    return result


def attach_mask_statistics(proposals: Sequence[Proposal], config: VisionConfig) -> None:
    """Record mask area, occupancy and a trust flag on each proposal.

    Proposals whose occupancy falls below ``min_mask_occupancy`` keep their mask
    array (visualization still shows it) but are flagged
    ``mask_trusted = False``, and deduplication ignores mask evidence for them.
    """
    for proposal in proposals:
        if proposal.mask is None:
            proposal.metadata["mask_trusted"] = False
            continue
        area = mask_area(proposal.mask)
        occupancy = bbox_occupancy(proposal.mask, proposal.bbox)
        proposal.metadata["mask_area"] = area
        proposal.metadata["mask_bbox_occupancy"] = round(occupancy, 4)
        proposal.metadata["mask_trusted"] = occupancy >= config.min_mask_occupancy
        if not proposal.metadata["mask_trusted"]:
            logger.debug(
                "proposal %d mask occupancy %.3f below %.3f; ignoring mask evidence",
                proposal.proposal_id,
                occupancy,
                config.min_mask_occupancy,
            )


def trusted_masks(proposals: Sequence[Proposal]) -> list["np.ndarray | None"]:
    """Masks for proposals that passed the occupancy gate; ``None`` otherwise."""
    out: list["np.ndarray | None"] = []
    for proposal in proposals:
        if proposal.mask is not None and proposal.metadata.get("mask_trusted", True):
            out.append(proposal.mask)
        else:
            out.append(None)
    return out


def extract_bbox_crop(image: np.ndarray, bbox: Sequence[float], pad_frac: float = 0.0) -> "np.ndarray | None":
    """Crop ``image`` to ``bbox``, optionally padded by a fraction of box size.

    Returns ``None`` for degenerate boxes so callers can skip rather than having
    to guard against zero-size arrays.
    """
    height, width = image.shape[:2]
    x1, y1, x2, y2 = (float(v) for v in bbox[:4])
    if pad_frac > 0.0:
        pad_x = (x2 - x1) * pad_frac
        pad_y = (y2 - y1) * pad_frac
        x1, y1, x2, y2 = x1 - pad_x, y1 - pad_y, x2 + pad_x, y2 + pad_y

    ix1 = max(0, int(round(x1)))
    iy1 = max(0, int(round(y1)))
    ix2 = min(width, int(round(x2)))
    iy2 = min(height, int(round(y2)))
    if ix2 <= ix1 or iy2 <= iy1:
        return None

    crop = image[iy1:iy2, ix1:ix2]
    return crop if crop.size else None


def extract_masked_crop(
    image: np.ndarray,
    bbox: Sequence[float],
    mask: "np.ndarray | None",
    background: int = 0,
    pad_frac: float = 0.0,
) -> "np.ndarray | None":
    """Crop to ``bbox`` with pixels outside ``mask`` replaced by ``background``.

    Falls back to a plain bbox crop when no mask is available, so a caller can
    request masked crops uniformly without checking mask presence per proposal.

    The background is filled with a constant rather than blurred or inpainted.
    A constant is what CLIP's training distribution tolerates best of the cheap
    options, and anything fancier would add cost to a per-proposal operation for
    an effect the benchmark can't currently distinguish.
    """
    crop = extract_bbox_crop(image, bbox, pad_frac=pad_frac)
    if crop is None or mask is None:
        return crop

    height, width = image.shape[:2]
    x1, y1, x2, y2 = (float(v) for v in bbox[:4])
    if pad_frac > 0.0:
        pad_x = (x2 - x1) * pad_frac
        pad_y = (y2 - y1) * pad_frac
        x1, y1, x2, y2 = x1 - pad_x, y1 - pad_y, x2 + pad_x, y2 + pad_y

    ix1 = max(0, int(round(x1)))
    iy1 = max(0, int(round(y1)))
    ix2 = min(width, int(round(x2)))
    iy2 = min(height, int(round(y2)))

    mask_region = mask[iy1:iy2, ix1:ix2]
    if mask_region.shape[:2] != crop.shape[:2]:
        logger.debug("mask region %s does not match crop %s; using bbox crop", mask_region.shape, crop.shape)
        return crop
    if not np.any(mask_region):
        # An all-zero mask over this box would blank the crop entirely; the
        # bbox crop is strictly more informative than a black square.
        return crop

    out = crop.copy()
    keep = mask_region.astype(bool, copy=False)
    if out.ndim == 3:
        out[~keep] = background
    else:
        out[~keep] = background
    return out


def merge_masks(masks: Sequence["np.ndarray | None"]) -> "np.ndarray | None":
    """Union of several binary masks, used when fusing a cluster."""
    present = [m for m in masks if m is not None]
    if not present:
        return None
    accumulator = present[0].astype(bool, copy=True)
    for mask in present[1:]:
        if mask.shape != accumulator.shape:
            raise ValueError("all masks must share the same shape")
        accumulator |= mask.astype(bool, copy=False)
    return accumulator.astype(np.uint8)


__all__ = [
    "attach_mask_statistics",
    "bbox_occupancy",
    "extract_bbox_crop",
    "extract_masked_crop",
    "mask_area",
    "mask_containment",
    "mask_iou",
    "merge_masks",
    "pairwise_mask_iou",
    "resize_mask",
    "trusted_masks",
]
