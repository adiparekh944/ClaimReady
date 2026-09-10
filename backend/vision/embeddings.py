"""Batched visual embeddings for appearance-based reasoning.

Model choice
------------
OpenCLIP ``ViT-B-32`` with the ``laion2b_s34b_b79k`` weights. Reasons:

- ``open-clip-torch`` is already in ``backend/requirements.txt``, so this adds
  no new dependency. SigLIP would perform slightly better on fine-grained
  retrieval but would pull in ``transformers``, which is a much heavier install
  for a container that already carries torch and ultralytics.
- ``ViT-B-32`` is the cheapest useful variant: 224x224 input, patch size 32, so
  49 tokens per crop. ``ViT-B-16`` quadruples token count for an improvement
  that does not change merge decisions at the thresholds used here.
- The embedding is only ever used for *relative* comparisons between crops from
  the same photo, so absolute retrieval quality matters less than consistency.

What the embeddings are and are not used for
--------------------------------------------
These vectors decide whether two crops depict the same physical object. They do
**not** classify, name, or price anything — that remains the multimodal model's
job. CLIP has no notion of "Herman Miller Aeron"; it only supports statements of
the form "these two crops look like the same thing".

Cost model
----------
Similarity is needed for every pair of proposals, but embeddings are computed
**once per crop**, not once per pair. N crops go through the encoder in batches,
producing an ``(N, D)`` matrix, and the full ``(N, N)`` similarity matrix is a
single ``E @ E.T``. Because rows are L2-normalized, that matrix product *is*
cosine similarity — no per-pair normalization needed.

The naive alternative, embedding each pair independently, costs O(N^2) forward
passes; at N=300 that is 89,700 encoder calls instead of 300. Proposals are
capped before this stage so the linear cost stays bounded.
"""

from __future__ import annotations

import logging
import threading
from typing import Sequence

import numpy as np

logger = logging.getLogger(__name__)

# Populated on first use. Module-level so a web worker loads the encoder once
# per process rather than once per request.
_MODEL_CACHE: dict[tuple[str, str, str], "_LoadedEncoder"] = {}
_CACHE_LOCK = threading.Lock()


class _LoadedEncoder:
    """A loaded OpenCLIP model with its preprocessing transform and device."""

    __slots__ = ("model", "preprocess", "device", "dim")

    def __init__(self, model, preprocess, device: str, dim: int) -> None:
        self.model = model
        self.preprocess = preprocess
        self.device = device
        self.dim = dim


def resolve_device(requested: str = "auto") -> str:
    """Pick a torch device.

    ``auto`` prefers CUDA, then Apple Silicon MPS, then CPU. MPS is included
    because development happens on Macs while deployment is CPU or CUDA
    containers; without it local benchmark runs are needlessly slow.
    """
    if requested and requested != "auto":
        return requested
    try:
        import torch
    except ImportError:  # pragma: no cover - torch is a hard dep in production
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_encoder(
    model_name: str = "ViT-B-32",
    pretrained: str = "laion2b_s34b_b79k",
    device: str = "auto",
) -> _LoadedEncoder:
    """Load and cache an OpenCLIP encoder.

    Cached by ``(model, pretrained, device)`` under a lock, so concurrent Flask
    threads hitting a cold cache load the weights once instead of racing to
    allocate several copies.
    """
    resolved = resolve_device(device)
    key = (model_name, pretrained, resolved)

    cached = _MODEL_CACHE.get(key)
    if cached is not None:
        return cached

    with _CACHE_LOCK:
        cached = _MODEL_CACHE.get(key)
        if cached is not None:
            return cached

        import open_clip
        import torch

        logger.info("loading OpenCLIP %s/%s on %s", model_name, pretrained, resolved)
        model, _, preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained, device=resolved
        )
        model.eval()

        # Probe the output dimensionality rather than hardcoding 512, so
        # swapping the backbone via config does not silently break shapes.
        with torch.inference_mode():
            probe = torch.zeros(1, 3, 224, 224, device=resolved)
            dim = int(model.encode_image(probe).shape[-1])

        encoder = _LoadedEncoder(model, preprocess, resolved, dim)
        _MODEL_CACHE[key] = encoder
        return encoder


def l2_normalize(matrix: np.ndarray, axis: int = -1) -> np.ndarray:
    """Scale rows to unit length.

    Zero rows are left as zeros rather than becoming NaN. A zero row yields
    similarity 0 against everything, which is the correct "no evidence" answer
    for a crop that failed to embed.
    """
    arr = np.asarray(matrix, dtype=np.float32)
    if arr.size == 0:
        return arr
    norms = np.linalg.norm(arr, axis=axis, keepdims=True)
    norms = np.where(norms > 0.0, norms, 1.0)
    return arr / norms


def cosine_similarity_matrix(embeddings: "np.ndarray | None") -> "np.ndarray | None":
    """Full ``(N, N)`` cosine similarity from an ``(N, D)`` embedding matrix.

    Assumes rows are already L2-normalized (:func:`embed_crops` guarantees
    this), so the Gram matrix is exactly cosine similarity. Values are clipped
    to ``[-1, 1]`` to absorb float32 rounding, which otherwise produces
    self-similarities like 1.0000001 that trip strict threshold comparisons.
    """
    if embeddings is None or embeddings.size == 0:
        return None
    arr = np.asarray(embeddings, dtype=np.float32)
    if arr.ndim != 2:
        raise ValueError(f"expected an (N, D) matrix, got shape {arr.shape}")
    return np.clip(arr @ arr.T, -1.0, 1.0)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors, normalizing defensively."""
    va = np.asarray(a, dtype=np.float32).reshape(-1)
    vb = np.asarray(b, dtype=np.float32).reshape(-1)
    if va.shape != vb.shape:
        raise ValueError(f"vector shapes differ: {va.shape} vs {vb.shape}")
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0.0:
        return 0.0
    return float(np.clip(float(va @ vb) / denom, -1.0, 1.0))


class EmbeddingExtractor:
    """Batched crop encoder.

    Holds a reference to a cached OpenCLIP model. Constructing several
    extractors with the same settings is cheap; they share the underlying
    weights.
    """

    def __init__(
        self,
        model_name: str = "ViT-B-32",
        pretrained: str = "laion2b_s34b_b79k",
        device: str = "auto",
        batch_size: int = 32,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        self.model_name = model_name
        self.pretrained = pretrained
        self.requested_device = device
        self.batch_size = batch_size
        self._encoder: "_LoadedEncoder | None" = None

    @property
    def encoder(self) -> _LoadedEncoder:
        """Load on first access, so constructing an extractor stays cheap."""
        if self._encoder is None:
            self._encoder = load_encoder(self.model_name, self.pretrained, self.requested_device)
        return self._encoder

    @property
    def device(self) -> str:
        return self.encoder.device

    @property
    def dim(self) -> int:
        return self.encoder.dim

    def embed_crops(self, crops: Sequence[np.ndarray]) -> np.ndarray:
        """Encode BGR crops into an L2-normalized ``(N, D)`` float32 matrix.

        Args:
            crops: OpenCV-convention BGR uint8 arrays of arbitrary sizes.

        Returns:
            ``(N, D)`` with unit-length rows, aligned with the input order.
            Crops that fail to preprocess become zero rows so alignment with
            the caller's proposal list is never broken by a skip.
        """
        if not crops:
            return np.zeros((0, 0), dtype=np.float32)

        import torch
        from PIL import Image

        encoder = self.encoder
        preprocess = encoder.preprocess

        tensors: list["torch.Tensor | None"] = []
        for index, crop in enumerate(crops):
            if crop is None or crop.size == 0:
                tensors.append(None)
                continue
            try:
                # OpenCV gives BGR; CLIP's preprocessing expects RGB.
                rgb = crop[:, :, ::-1] if crop.ndim == 3 else np.stack([crop] * 3, axis=-1)
                tensors.append(preprocess(Image.fromarray(np.ascontiguousarray(rgb))))
            except (ValueError, TypeError, OSError) as exc:
                logger.warning("could not preprocess crop %d: %s", index, exc)
                tensors.append(None)

        valid_positions = [i for i, t in enumerate(tensors) if t is not None]
        output = np.zeros((len(crops), encoder.dim), dtype=np.float32)
        if not valid_positions:
            return output

        with torch.inference_mode():
            for start in range(0, len(valid_positions), self.batch_size):
                chunk = valid_positions[start : start + self.batch_size]
                batch = torch.stack([tensors[i] for i in chunk]).to(encoder.device)
                features = encoder.model.encode_image(batch)
                # Normalize on-device: cheaper than moving unnormalized floats
                # to host memory first, and keeps the host copy final.
                features = features / features.norm(dim=-1, keepdim=True).clamp_min(1e-12)
                output[chunk] = features.float().cpu().numpy()

        return output

    def embed_dual(
        self,
        bbox_crops: Sequence[np.ndarray],
        masked_crops: Sequence[np.ndarray],
    ) -> np.ndarray:
        """Average the bbox-crop and masked-crop embeddings of the same objects.

        Both views are L2-normalized before averaging and the mean is
        renormalized, so the result stays on the unit sphere and cosine
        similarity remains comparable to single-view embeddings.

        Averaging unit vectors, rather than concatenating them, keeps
        dimensionality fixed and weights the two views equally. Concatenation
        would double D and — unless each half were rescaled by 1/sqrt(2) —
        change the effective similarity scale, invalidating the configured
        thresholds.
        """
        if len(bbox_crops) != len(masked_crops):
            raise ValueError(f"got {len(bbox_crops)} bbox crops but {len(masked_crops)} masked crops")
        if not bbox_crops:
            return np.zeros((0, 0), dtype=np.float32)

        bbox_embeddings = self.embed_crops(bbox_crops)
        masked_embeddings = self.embed_crops(masked_crops)
        return l2_normalize((bbox_embeddings + masked_embeddings) / 2.0)


__all__ = [
    "EmbeddingExtractor",
    "cosine_similarity",
    "cosine_similarity_matrix",
    "l2_normalize",
    "load_encoder",
    "resolve_device",
]
