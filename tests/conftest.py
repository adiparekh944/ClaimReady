"""Shared pytest fixtures for the perception test suite.

Design constraint: the tests must not download neural network weights. The
whole suite therefore runs against synthetic arrays and a fake encoder, which
keeps it fast and runnable in CI. The two places where real weights would be
needed — YOLO inference and CLIP embedding — are covered by injecting stubs
through the constructor parameters the production classes already accept
(``ProposalDetector(config, model=...)`` and
``VisionPipeline(config, model=..., embedder=...)``), so the seams being tested
are the real ones rather than test-only hooks.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest

# The vision package lives under backend/ so that it falls inside the Docker
# build context; see docs/deployment.md.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "backend"))
sys.path.insert(0, _REPO_ROOT)

from vision.config import PipelineMode, VisionConfig, config_for_mode  # noqa: E402


@pytest.fixture
def balanced_config() -> VisionConfig:
    """BALANCED preset with a lightweight model path (never actually loaded)."""
    return config_for_mode(PipelineMode.BALANCED, model_path="test-model.pt")


@pytest.fixture
def fast_config() -> VisionConfig:
    return config_for_mode(PipelineMode.FAST, model_path="test-model.pt")


@pytest.fixture
def rng() -> np.random.Generator:
    """Seeded generator, so a failure is reproducible."""
    return np.random.default_rng(1234)


@pytest.fixture
def solid_image() -> np.ndarray:
    """A mid-grey 200x300 BGR image with one bright rectangle."""
    image = np.full((200, 300, 3), 110, dtype=np.uint8)
    image[40:120, 60:180] = 220
    return image


class FakeEmbedder:
    """Stand-in for :class:`vision.embeddings.EmbeddingExtractor`.

    Produces a deterministic unit vector from each crop's mean colour, so two
    similarly coloured crops embed close together and differently coloured ones
    do not. That is enough structure to exercise the appearance-gated
    deduplication clauses without loading CLIP.
    """

    def __init__(self, dim: int = 8) -> None:
        self.dim = dim
        self.call_count = 0
        self.crops_seen = 0

    def _vector(self, crop: np.ndarray) -> np.ndarray:
        vector = np.zeros(self.dim, dtype=np.float32)
        if crop is None or crop.size == 0:
            return vector
        means = crop.reshape(-1, crop.shape[-1]).mean(axis=0) if crop.ndim == 3 else np.array([crop.mean()])
        for index, value in enumerate(means[: self.dim]):
            vector[index] = float(value) / 255.0
        norm = float(np.linalg.norm(vector))
        return vector / norm if norm > 0 else vector

    def embed_crops(self, crops) -> np.ndarray:
        self.call_count += 1
        self.crops_seen += len(crops)
        if not crops:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.stack([self._vector(c) for c in crops])

    def embed_dual(self, bbox_crops, masked_crops) -> np.ndarray:
        a = self.embed_crops(bbox_crops)
        b = self.embed_crops(masked_crops)
        combined = (a + b) / 2.0
        norms = np.linalg.norm(combined, axis=-1, keepdims=True)
        return combined / np.where(norms > 0, norms, 1.0)


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()


class FakeBox:
    """Minimal stand-in for an Ultralytics ``Boxes`` object."""

    def __init__(self, xyxy: np.ndarray, conf: np.ndarray, cls: "np.ndarray | None" = None,
                 ids: "np.ndarray | None" = None) -> None:
        self.xyxy = _Tensorish(xyxy)
        self.conf = _Tensorish(conf)
        self.cls = _Tensorish(cls if cls is not None else np.zeros(len(xyxy)))
        self.id = _Tensorish(ids) if ids is not None else None

    def __len__(self) -> int:
        return len(self.xyxy.array)


class _Tensorish:
    """Wraps an ndarray with the ``.cpu().numpy()`` chain Ultralytics returns."""

    def __init__(self, array: np.ndarray) -> None:
        self.array = np.asarray(array)

    def cpu(self) -> "_Tensorish":
        return self

    def numpy(self) -> np.ndarray:
        return self.array

    def __getitem__(self, item):
        return _Tensorish(self.array[item])

    def __len__(self) -> int:
        return len(self.array)

    def astype(self, dtype):
        return self.array.astype(dtype)


class FakeMasks:
    def __init__(self, data: np.ndarray) -> None:
        self.data = _Tensorish(data)


class FakeResult:
    def __init__(self, boxes=None, masks=None, names=None) -> None:
        self.boxes = boxes
        self.masks = masks
        self.names = names or {0: "object"}


class FakeYOLO:
    """Scripted detector.

    Returns a fixed set of boxes for every call, recording the ``imgsz`` each
    time so multi-scale scheduling can be asserted without real inference.
    """

    def __init__(self, boxes, confidences, masks=None, names=None) -> None:
        self.boxes = np.asarray(boxes, dtype=np.float32)
        self.confidences = np.asarray(confidences, dtype=np.float32)
        self.masks = masks
        self.names = names or {0: "object"}
        self.calls: list[dict] = []

    def predict(self, image, imgsz=640, conf=0.25, iou=0.7, agnostic_nms=True, verbose=False, **kwargs):
        self.calls.append(
            {
                "imgsz": imgsz,
                "conf": conf,
                "iou": iou,
                "agnostic_nms": agnostic_nms,
                "shape": tuple(image.shape[:2]),
            }
        )
        keep = self.confidences >= conf
        boxes = self.boxes[keep]
        confidences = self.confidences[keep]
        if len(boxes) == 0:
            return [FakeResult(boxes=None, names=self.names)]

        masks = None
        if self.masks is not None:
            masks = FakeMasks(np.asarray(self.masks)[keep])
        return [
            FakeResult(
                boxes=FakeBox(boxes, confidences, np.zeros(len(boxes))),
                masks=masks,
                names=self.names,
            )
        ]

    def track(self, image, persist=True, conf=0.25, iou=0.45, imgsz=640, verbose=False, **kwargs):
        keep = self.confidences >= conf
        boxes = self.boxes[keep]
        confidences = self.confidences[keep]
        if len(boxes) == 0:
            return [FakeResult(boxes=None, names=self.names)]
        ids = np.arange(1, len(boxes) + 1)
        return [
            FakeResult(
                boxes=FakeBox(boxes, confidences, np.zeros(len(boxes)), ids),
                names=self.names,
            )
        ]


@pytest.fixture
def fake_yolo() -> FakeYOLO:
    """Two overlapping boxes plus one isolated box."""
    return FakeYOLO(
        boxes=[[10, 10, 110, 110], [14, 12, 116, 114], [200, 150, 260, 190]],
        confidences=[0.9, 0.6, 0.3],
    )
