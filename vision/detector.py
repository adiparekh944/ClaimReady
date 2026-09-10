"""Multi-scale, class-agnostic YOLO proposal generation.

Why class-agnostic
------------------
YOLO here is an *objectness* proposer, not a classifier. It runs with
``agnostic_nms=True`` and its predicted class labels are discarded. The reason
is that the checkpoint's label set is COCO's 80 categories — ``chair``,
``couch``, ``tv``, ``vase`` — which is close to useless for insurance, where the
answer needs to be "Herman Miller Aeron, ~$1,200". An open-vocabulary
multimodal model handles naming and valuation downstream, so this stage only has
to answer "is there an object here, and where".

That division of labour is what justifies the very low confidence thresholds. A
false positive costs one extra crop for the downstream model to reject; a false
negative is an item missing from someone's insurance claim. So the operating
point is deliberately pushed toward recall, and the cost is controlled by fusion
and a proposal cap rather than by raising the threshold.

Why multi-scale
---------------
A single 640px pass downsamples a 4000px-wide photo by more than 6x. Objects
that occupy 40 pixels in the original are 6 pixels at inference and fall below
the detector's effective receptive resolution. Running additional passes at
960px and 1280px gives small objects more pixels to be found in. Cost is roughly
linear in the number of scales, which is why the scale list is per-mode.

Coordinate handling
-------------------
Two things need care, and they are handled differently because Ultralytics
treats them differently:

*Boxes.* Ultralytics already maps predicted boxes back to original-image
coordinates regardless of ``imgsz``, so full-frame multi-scale passes need no
projection. Verified empirically against a non-square input.

*Masks.* ``masks.data`` is **not** in original coordinates. It is at the
letterboxed network resolution — a 854x480 input at ``imgsz=640`` yields a
384x640 mask whose content occupies only rows 12..372, the rest being padding.
Resizing that array straight to the original shape stretches the padding into
the image. :func:`project_mask` removes the padding first. Measured against
Ultralytics' own polygon output as reference, un-letterboxing scores 0.987-0.998
mask IoU versus 0.928-0.987 for a naive resize.

Tile detections are the one case needing explicit projection: a tile is a real
crop, so its boxes and masks are translated by the tile origin.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

import cv2
import numpy as np

from . import preprocessing, segmentation
from .config import VisionConfig
from .preprocessing import ImageQuality
from .proposals import (
    SOURCE_ENHANCED,
    SOURCE_FULL_FRAME,
    SOURCE_SECONDARY,
    SOURCE_TILE,
    Proposal,
    assign_ids,
    filter_small,
)

logger = logging.getLogger(__name__)

# Cache keyed by weights path so a web worker loads each checkpoint once.
_MODEL_CACHE: dict[str, Any] = {}


def load_model(model_path: str) -> Any:
    """Load and cache an Ultralytics model."""
    cached = _MODEL_CACHE.get(model_path)
    if cached is not None:
        return cached
    from ultralytics import YOLO

    logger.info("loading YOLO weights %s", model_path)
    model = YOLO(model_path)
    _MODEL_CACHE[model_path] = model
    return model


def project_mask(mask: np.ndarray, width: int, height: int, threshold: float = 0.5) -> np.ndarray:
    """Map a network-resolution mask into original-image coordinates.

    Ultralytics letterboxes the input: the image is scaled so its long side
    fits the inference size, then symmetrically padded to a multiple of the
    stride. The returned mask covers that padded canvas. This reverses the
    process by recovering the scale factor from the mask's own dimensions,
    cropping away the padding, and resizing the remaining content.

    Deriving the scale from ``min(mask_w / width, mask_h / height)`` rather than
    from the requested ``imgsz`` means this stays correct even when Ultralytics
    rounds the padded shape differently than expected.
    """
    if mask.ndim != 2:
        raise ValueError(f"expected a 2-D mask, got shape {mask.shape}")
    if width <= 0 or height <= 0:
        raise ValueError(f"invalid target size {width}x{height}")

    mask_h, mask_w = mask.shape[:2]
    scale = min(mask_w / width, mask_h / height)
    content_w = int(round(width * scale))
    content_h = int(round(height * scale))
    pad_x = max(0, (mask_w - content_w) // 2)
    pad_y = max(0, (mask_h - content_h) // 2)

    core = mask[pad_y : pad_y + content_h, pad_x : pad_x + content_w]
    if core.size == 0:
        core = mask
    return segmentation.resize_mask(core, width, height, threshold=threshold)


@dataclass
class DetectionPass:
    """One detector invocation and what it produced."""

    name: str
    source_pass: str
    scale: int
    confidence: float
    proposal_count: int
    duration_s: float
    tile_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source_pass": self.source_pass,
            "scale": self.scale,
            "confidence": self.confidence,
            "proposal_count": self.proposal_count,
            "duration_s": round(self.duration_s, 4),
            "tile_count": self.tile_count,
        }


@dataclass
class DetectionResult:
    """Raw proposals from every pass, before fusion."""

    proposals: list[Proposal]
    passes: list[DetectionPass] = field(default_factory=list)
    quality: "ImageQuality | None" = None
    tiled: bool = False
    # Proposals below ``small_object_area_frac`` of the frame, from the
    # full-resolution passes. Drives the tiling trigger and is reported by the
    # benchmark as the small-object recall denominator.
    small_object_count: int = 0

    @property
    def raw_count(self) -> int:
        return len(self.proposals)

    def counts_by_source(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for proposal in self.proposals:
            counts[proposal.source_pass] = counts.get(proposal.source_pass, 0) + 1
        return dict(sorted(counts.items()))

    def counts_by_scale(self) -> dict[int, int]:
        counts: dict[int, int] = {}
        for proposal in self.proposals:
            counts[proposal.source_scale] = counts.get(proposal.source_scale, 0) + 1
        return dict(sorted(counts.items()))


def plan_tiles(
    width: int,
    height: int,
    tile_size: int,
    overlap: float,
    max_tiles: int,
) -> list[tuple[int, int, int, int]]:
    """Lay out overlapping tiles covering the image.

    Overlap matters: an object straddling a tile boundary is cut in half in both
    tiles and may be detected in neither. With 25% overlap any object smaller
    than a quarter of a tile is wholly inside at least one tile. Edge tiles are
    shifted inward so the last row and column are fully covered rather than
    running past the image bounds.

    Returns ``(x1, y1, x2, y2)`` tiles. When the layout would exceed
    ``max_tiles``, the tile size is grown until it fits — degrading toward
    fewer, larger tiles rather than silently dropping regions and losing recall
    in whichever part of the image happened to come last.
    """
    if tile_size <= 0:
        raise ValueError("tile_size must be positive")
    if not 0.0 <= overlap < 1.0:
        raise ValueError("overlap must lie in [0, 1)")
    if max_tiles <= 0:
        raise ValueError("max_tiles must be positive")

    if width <= tile_size and height <= tile_size:
        return [(0, 0, width, height)]

    effective = tile_size
    for _ in range(8):
        stride = max(1, int(round(effective * (1.0 - overlap))))
        cols = max(1, math.ceil(max(0, width - effective) / stride) + 1)
        rows = max(1, math.ceil(max(0, height - effective) / stride) + 1)
        if cols * rows <= max_tiles:
            break
        effective = int(effective * 1.4)
    else:
        logger.warning("could not fit tiling within max_tiles=%d; using a single tile", max_tiles)
        return [(0, 0, width, height)]

    stride = max(1, int(round(effective * (1.0 - overlap))))
    xs = sorted({min(x, max(0, width - effective)) for x in range(0, width, stride)})
    ys = sorted({min(y, max(0, height - effective)) for y in range(0, height, stride)})

    tiles: list[tuple[int, int, int, int]] = []
    for y in ys:
        for x in xs:
            x2 = min(width, x + effective)
            y2 = min(height, y + effective)
            if x2 > x and y2 > y:
                tiles.append((x, y, x2, y2))
    return tiles[:max_tiles]


class ProposalDetector:
    """Generates class-agnostic object proposals for one image."""

    def __init__(self, config: VisionConfig, model: "Any | None" = None) -> None:
        self.config = config
        self._model = model

    @property
    def model(self) -> Any:
        """Load weights on first use so constructing a detector is cheap."""
        if self._model is None:
            self._model = load_model(self.config.model_path)
        return self._model

    def _predict(
        self,
        image: np.ndarray,
        scale: int,
        confidence: float,
        want_masks: bool,
    ) -> tuple[list[tuple[float, float, float, float]], list[float], list["np.ndarray | None"]]:
        """One YOLO forward pass. Boxes come back in ``image`` coordinates."""
        results = self.model.predict(
            image,
            imgsz=scale,
            conf=confidence,
            iou=self.config.yolo_nms_iou,
            # Class-agnostic: suppress by geometry only, ignoring predicted
            # labels, since the labels are discarded anyway.
            agnostic_nms=True,
            verbose=False,
        )
        if not results:
            return [], [], []

        result = results[0]
        if result.boxes is None or len(result.boxes) == 0:
            return [], [], []

        boxes_xyxy = result.boxes.xyxy.cpu().numpy()
        scores = result.boxes.conf.cpu().numpy()

        height, width = image.shape[:2]
        masks: list["np.ndarray | None"] = [None] * len(boxes_xyxy)
        if want_masks and getattr(result, "masks", None) is not None and result.masks.data is not None:
            mask_data = result.masks.data.cpu().numpy()
            for index in range(min(len(masks), len(mask_data))):
                masks[index] = project_mask(
                    mask_data[index],
                    width,
                    height,
                    threshold=self.config.mask_binarize_threshold,
                )

        boxes = [(float(b[0]), float(b[1]), float(b[2]), float(b[3])) for b in boxes_xyxy]
        return boxes, [float(s) for s in scores], masks

    def _run_pass(
        self,
        image: np.ndarray,
        scale: int,
        confidence: float,
        source_pass: str,
        name: str,
        want_masks: bool,
    ) -> tuple[list[Proposal], DetectionPass]:
        """Run one full-frame pass and wrap the output as proposals."""
        import time

        started = time.perf_counter()
        boxes, scores, masks = self._predict(image, scale, confidence, want_masks)
        elapsed = time.perf_counter() - started

        proposals = [
            Proposal(
                bbox=box,
                confidence=score,
                source_pass=source_pass,
                source_scale=scale,
                mask=mask,
            )
            for box, score, mask in zip(boxes, scores, masks)
        ]
        proposals = filter_small(proposals, self.config.min_box_area)

        # Per-pass cap. A 0.005 threshold on a cluttered image can return
        # hundreds of boxes from a single pass; without this the multi-scale
        # total would grow past what fusion can process in a request budget.
        if len(proposals) > self.config.max_proposals_per_pass:
            proposals.sort(key=lambda p: p.confidence, reverse=True)
            logger.debug(
                "pass %s produced %d proposals; capping at %d",
                name,
                len(proposals),
                self.config.max_proposals_per_pass,
            )
            proposals = proposals[: self.config.max_proposals_per_pass]

        return proposals, DetectionPass(
            name=name,
            source_pass=source_pass,
            scale=scale,
            confidence=confidence,
            proposal_count=len(proposals),
            duration_s=elapsed,
        )

    def _run_tiled_pass(
        self,
        image: np.ndarray,
        scale: int,
        confidence: float,
        want_masks: bool,
    ) -> tuple[list[Proposal], DetectionPass]:
        """Detect inside overlapping tiles, projecting results back to global coordinates.

        A tile is a genuine crop, so an object occupying 40px of a 4000px-wide
        photo occupies 40px of a 768px tile — a 10x effective magnification
        versus the full-frame pass. That is the mechanism by which tiling
        improves small-object recall.
        """
        import time

        height, width = image.shape[:2]
        tiles = plan_tiles(
            width,
            height,
            self.config.tile_size,
            self.config.tile_overlap,
            self.config.max_tiles,
        )

        started = time.perf_counter()
        proposals: list[Proposal] = []
        for x1, y1, x2, y2 in tiles:
            tile = image[y1:y2, x1:x2]
            if tile.size == 0:
                continue
            boxes, scores, masks = self._predict(tile, scale, confidence, want_masks)
            for box, score, mask in zip(boxes, scores, masks):
                # Translate the box from tile-local into full-image coordinates.
                global_box = (box[0] + x1, box[1] + y1, box[2] + x1, box[3] + y1)

                global_mask: "np.ndarray | None" = None
                if mask is not None:
                    # The tile mask is already tile-sized; paste it into a
                    # full-frame canvas at the tile origin so mask IoU against
                    # full-frame proposals is a direct array comparison.
                    global_mask = np.zeros((height, width), dtype=np.uint8)
                    tile_h, tile_w = mask.shape[:2]
                    paste_h = min(tile_h, y2 - y1)
                    paste_w = min(tile_w, x2 - x1)
                    global_mask[y1 : y1 + paste_h, x1 : x1 + paste_w] = mask[:paste_h, :paste_w]

                proposals.append(
                    Proposal(
                        bbox=global_box,
                        confidence=score,
                        source_pass=SOURCE_TILE,
                        source_scale=scale,
                        mask=global_mask,
                        metadata={"tile": (x1, y1, x2, y2)},
                    )
                )
        elapsed = time.perf_counter() - started

        proposals = filter_small(proposals, self.config.min_box_area)
        if len(proposals) > self.config.max_proposals_per_pass:
            proposals.sort(key=lambda p: p.confidence, reverse=True)
            proposals = proposals[: self.config.max_proposals_per_pass]

        logger.debug("tiled pass: %d tiles -> %d proposals", len(tiles), len(proposals))
        return proposals, DetectionPass(
            name=f"tiled@{scale}",
            source_pass=SOURCE_TILE,
            scale=scale,
            confidence=confidence,
            proposal_count=len(proposals),
            duration_s=elapsed,
            tile_count=len(tiles),
        )

    def detect(self, image: np.ndarray) -> DetectionResult:
        """Generate proposals for one BGR image.

        Pass schedule:

        1. Every configured scale at ``yolo_confidence``.
        2. The smallest scale at ``yolo_confidence_secondary`` — a cheaper way
           to recover weak detections than repeating every scale, since the
           lower threshold rather than the resolution is what surfaces them.
        3. One pass over an enhanced variant, only if the quality gate produced
           one.
        4. A tiled pass, if mode or the size/density trigger calls for it.

        All returned boxes and masks are in original-image coordinates.
        """
        if image is None or image.size == 0:
            raise ValueError("cannot run detection on an empty image")

        config = self.config
        height, width = image.shape[:2]
        want_masks = config.uses_masks

        images, quality = preprocessing.prepare_passes(image, config)
        original = images[0]
        enhanced = images[1] if len(images) > 1 else None

        proposals: list[Proposal] = []
        passes: list[DetectionPass] = []

        for scale in config.scales:
            found, record = self._run_pass(
                original, scale, config.yolo_confidence, SOURCE_FULL_FRAME, f"full@{scale}", want_masks
            )
            proposals.extend(found)
            passes.append(record)

        if config.enable_secondary_pass:
            scale = min(config.scales)
            found, record = self._run_pass(
                original,
                scale,
                config.yolo_confidence_secondary,
                SOURCE_SECONDARY,
                f"secondary@{scale}",
                want_masks,
            )
            proposals.extend(found)
            passes.append(record)

        if enhanced is not None:
            scale = min(config.scales)
            found, record = self._run_pass(
                enhanced, scale, config.yolo_confidence, SOURCE_ENHANCED, f"enhanced@{scale}", want_masks
            )
            proposals.extend(found)
            passes.append(record)

        # Density trigger: count how many proposals so far are *small* relative
        # to the frame. That is the property tiling actually addresses. Using
        # the raw total instead would trigger on nearly every image, because
        # the 0.005 secondary pass always returns a lot of boxes.
        megapixels = (width * height) / 1e6
        small_area_limit = width * height * config.small_object_area_frac
        small_object_count = sum(1 for p in proposals if p.area < small_area_limit)

        tiled = config.should_tile(megapixels, small_object_count)
        if tiled:
            scale = min(config.scales)
            found, record = self._run_tiled_pass(original, scale, config.yolo_confidence, want_masks)
            proposals.extend(found)
            passes.append(record)

        assign_ids(proposals)
        if want_masks:
            segmentation.attach_mask_statistics(proposals, config)

        logger.info(
            "detected %d raw proposals across %d passes (%d small, tiled=%s)",
            len(proposals),
            len(passes),
            small_object_count,
            tiled,
        )
        return DetectionResult(
            proposals=proposals,
            passes=passes,
            quality=quality,
            tiled=tiled,
            small_object_count=small_object_count,
        )


__all__ = [
    "DetectionPass",
    "DetectionResult",
    "ProposalDetector",
    "load_model",
    "plan_tiles",
    "project_mask",
]
