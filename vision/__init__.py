"""ClaimReady perception package.

Class-agnostic object proposal generation, appearance-based deduplication and
video re-identification for the home-inventory pipeline.

Submodules are imported lazily so that ``import vision`` stays cheap and does
not pull in torch or ultralytics. Tests that only exercise geometry or config
should not pay for a deep-learning import.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from .config import EmbeddingCropMode, PipelineMode, VisionConfig, config_for_mode, load_config
from .geometry import containment, intersection_over_smaller, iou
from .proposals import Proposal, UnionFind

__version__ = "0.1.0"

# Attribute name -> submodule that defines it. Resolved on first access.
_LAZY: dict[str, str] = {
    "VisionPipeline": "vision.pipeline",
    "PipelineResult": "vision.pipeline",
    "ProposalDetector": "vision.detector",
    "EmbeddingExtractor": "vision.embeddings",
    "Deduplicator": "vision.deduplication",
    "InventoryMemoryBank": "vision.association",
    "VideoInventoryTracker": "vision.tracking",
}

if TYPE_CHECKING:  # pragma: no cover - import-time typing only
    from .association import InventoryMemoryBank
    from .deduplication import Deduplicator
    from .detector import ProposalDetector
    from .embeddings import EmbeddingExtractor
    from .pipeline import PipelineResult, VisionPipeline
    from .tracking import VideoInventoryTracker


def __getattr__(name: str) -> Any:
    module_path = _LAZY.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(module_path)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY))


__all__ = [
    "Deduplicator",
    "EmbeddingCropMode",
    "EmbeddingExtractor",
    "InventoryMemoryBank",
    "PipelineMode",
    "PipelineResult",
    "Proposal",
    "ProposalDetector",
    "UnionFind",
    "VideoInventoryTracker",
    "VisionConfig",
    "VisionPipeline",
    "config_for_mode",
    "containment",
    "intersection_over_smaller",
    "iou",
    "load_config",
]
