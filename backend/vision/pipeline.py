"""The end-to-end image perception pipeline.

Stage order and why
-------------------
::

    image
      │
      ├─ 1. quality assessment ───────► optional enhanced variant
      │
      ├─ 2. detection                   multi-scale + secondary + enhanced
      │                                 + optional tiled pass
      │                                 (all output in original coordinates)
      │
      ├─ 3. coarse IoU pre-fusion       collapse near-identical boxes with WBF
      │
      ├─ 4. proposal cap                keep top-N by confidence
      │
      ├─ 5. embeddings                  batched CLIP over surviving crops
      │
      ├─ 6. deduplication               geometry + mask + appearance, union-find
      │
      └─ 7. crop extraction             final crops for the multimodal stage

Steps 3 and 4 come before step 5 deliberately. Embedding cost is linear in
proposal count, so collapsing unambiguous duplicates first means the expensive
stage sees distinct candidates. Capping *before* pre-fusion would be worse: a
confidence-ranked cut on raw detector output happily keeps three copies of one
object while discarding a distinct one, since duplicates of a salient object all
score highly.

Step 6 needs the embeddings from step 5, which is why deduplication cannot
simply be merged into step 3.

Modes
-----
``FAST`` skips steps 1, 5 and the tiled pass, and step 6 degrades to
geometry-only. This preserves a low-latency path with behaviour close to the
original pipeline. ``BALANCED`` and ``ACCURATE`` run everything, differing in
scale count and whether tiling is forced.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator, Sequence

import numpy as np

from . import fusion, segmentation
from .config import EmbeddingCropMode, PipelineMode, VisionConfig, load_config
from .deduplication import Deduplicator, DeduplicationResult
from .detector import DetectionResult, ProposalDetector
from .embeddings import EmbeddingExtractor, cosine_similarity_matrix
from .preprocessing import ImageQuality
from .proposals import Proposal, cap_proposals

logger = logging.getLogger(__name__)


class StageTimer:
    """Accumulates per-stage wall-clock timings.

    Wall clock rather than CPU time, because the numbers exist to answer "is
    this usable in a web request", and GPU work plus model loading are exactly
    the parts CPU time would under-report.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.timings: dict[str, float] = {}

    @contextmanager
    def measure(self, stage: str) -> Iterator[None]:
        if not self.enabled:
            yield
            return
        started = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - started
            self.timings[stage] = self.timings.get(stage, 0.0) + elapsed

    def record(self, stage: str, seconds: float) -> None:
        if self.enabled:
            self.timings[stage] = self.timings.get(stage, 0.0) + seconds

    @property
    def total(self) -> float:
        return float(sum(self.timings.values()))

    def to_dict(self) -> dict[str, float]:
        out = {k: round(v, 4) for k, v in self.timings.items()}
        out["total"] = round(self.total, 4)
        return out


@dataclass
class PipelineResult:
    """Everything one image produced, including the audit trail."""

    proposals: list[Proposal]
    crops: list[np.ndarray] = field(default_factory=list)
    mode: PipelineMode = PipelineMode.BALANCED
    image_shape: tuple[int, int] = (0, 0)
    quality: "ImageQuality | None" = None
    detection: "DetectionResult | None" = None
    dedup: "DeduplicationResult | None" = None
    timings: dict[str, float] = field(default_factory=dict)
    raw_count: int = 0
    prefused_count: int = 0
    capped_count: int = 0
    embedding_count: int = 0
    tiled: bool = False
    # The proposals fed into deduplication, retained only when
    # ``debug_visualization`` is set. Merge records reference these IDs, so the
    # merge-graph render needs them; the canonical proposals in ``proposals``
    # only carry the surviving anchor IDs. Kept behind the flag because each
    # proposal may hold a full-frame mask, which is roughly 0.9 MB per mask on
    # a 1280x720 frame.
    pre_dedup_proposals: list[Proposal] = field(default_factory=list)

    @property
    def final_count(self) -> int:
        return len(self.proposals)

    @property
    def duplicates_removed(self) -> int:
        """Raw proposals minus final, i.e. everything fusion and dedup collapsed."""
        return max(0, self.raw_count - self.final_count)

    @property
    def reduction_ratio(self) -> float:
        """Fraction of raw proposals eliminated. 0.0 when there were none."""
        if self.raw_count == 0:
            return 0.0
        return 1.0 - (self.final_count / self.raw_count)

    def stage_counts(self) -> dict[str, int]:
        return {
            "raw": self.raw_count,
            "after_prefusion": self.prefused_count,
            "after_cap": self.capped_count,
            "embedded": self.embedding_count,
            "final": self.final_count,
        }

    def to_dict(self, include_proposals: bool = True) -> dict[str, Any]:
        out: dict[str, Any] = {
            "mode": self.mode.value,
            "image_shape": list(self.image_shape),
            "stage_counts": self.stage_counts(),
            "duplicates_removed": self.duplicates_removed,
            "reduction_ratio": round(self.reduction_ratio, 4),
            "tiled": self.tiled,
            "timings": dict(self.timings),
        }
        if self.quality is not None:
            out["quality"] = self.quality.to_dict()
        if self.detection is not None:
            out["detection_passes"] = [p.to_dict() for p in self.detection.passes]
            out["counts_by_source"] = self.detection.counts_by_source()
            out["counts_by_scale"] = {str(k): v for k, v in self.detection.counts_by_scale().items()}
            out["small_object_count"] = self.detection.small_object_count
        if self.dedup is not None:
            out["merge_reasons"] = self.dedup.reason_counts()
        if include_proposals:
            out["proposals"] = [p.to_dict() for p in self.proposals]
        return out


class VisionPipeline:
    """Configurable perception pipeline for inventory images.

    Models are loaded lazily and cached at module level, so constructing a
    pipeline is cheap and a long-lived server shares one copy of the weights
    across requests. Construct once at startup and reuse.
    """

    def __init__(
        self,
        config: "VisionConfig | None" = None,
        model: "Any | None" = None,
        embedder: "EmbeddingExtractor | None" = None,
    ) -> None:
        self.config = config if config is not None else load_config()
        self.detector = ProposalDetector(self.config, model=model)
        self.deduplicator = Deduplicator(self.config)
        self._embedder = embedder

    @property
    def mode(self) -> PipelineMode:
        return self.config.mode

    @property
    def embedder(self) -> "EmbeddingExtractor | None":
        """The appearance encoder, or ``None`` when embeddings are disabled."""
        if not self.config.enable_embeddings:
            return None
        if self._embedder is None:
            self._embedder = EmbeddingExtractor(
                model_name=self.config.embedding_model,
                pretrained=self.config.embedding_pretrained,
                device=self.config.embedding_device,
                batch_size=self.config.embedding_batch_size,
            )
        return self._embedder

    def warmup(self) -> None:
        """Force model loading outside the request path.

        Call at server startup. Without it the first user request pays the
        weight-loading cost, which for the CLIP encoder alone was measured at
        roughly 35 s cold on this machine.
        """
        _ = self.detector.model
        embedder = self.embedder
        if embedder is not None:
            _ = embedder.dim

    def _extract_crops(
        self,
        image: np.ndarray,
        proposals: Sequence[Proposal],
        masked: bool,
    ) -> list[np.ndarray]:
        """Crop each proposal, optionally suppressing background via its mask.

        Always returns one entry per proposal — a 1x1 black pixel for
        degenerate boxes — so downstream index alignment with ``proposals`` is
        guaranteed.
        """
        crops: list[np.ndarray] = []
        for proposal in proposals:
            if masked and proposal.mask is not None and proposal.metadata.get("mask_trusted", True):
                crop = segmentation.extract_masked_crop(image, proposal.bbox, proposal.mask)
            else:
                crop = segmentation.extract_bbox_crop(image, proposal.bbox)
            if crop is None or crop.size == 0:
                crop = np.zeros((1, 1, 3), dtype=np.uint8)
            crops.append(crop)
        return crops

    def _compute_similarity(
        self,
        image: np.ndarray,
        proposals: Sequence[Proposal],
        timer: StageTimer,
    ) -> "np.ndarray | None":
        """Embed the proposals and return their cosine similarity matrix.

        Honours ``embedding_crop_mode``: plain bbox crops, background-suppressed
        masked crops, or the average of both.
        """
        embedder = self.embedder
        if embedder is None or not proposals:
            return None

        crop_mode = self.config.embedding_crop_mode
        with timer.measure("crops_for_embedding"):
            if crop_mode is EmbeddingCropMode.BBOX:
                bbox_crops = self._extract_crops(image, proposals, masked=False)
                masked_crops = None
            elif crop_mode is EmbeddingCropMode.MASKED:
                bbox_crops = self._extract_crops(image, proposals, masked=True)
                masked_crops = None
            else:
                bbox_crops = self._extract_crops(image, proposals, masked=False)
                masked_crops = self._extract_crops(image, proposals, masked=True)

        with timer.measure("embedding"):
            if masked_crops is None:
                matrix = embedder.embed_crops(bbox_crops)
            else:
                matrix = embedder.embed_dual(bbox_crops, masked_crops)

        for proposal, vector in zip(proposals, matrix):
            proposal.embedding = vector

        with timer.measure("similarity"):
            return cosine_similarity_matrix(matrix)

    def process_image(self, image: np.ndarray) -> PipelineResult:
        """Run the full pipeline on one BGR image.

        Args:
            image: OpenCV-convention BGR array.

        Returns:
            A :class:`PipelineResult` whose ``proposals`` are deduplicated and
            in original-image coordinates, ``crops`` are aligned with them, and
            ``timings`` gives the per-stage breakdown.
        """
        if image is None or getattr(image, "size", 0) == 0:
            raise ValueError("cannot process an empty image")

        config = self.config
        timer = StageTimer(enabled=config.collect_timings)
        height, width = image.shape[:2]

        # --- 1 & 2: quality assessment and detection -----------------------
        with timer.measure("detection"):
            detection = self.detector.detect(image)
        raw_count = detection.raw_count

        # --- 3: coarse IoU pre-fusion --------------------------------------
        with timer.measure("prefusion"):
            prefused = fusion.fuse_by_iou(detection.proposals, config.fusion_iou_threshold)
        prefused_count = len(prefused)

        # --- 4: proposal cap, before anything per-crop and expensive -------
        with timer.measure("cap"):
            capped = cap_proposals(prefused, config.max_proposals)
        if len(capped) < prefused_count:
            logger.info("capped proposals from %d to %d", prefused_count, len(capped))

        # --- 5: appearance embeddings --------------------------------------
        similarity = self._compute_similarity(image, capped, timer)
        embedding_count = len(capped) if similarity is not None else 0

        # --- 6: deduplication ----------------------------------------------
        with timer.measure("deduplication"):
            dedup = self.deduplicator.deduplicate(capped, similarity)

        # --- 7: final crops for the multimodal stage -----------------------
        with timer.measure("final_crops"):
            crops = self._extract_crops(image, dedup.proposals, masked=False)

        result = PipelineResult(
            proposals=dedup.proposals,
            crops=crops,
            mode=config.mode,
            image_shape=(height, width),
            quality=detection.quality,
            detection=detection,
            dedup=dedup,
            timings=timer.to_dict(),
            raw_count=raw_count,
            prefused_count=prefused_count,
            capped_count=len(capped),
            embedding_count=embedding_count,
            tiled=detection.tiled,
            pre_dedup_proposals=list(capped) if config.debug_visualization else [],
        )

        logger.info(
            "%s pipeline: %d raw -> %d prefused -> %d final in %.2fs",
            config.mode.value,
            raw_count,
            prefused_count,
            result.final_count,
            timer.total,
        )
        return result

    def process_baseline(self, image: np.ndarray) -> PipelineResult:
        """Reproduce the original pipeline, for benchmarking against.

        Two low-confidence full-frame passes at a single scale, then greedy
        IoU suppression — no fusion, no masks, no appearance. This is
        configuration ``A`` in the ablation study. It exists so the comparison
        has a real control measured on the same machine and images, rather than
        an assumed one.
        """
        if image is None or getattr(image, "size", 0) == 0:
            raise ValueError("cannot process an empty image")

        timer = StageTimer(enabled=self.config.collect_timings)
        height, width = image.shape[:2]

        baseline_config = self.config.with_overrides(
            scales=(min(self.config.scales),),
            enable_segmentation=False,
            enable_embeddings=False,
            enable_preprocessing=False,
            enable_tiling=False,
            enable_fragment_union=False,
            tiling_megapixel_threshold=float("inf"),
            tiling_density_threshold=1_000_000,
        )
        detector = ProposalDetector(baseline_config, model=self.detector._model)

        with timer.measure("detection"):
            detection = detector.detect(image)

        with timer.measure("deduplication"):
            kept = fusion.greedy_iou_suppression(detection.proposals, baseline_config.iou_threshold)

        with timer.measure("final_crops"):
            crops = self._extract_crops(image, kept, masked=False)

        return PipelineResult(
            proposals=kept,
            crops=crops,
            mode=baseline_config.mode,
            image_shape=(height, width),
            quality=detection.quality,
            detection=detection,
            dedup=None,
            timings=timer.to_dict(),
            raw_count=detection.raw_count,
            prefused_count=detection.raw_count,
            capped_count=detection.raw_count,
            embedding_count=0,
            tiled=False,
        )


__all__ = ["PipelineResult", "StageTimer", "VisionPipeline"]
