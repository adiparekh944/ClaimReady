"""Central configuration for the ClaimReady perception pipeline.

Every threshold used by the vision package lives here. Nothing in ``vision/``
should contain a bare magic number; if a value needs tuning it belongs on
:class:`VisionConfig`.

Three presets cover the latency/recall spectrum:

``FAST``
    Single scale, geometric dedup only. Preserves the latency profile of the
    original pipeline and stays available as an escape hatch.
``BALANCED``
    Two scales, segmentation masks, CLIP embedding dedup. Intended default for
    interactive requests.
``ACCURATE``
    Three scales plus a tiled pass for small objects. Maximum recall, meant for
    batch or offline use.

Any field can be overridden from the environment with a ``CR_VISION_`` prefix,
so production can be retuned without a redeploy of new code.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field, fields, replace
from enum import Enum
from typing import Any, Sequence

logger = logging.getLogger(__name__)

ENV_PREFIX = "CR_VISION_"


class PipelineMode(str, Enum):
    """Named latency/recall operating points."""

    FAST = "FAST"
    BALANCED = "BALANCED"
    ACCURATE = "ACCURATE"

    @classmethod
    def parse(cls, value: "str | PipelineMode") -> "PipelineMode":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().upper())
        except ValueError as exc:
            valid = ", ".join(m.value for m in cls)
            raise ValueError(f"Unknown pipeline mode {value!r}; expected one of {valid}") from exc


class EmbeddingCropMode(str, Enum):
    """How a crop is presented to the visual encoder.

    ``BBOX``
        Plain bounding-box crop, background pixels included.
    ``MASKED``
        Background suppressed using the segmentation mask, so the embedding
        describes the object rather than its surroundings.
    ``BOTH``
        Embed both variants and average the two L2-normalized vectors, then
        renormalize. Averaging unit vectors keeps cosine similarity meaningful
        and weights the two views equally, which concatenation would not do
        without also doubling dimensionality.
    """

    BBOX = "bbox"
    MASKED = "masked"
    BOTH = "both"

    @classmethod
    def parse(cls, value: "str | EmbeddingCropMode") -> "EmbeddingCropMode":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower())
        except ValueError as exc:
            valid = ", ".join(m.value for m in cls)
            raise ValueError(f"Unknown embedding crop mode {value!r}; expected one of {valid}") from exc


def _coerce(raw: str, template: Any) -> Any:
    """Convert an environment string to the type of an existing default."""
    if isinstance(template, bool):
        lowered = raw.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
        raise ValueError(f"Cannot read {raw!r} as a boolean")
    if isinstance(template, PipelineMode):
        return PipelineMode.parse(raw)
    if isinstance(template, EmbeddingCropMode):
        return EmbeddingCropMode.parse(raw)
    if isinstance(template, tuple):
        parts = [p for p in raw.replace(",", " ").split() if p]
        return tuple(int(p) for p in parts)
    if isinstance(template, int) and not isinstance(template, bool):
        return int(raw)
    if isinstance(template, float):
        return float(raw)
    return raw


@dataclass(frozen=True)
class VisionConfig:
    """Immutable snapshot of every perception threshold.

    Frozen so a pipeline cannot be reconfigured mid-request. Use
    :meth:`with_overrides` to derive a variant, which is how the benchmark
    builds its ablation configurations.
    """

    mode: PipelineMode = PipelineMode.BALANCED

    # --- detector ---------------------------------------------------------
    model_path: str = "yolo11x-seg.pt"
    # Deliberately far below a typical 0.25. YOLO is used as a class-agnostic
    # objectness proposer and a downstream multimodal model rejects false
    # positives, so recall matters more than proposal precision here.
    yolo_confidence: float = 0.01
    # Second, even lower pass to recover objects the first pass missed.
    yolo_confidence_secondary: float = 0.005
    enable_secondary_pass: bool = True
    # Kept high so YOLO's internal NMS does not suppress overlapping proposals
    # before our own fusion stage gets to see them.
    yolo_nms_iou: float = 0.7
    scales: tuple[int, ...] = (640, 960)
    # Hard ceiling applied before any expensive per-crop work. Very low
    # confidence thresholds can produce thousands of boxes on cluttered images.
    max_proposals: int = 300
    max_proposals_per_pass: int = 400
    min_box_area: int = 64

    # --- segmentation -----------------------------------------------------
    enable_segmentation: bool = True
    mask_binarize_threshold: float = 0.5
    mask_iou_threshold: float = 0.55
    # A mask filling almost none of its box usually means a bad mask, not a
    # thin object; below this the mask is ignored rather than trusted.
    min_mask_occupancy: float = 0.05

    # --- fusion -----------------------------------------------------------
    fusion_iou_threshold: float = 0.55
    containment_threshold: float = 0.80
    # Fragments that barely touch are only unioned when appearance agrees.
    fragment_iou_threshold: float = 0.10
    enable_fragment_union: bool = True

    # --- embeddings -------------------------------------------------------
    enable_embeddings: bool = True
    embedding_model: str = "ViT-B-32"
    embedding_pretrained: str = "laion2b_s34b_b79k"
    embedding_batch_size: int = 32
    embedding_crop_mode: EmbeddingCropMode = EmbeddingCropMode.BBOX
    # Cosine similarity above which two crops are considered the same object,
    # given at least moderate geometric overlap.
    embedding_similarity_threshold: float = 0.92
    # Higher bar used when geometry is weak (containment without much IoU).
    embedding_strict_threshold: float = 0.95
    embedding_device: str = "auto"

    # --- deduplication ----------------------------------------------------
    iou_threshold: float = 0.60
    moderate_iou_threshold: float = 0.30
    # Scale-free centre separation, as a fraction of the mean box diagonal.
    # Note the fragment IoU gate already bounds this: two equal boxes at
    # IoU 0.10 sit at a normalized centre distance of roughly 0.37 (tall boxes)
    # to 0.73 (wide boxes). So this threshold is not the primary guard for
    # side-by-side fragments; its job is rejecting strongly asymmetric pairs,
    # where a small box clips the corner of a large one and the two centres are
    # far apart relative to their sizes. Set below ~0.35 it would disable the
    # fragment clause entirely.
    center_distance_threshold: float = 0.70
    size_ratio_threshold: float = 0.45

    # --- preprocessing ----------------------------------------------------
    enable_preprocessing: bool = True
    # Quality gates. An enhanced pass is only generated when the image
    # actually looks poor, so well-exposed photos cost nothing extra.
    dark_brightness_threshold: float = 70.0
    bright_brightness_threshold: float = 185.0
    low_contrast_threshold: float = 40.0
    blur_variance_threshold: float = 100.0
    clahe_clip_limit: float = 2.0
    clahe_grid_size: int = 8
    # Convention (see preprocessing.apply_gamma): gamma > 1 brightens,
    # gamma < 1 darkens. So an underexposed frame needs a value above 1.
    gamma_dark: float = 1.5
    gamma_bright: float = 0.7
    sharpen_amount: float = 0.6

    # --- tiling -----------------------------------------------------------
    enable_tiling: bool = False
    tile_size: int = 768
    tile_overlap: float = 0.25
    # Auto-triggers so BALANCED can still tile a genuinely huge or cluttered
    # image without paying for it on ordinary photos.
    tiling_megapixel_threshold: float = 8.0
    # A proposal counts as "small" below this fraction of the frame area.
    # 1% of the frame is roughly a 90x100 px region in a 1MP photo: the scale
    # at which full-frame downsampling to 640px starts losing detail.
    small_object_area_frac: float = 0.01
    # Number of small proposals above which the scene is treated as cluttered.
    # Deliberately keyed to small-object count rather than total proposal
    # count: at a 0.005 confidence threshold the raw total is high on every
    # image and says nothing about whether tiling would help.
    tiling_density_threshold: int = 25
    max_tiles: int = 24

    # --- video tracking / re-identification -------------------------------
    tracker_confidence: float = 0.55
    tracker_iou: float = 0.45
    min_frames_to_confirm: int = 3
    max_missing_frames: int = 5
    reid_similarity_threshold: float = 0.90
    reid_max_gallery_size: int = 512
    enable_reid: bool = True
    excluded_classes: tuple[str, ...] = ("person",)
    # Crop-quality weights. Sum need not be 1; scores are relative.
    quality_weight_confidence: float = 0.40
    quality_weight_area: float = 0.25
    quality_weight_sharpness: float = 0.25
    quality_weight_centrality: float = 0.10

    # --- diagnostics ------------------------------------------------------
    collect_timings: bool = True
    debug_visualization: bool = False
    debug_output_dir: str = "artifacts/cv_debug"
    random_seed: int = 0

    def __post_init__(self) -> None:
        if not self.scales:
            raise ValueError("scales must contain at least one inference resolution")
        if any(s <= 0 for s in self.scales):
            raise ValueError(f"scales must be positive, got {self.scales}")
        if self.max_proposals <= 0:
            raise ValueError("max_proposals must be positive")
        if not 0.0 < self.tile_overlap < 1.0:
            raise ValueError("tile_overlap must lie in (0, 1)")
        for name in (
            "yolo_confidence",
            "yolo_confidence_secondary",
            "iou_threshold",
            "fusion_iou_threshold",
            "containment_threshold",
            "embedding_similarity_threshold",
            "mask_iou_threshold",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must lie in [0, 1], got {value}")

    # -- derived helpers ---------------------------------------------------

    @property
    def uses_masks(self) -> bool:
        return self.enable_segmentation and "seg" in self.model_path

    def should_tile(self, megapixels: float, small_object_count: int) -> bool:
        """Decide whether a tiled pass is worth its cost for this image.

        Tiling cost grows with tile count, so it runs only when explicitly
        enabled by the mode, or when a measured property of *this* image
        suggests small objects are being lost to full-frame downsampling:

        - the image is large enough that a 640px pass discards most detail, or
        - the detector already found many small objects, implying clutter at a
          scale where more are likely hiding.

        Args:
            megapixels: Original image size.
            small_object_count: Proposals below ``small_object_area_frac`` of
                the frame area, from the full-resolution passes.
        """
        if self.enable_tiling:
            return True
        if megapixels >= self.tiling_megapixel_threshold:
            return True
        return small_object_count >= self.tiling_density_threshold

    def with_overrides(self, **overrides: Any) -> "VisionConfig":
        """Return a copy with specific fields replaced."""
        if "mode" in overrides:
            overrides["mode"] = PipelineMode.parse(overrides["mode"])
        if "embedding_crop_mode" in overrides:
            overrides["embedding_crop_mode"] = EmbeddingCropMode.parse(overrides["embedding_crop_mode"])
        if "scales" in overrides and overrides["scales"] is not None:
            overrides["scales"] = tuple(int(s) for s in overrides["scales"])
        return replace(self, **overrides)

    def summary(self) -> dict[str, Any]:
        """Flat JSON-serializable view, used by benchmark result files."""
        out: dict[str, Any] = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if isinstance(value, Enum):
                out[f.name] = value.value
            elif isinstance(value, tuple):
                out[f.name] = list(value)
            else:
                out[f.name] = value
        return out


# Preset deltas relative to the dataclass defaults. Keeping these as plain
# dictionaries makes the difference between modes readable at a glance.
_MODE_PRESETS: dict[PipelineMode, dict[str, Any]] = {
    PipelineMode.FAST: {
        "scales": (640,),
        "enable_secondary_pass": True,
        "enable_segmentation": False,
        "enable_embeddings": False,
        "enable_preprocessing": False,
        "enable_tiling": False,
        "enable_fragment_union": False,
        "max_proposals": 200,
        # No appearance model in FAST, so auto-tiling would only add latency.
        "tiling_megapixel_threshold": float("inf"),
        "tiling_density_threshold": 1_000_000,
    },
    PipelineMode.BALANCED: {
        "scales": (640, 960),
        "enable_segmentation": True,
        "enable_embeddings": True,
        "enable_preprocessing": True,
        "enable_tiling": False,
        "enable_fragment_union": True,
        "max_proposals": 300,
    },
    PipelineMode.ACCURATE: {
        "scales": (640, 960, 1280),
        "enable_segmentation": True,
        "enable_embeddings": True,
        "enable_preprocessing": True,
        "enable_tiling": True,
        "enable_fragment_union": True,
        "max_proposals": 500,
        # BOTH rather than MASKED. Measured on 34 frames with yolo11x-seg
        # (benchmarks configs E/F/G, see docs/benchmark_results.md):
        # masked-only crops produced the *fewest* appearance-driven merges
        # (6, versus 11 for bbox and 14 for both) and were the slowest.
        # Zeroing the background appears to push crops away from CLIP's
        # training distribution, making genuinely similar objects score lower.
        # Averaging the two views cost no more than bbox alone.
        "embedding_crop_mode": EmbeddingCropMode.BOTH,
    },
}


def config_for_mode(mode: "str | PipelineMode", **overrides: Any) -> VisionConfig:
    """Build a config from a named preset, then apply explicit overrides."""
    parsed = PipelineMode.parse(mode)
    preset = dict(_MODE_PRESETS[parsed])
    preset["mode"] = parsed
    preset.update(overrides)
    return VisionConfig(**preset)


def _env_overrides(env: "dict[str, str] | None" = None) -> dict[str, Any]:
    """Collect ``CR_VISION_*`` variables that map onto config fields."""
    source = os.environ if env is None else env
    defaults = VisionConfig()
    known = {f.name for f in fields(defaults)}
    found: dict[str, Any] = {}
    for key, raw in source.items():
        if not key.startswith(ENV_PREFIX):
            continue
        name = key[len(ENV_PREFIX) :].lower()
        if name not in known:
            logger.warning("Ignoring unknown vision env override %s", key)
            continue
        try:
            found[name] = _coerce(raw, getattr(defaults, name))
        except (ValueError, TypeError) as exc:
            logger.warning("Ignoring bad value for %s (%r): %s", key, raw, exc)
    return found


def load_config(
    mode: "str | PipelineMode | None" = None,
    env: "dict[str, str] | None" = None,
    **overrides: Any,
) -> VisionConfig:
    """Resolve the effective config.

    Precedence, lowest to highest: mode preset, ``CR_VISION_*`` environment
    variables, then explicit keyword overrides. Environment sits below explicit
    arguments so tests and benchmarks stay deterministic, but above presets so
    production can retune a deployed build.
    """
    source = os.environ if env is None else env
    env_values = _env_overrides(source)

    if mode is None:
        mode = env_values.pop("mode", None) or source.get(f"{ENV_PREFIX}MODE") or PipelineMode.BALANCED
    else:
        env_values.pop("mode", None)

    merged: dict[str, Any] = {**env_values, **overrides}
    return config_for_mode(mode, **merged)


__all__ = [
    "EmbeddingCropMode",
    "PipelineMode",
    "VisionConfig",
    "config_for_mode",
    "load_config",
]
