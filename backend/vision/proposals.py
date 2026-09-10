"""The :class:`Proposal` record and the clustering machinery that groups them.

A ``Proposal`` is one candidate object region. It carries provenance (which
detector pass and inference resolution produced it) so the benchmark can measure
what each pass actually contributes, and so debug renders can be coloured by
source.

Clustering uses union-find: pairwise "same object" decisions are unioned into
connected components, giving a stable partition regardless of the order pairs
were examined. Greedy suppression, which the original pipeline used, is
order-dependent — it keeps whichever box happened to be sorted first and can
split a chain of overlapping fragments arbitrarily.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Sequence

import numpy as np

from . import geometry

# Source-pass identifiers. Free-form strings would drift, so the known values
# are named here and reused by the detector and the visualizer.
SOURCE_FULL_FRAME = "full"
SOURCE_SECONDARY = "full_lowconf"
SOURCE_ENHANCED = "enhanced"
SOURCE_TILE = "tile"

# Where a final inventory item came from. Phase 10: separating detector recall
# from multimodal recovery is the only way to measure the detector honestly.
ORIGIN_PROPOSAL = "proposal"
ORIGIN_SCENE_RECOVERY = "scene_recovery"


@dataclass
class Proposal:
    """One candidate object region.

    Attributes:
        proposal_id: Stable index assigned once, at creation, and never reused.
            Referenced by debug renders and merge records.
        bbox: ``(x1, y1, x2, y2)`` in *original image* coordinates. Detections
            made at another scale or inside a tile are projected back before a
            ``Proposal`` is constructed, so consumers never deal with
            tile-local or resized coordinates.
        confidence: Detector objectness score.
        source_pass: Which pass produced it; one of the ``SOURCE_*`` constants.
        source_scale: Inference resolution used, in pixels of the long edge.
        mask: Optional binary mask at full image resolution, ``uint8`` with
            values in ``{0, 1}``. Stored full-frame rather than crop-local so
            mask IoU between two proposals is a direct array operation.
        embedding: Optional L2-normalized appearance vector.
        cluster_id: Index of the cluster this proposal was assigned to, or
            ``None`` before clustering.
        is_canonical: True when this proposal represents its cluster in the
            final output.
        merge_reason: Why it was merged, for debugging. See
            :mod:`vision.deduplication`.
        origin: ``proposal`` or ``scene_recovery``.
    """

    bbox: tuple[float, float, float, float]
    confidence: float
    proposal_id: int = -1
    source_pass: str = SOURCE_FULL_FRAME
    source_scale: int = 0
    mask: "np.ndarray | None" = None
    embedding: "np.ndarray | None" = None
    cluster_id: "int | None" = None
    is_canonical: bool = False
    merge_reason: "str | None" = None
    origin: str = ORIGIN_PROPOSAL
    # Members absorbed into this proposal when it became canonical.
    merged_from: list[int] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        x1, y1, x2, y2 = (float(v) for v in self.bbox[:4])
        # Normalize inverted boxes rather than rejecting them; some transforms
        # can flip coordinates and a silent swap is safer than a hard failure
        # in a request path.
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1
        self.bbox = (x1, y1, x2, y2)
        self.confidence = float(self.confidence)

    # -- geometry conveniences --------------------------------------------

    @property
    def area(self) -> float:
        return geometry.box_area(self.bbox)

    @property
    def center(self) -> tuple[float, float]:
        return geometry.box_center(self.bbox)

    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]

    @property
    def has_mask(self) -> bool:
        return self.mask is not None

    @property
    def has_embedding(self) -> bool:
        return self.embedding is not None

    @property
    def mask_area(self) -> float:
        """Pixel count of the mask, or 0 when absent."""
        if self.mask is None:
            return 0.0
        return float(self.mask.sum())

    @property
    def mask_occupancy(self) -> float:
        """Mask area divided by bbox area.

        A low value means the mask covers only a sliver of its own box, which in
        practice signals a bad mask rather than a genuinely thin object. The
        pipeline uses this to decide whether a mask is trustworthy.
        """
        if self.mask is None:
            return 0.0
        box_area = self.area
        if box_area <= 0.0:
            return 0.0
        return float(self.mask_area / box_area)

    def int_bbox(self) -> tuple[int, int, int, int]:
        return tuple(int(round(v)) for v in self.bbox)  # type: ignore[return-value]

    def clipped_bbox(self, width: int, height: int) -> tuple[int, int, int, int]:
        return geometry.clip_box(self.bbox, width, height)

    def to_dict(self, include_arrays: bool = False) -> dict[str, Any]:
        """JSON-serializable view. Arrays are summarized unless requested."""
        out: dict[str, Any] = {
            "proposal_id": self.proposal_id,
            "bbox": [round(float(v), 2) for v in self.bbox],
            "confidence": round(float(self.confidence), 4),
            "source_pass": self.source_pass,
            "source_scale": self.source_scale,
            "cluster_id": self.cluster_id,
            "is_canonical": self.is_canonical,
            "merge_reason": self.merge_reason,
            "origin": self.origin,
            "merged_from": list(self.merged_from),
            "has_mask": self.has_mask,
            "has_embedding": self.has_embedding,
        }
        if self.has_mask:
            out["mask_area"] = round(self.mask_area, 1)
            out["mask_occupancy"] = round(self.mask_occupancy, 4)
        if include_arrays and self.embedding is not None:
            out["embedding"] = [round(float(v), 6) for v in self.embedding]
        if self.metadata:
            out["metadata"] = dict(self.metadata)
        return out


def assign_ids(proposals: Sequence[Proposal], start: int = 0) -> list[Proposal]:
    """Stamp sequential ``proposal_id`` values, in place, and return the list."""
    for offset, proposal in enumerate(proposals):
        proposal.proposal_id = start + offset
    return list(proposals)


def boxes_array(proposals: Sequence[Proposal]) -> np.ndarray:
    """``(N, 4)`` array of boxes, for the vectorized geometry helpers."""
    if not proposals:
        return np.zeros((0, 4), dtype=np.float64)
    return np.asarray([p.bbox for p in proposals], dtype=np.float64)


def confidences_array(proposals: Sequence[Proposal]) -> np.ndarray:
    if not proposals:
        return np.zeros((0,), dtype=np.float64)
    return np.asarray([p.confidence for p in proposals], dtype=np.float64)


def filter_small(proposals: Sequence[Proposal], min_area: float) -> list[Proposal]:
    """Drop degenerate and sub-threshold boxes."""
    return [p for p in proposals if p.area >= min_area]


def cap_proposals(proposals: Sequence[Proposal], limit: int) -> list[Proposal]:
    """Keep the ``limit`` highest-confidence proposals.

    Applied *before* embedding inference. Without a cap, a 0.005 confidence
    threshold on a cluttered image can yield thousands of boxes, and the
    embedding stage cost is linear in that count.
    """
    if limit <= 0 or len(proposals) <= limit:
        return list(proposals)
    ordered = sorted(proposals, key=lambda p: p.confidence, reverse=True)
    return ordered[:limit]


class UnionFind:
    """Disjoint-set forest with union by size and path compression.

    Used to turn pairwise "same object" verdicts into stable clusters. The
    transitive closure it computes is a deliberate design choice: if A matches
    B and B matches C, all three describe one physical item even when A and C
    were never compared directly. That is what makes the result independent of
    iteration order.
    """

    __slots__ = ("_parent", "_size", "_count")

    def __init__(self, n: int) -> None:
        if n < 0:
            raise ValueError("UnionFind size must be non-negative")
        self._parent = list(range(n))
        self._size = [1] * n
        self._count = n

    def __len__(self) -> int:
        return len(self._parent)

    @property
    def num_components(self) -> int:
        return self._count

    def find(self, x: int) -> int:
        if not 0 <= x < len(self._parent):
            raise IndexError(f"index {x} out of range for UnionFind of size {len(self._parent)}")
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        # Path compression: point every node on the walk straight at the root.
        while self._parent[x] != root:
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, a: int, b: int) -> bool:
        """Merge two sets. Returns False when they were already joined."""
        root_a, root_b = self.find(a), self.find(b)
        if root_a == root_b:
            return False
        if self._size[root_a] < self._size[root_b]:
            root_a, root_b = root_b, root_a
        self._parent[root_b] = root_a
        self._size[root_a] += self._size[root_b]
        self._count -= 1
        return True

    def connected(self, a: int, b: int) -> bool:
        return self.find(a) == self.find(b)

    def component_size(self, x: int) -> int:
        return self._size[self.find(x)]

    def groups(self) -> list[list[int]]:
        """Components as lists of member indices.

        Ordered by each component's smallest member so the numbering is
        deterministic across runs.
        """
        buckets: dict[int, list[int]] = {}
        for i in range(len(self._parent)):
            buckets.setdefault(self.find(i), []).append(i)
        return [sorted(members) for _, members in sorted(buckets.items(), key=lambda kv: min(kv[1]))]


def cluster_from_pairs(n: int, pairs: Iterable[tuple[int, int]]) -> list[list[int]]:
    """Build connected components from an iterable of matched index pairs."""
    uf = UnionFind(n)
    for a, b in pairs:
        uf.union(a, b)
    return uf.groups()


def iter_upper_pairs(n: int) -> Iterator[tuple[int, int]]:
    """Yield ``(i, j)`` with ``i < j``, i.e. the upper triangle without the diagonal."""
    return itertools.combinations(range(n), 2)


__all__ = [
    "ORIGIN_PROPOSAL",
    "ORIGIN_SCENE_RECOVERY",
    "SOURCE_ENHANCED",
    "SOURCE_FULL_FRAME",
    "SOURCE_SECONDARY",
    "SOURCE_TILE",
    "Proposal",
    "UnionFind",
    "assign_ids",
    "boxes_array",
    "cap_proposals",
    "cluster_from_pairs",
    "confidences_array",
    "filter_small",
    "iter_upper_pairs",
]
