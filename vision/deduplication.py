"""Geometric and semantic proposal deduplication.

This module owns the single answer to "do these two proposals describe the same
physical object?". :mod:`vision.fusion` supplies the operators that collapse a
matched group; the policy lives here.

Why box IoU alone is not enough
-------------------------------
The original pipeline decided duplication from bounding-box IoU with
size-dependent thresholds. That fails in both directions on real inventory
photos:

*False merges.* A lamp standing in front of a bookshelf produces two boxes with
high IoU that are two distinct items. A phone lying on a desk is almost fully
contained in the desk's box. Geometry cannot tell either case from a genuine
duplicate.

*Missed merges.* The same sofa detected at 640px and at 960px can land at
IoU 0.45 — below any safe threshold — while clearly being one object. And a
low-confidence pass that fragments an L-shaped sectional into two boxes gives
near-zero IoU between pieces of one item.

Appearance evidence resolves both. Two crops of the same object have high CLIP
cosine similarity even when their boxes disagree; a lamp and a bookshelf do not,
however much their boxes overlap.

The decision rule
-----------------
For each candidate pair, signals are computed and the first matching clause
wins. Every clause records *why*, which is what makes the behaviour auditable
in the debug renders and countable in the benchmark.

1. ``iou >= iou_threshold``
   Unambiguous overlap. Merge on geometry alone; no appearance needed.
   → ``"iou"``

2. ``mask_iou >= mask_iou_threshold`` (both masks trusted)
   Pixel-level agreement, which is stronger evidence than box overlap because
   it is not fooled by two objects sharing a bounding region.
   → ``"mask_overlap"``

3. ``iou >= moderate_iou_threshold`` and ``cosine >= embedding_similarity_threshold``
   and ``size_ratio >= size_ratio_threshold``
   Partial overlap plus appearance agreement. The size guard stops a small
   object being absorbed into a much larger one just because they look alike
   (two similar cushions, one near and one far).
   → ``"iou+clip"``

4. ``containment >= containment_threshold`` and ``cosine >= embedding_strict_threshold``
   One box nested in another *and* they look like the same thing. The strict
   threshold applies because nesting is the most dangerous case: almost
   everything in a room is contained in some larger object's box. Without
   embeddings this clause is skipped rather than assumed.
   → ``"containment+clip"``

5. ``iou >= fragment_iou_threshold`` and ``cosine >= embedding_similarity_threshold``
   and ``normalized_center_distance <= center_distance_threshold``
   Barely-touching fragments of one object, e.g. a low-confidence pass that
   split an L-shaped sectional into two pieces. What keeps this from chaining
   across a row of identical dining chairs is the IoU floor, not the appearance
   check: distinct adjacent objects do not overlap, so they never reach this
   clause. The centre-distance term rejects strongly asymmetric pairs where a
   small box clips the corner of a large one.
   → ``"fragment_union"``

   This is the most speculative clause, so it is gated behind
   ``enable_fragment_union``, is off in FAST mode, and its firing count is
   reported separately by the benchmark rather than folded into a total.

Anything else stays separate. The rule is deliberately asymmetric in its risk
appetite: over-merging silently deletes an inventory item and its value, while
under-merging leaves a duplicate proposal that the downstream multimodal stage
usually reconciles. When uncertain, keep both.

Clustering
----------
Matched pairs are unioned into connected components (:class:`vision.proposals.UnionFind`),
so the partition does not depend on the order pairs were examined. The original
greedy suppression kept whichever box sorted first and could split a chain of
overlapping fragments arbitrarily.

Transitivity is intentional: if A matches B and B matches C, all three are one
item even if A and C were never directly compared. The centre-distance and size
guards in clauses 3–5 are what prevent this from chaining across a row of
similar objects.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from . import geometry, segmentation
from .config import VisionConfig
from .fusion import (
    MERGE_CONTAINMENT_CLIP,
    MERGE_FRAGMENT_UNION,
    MERGE_IOU,
    MERGE_MASK_OVERLAP,
    fuse_cluster,
)
from .proposals import Proposal, UnionFind, boxes_array

logger = logging.getLogger(__name__)

MERGE_IOU_CLIP = "iou+clip"


@dataclass
class MergeRecord:
    """One pairwise merge decision, kept for debugging and evaluation."""

    proposal_a: int
    proposal_b: int
    reason: str
    iou: float
    containment: float
    mask_iou: float
    similarity: float

    def to_dict(self) -> dict[str, object]:
        return {
            "a": self.proposal_a,
            "b": self.proposal_b,
            "reason": self.reason,
            "iou": round(self.iou, 4),
            "containment": round(self.containment, 4),
            "mask_iou": round(self.mask_iou, 4),
            "similarity": round(self.similarity, 4),
        }


@dataclass
class DeduplicationResult:
    """Deduplicated proposals plus an audit trail of how they were formed."""

    proposals: list[Proposal]
    merges: list[MergeRecord] = field(default_factory=list)
    clusters: list[list[int]] = field(default_factory=list)
    input_count: int = 0

    @property
    def output_count(self) -> int:
        return len(self.proposals)

    @property
    def duplicates_removed(self) -> int:
        return max(0, self.input_count - self.output_count)

    def reason_counts(self) -> dict[str, int]:
        """How many pairs were merged for each reason.

        The benchmark reports this so the contribution of each clause — and in
        particular of the appearance-gated ones — is measurable rather than
        assumed.
        """
        counts: dict[str, int] = {}
        for record in self.merges:
            counts[record.reason] = counts.get(record.reason, 0) + 1
        return dict(sorted(counts.items()))

    def to_dict(self) -> dict[str, object]:
        return {
            "input_count": self.input_count,
            "output_count": self.output_count,
            "duplicates_removed": self.duplicates_removed,
            "reason_counts": self.reason_counts(),
            "clusters": [list(c) for c in self.clusters],
            "merges": [m.to_dict() for m in self.merges],
        }


class Deduplicator:
    """Applies the decision rule above and fuses the resulting clusters."""

    def __init__(self, config: VisionConfig) -> None:
        self.config = config

    def _signals(
        self,
        proposals: Sequence[Proposal],
        similarity: "np.ndarray | None",
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, "np.ndarray | None"]:
        """Compute every pairwise signal matrix at once.

        All of these are vectorized numpy operations over the whole proposal
        set, so the per-pair Python loop below only reads precomputed values.
        """
        boxes = boxes_array(proposals)
        iou_matrix = geometry.pairwise_iou(boxes, boxes)
        containment_matrix = geometry.pairwise_containment(boxes)
        center_matrix = geometry.pairwise_normalized_center_distance(boxes)
        size_matrix = geometry.pairwise_size_ratio(boxes)

        masks = segmentation.trusted_masks(proposals)
        if self.config.enable_segmentation and any(m is not None for m in masks):
            mask_matrix = segmentation.pairwise_mask_iou(masks)
        else:
            mask_matrix = np.zeros_like(iou_matrix)

        return iou_matrix, containment_matrix, center_matrix, size_matrix, mask_matrix, similarity

    def _verdict(
        self,
        i: int,
        j: int,
        iou_matrix: np.ndarray,
        containment_matrix: np.ndarray,
        center_matrix: np.ndarray,
        size_matrix: np.ndarray,
        mask_matrix: np.ndarray,
        similarity: "np.ndarray | None",
    ) -> "tuple[str, float] | None":
        """Evaluate the clauses for one pair. Returns ``(reason, similarity)``."""
        config = self.config
        pair_iou = float(iou_matrix[i, j])
        nested = max(float(containment_matrix[i, j]), float(containment_matrix[j, i]))
        pair_mask_iou = float(mask_matrix[i, j])
        cosine = float(similarity[i, j]) if similarity is not None else 0.0

        # Clause 1: unambiguous box overlap.
        if pair_iou >= config.iou_threshold:
            return MERGE_IOU, cosine

        # Clause 2: pixel-level mask agreement.
        if pair_mask_iou >= config.mask_iou_threshold:
            return MERGE_MASK_OVERLAP, cosine

        has_appearance = similarity is not None
        similar = has_appearance and cosine >= config.embedding_similarity_threshold
        very_similar = has_appearance and cosine >= config.embedding_strict_threshold
        comparable_size = float(size_matrix[i, j]) >= config.size_ratio_threshold

        # Clause 3: partial overlap corroborated by appearance.
        if similar and comparable_size and pair_iou >= config.moderate_iou_threshold:
            return MERGE_IOU_CLIP, cosine

        # Clause 4: nesting, only ever with strong appearance agreement.
        if very_similar and nested >= config.containment_threshold:
            return MERGE_CONTAINMENT_CLIP, cosine

        # Clause 5: adjacent fragments of one object.
        if (
            config.enable_fragment_union
            and similar
            and pair_iou >= config.fragment_iou_threshold
            and float(center_matrix[i, j]) <= config.center_distance_threshold
        ):
            return MERGE_FRAGMENT_UNION, cosine

        return None

    def deduplicate(
        self,
        proposals: Sequence[Proposal],
        similarity: "np.ndarray | None" = None,
    ) -> DeduplicationResult:
        """Cluster and fuse proposals that describe the same physical object.

        Args:
            proposals: Candidates in original-image coordinates, ideally already
                through :func:`vision.fusion.fuse_by_iou` and the proposal cap.
            similarity: Optional ``(N, N)`` cosine matrix aligned with
                ``proposals``. When ``None`` (FAST mode, or embeddings
                disabled), the appearance-gated clauses are skipped rather than
                treated as satisfied — so FAST degrades to geometry-only
                behaviour instead of merging recklessly.

        Returns:
            A :class:`DeduplicationResult` whose ``proposals`` hold one
            canonical entry per cluster, sorted by descending confidence.
        """
        count = len(proposals)
        if count == 0:
            return DeduplicationResult(proposals=[], input_count=0)
        if count == 1:
            single = proposals[0]
            single.cluster_id = 0
            single.is_canonical = True
            return DeduplicationResult(proposals=[single], clusters=[[0]], input_count=1)

        if similarity is not None:
            if similarity.shape != (count, count):
                raise ValueError(f"similarity must be ({count}, {count}), got {similarity.shape}")
            if not self.config.enable_embeddings:
                logger.debug("embeddings disabled in config; ignoring supplied similarity matrix")
                similarity = None

        signals = self._signals(proposals, similarity)
        iou_matrix, containment_matrix, center_matrix, size_matrix, mask_matrix, similarity = signals

        # A pair can only match if it has *some* geometric or mask relationship.
        # Appearance alone is never sufficient — two identical dining chairs
        # across the room would otherwise collapse into one inventory item.
        # This also keeps the Python loop well below the N^2 bound.
        weakest_iou = min(
            self.config.iou_threshold,
            self.config.moderate_iou_threshold,
            self.config.fragment_iou_threshold if self.config.enable_fragment_union else 1.0,
        )
        related = (
            (iou_matrix >= weakest_iou)
            | (containment_matrix >= self.config.containment_threshold)
            | (containment_matrix.T >= self.config.containment_threshold)
            | (mask_matrix >= self.config.mask_iou_threshold)
        )
        rows, cols = np.where(np.triu(related, k=1))

        uf = UnionFind(count)
        merges: list[MergeRecord] = []
        pair_reasons: dict[tuple[int, int], str] = {}

        for i, j in zip(rows.tolist(), cols.tolist()):
            verdict = self._verdict(
                i, j, iou_matrix, containment_matrix, center_matrix, size_matrix, mask_matrix, similarity
            )
            if verdict is None:
                continue
            reason, cosine = verdict
            uf.union(i, j)
            pair_reasons[(i, j)] = reason
            merges.append(
                MergeRecord(
                    proposal_a=proposals[i].proposal_id,
                    proposal_b=proposals[j].proposal_id,
                    reason=reason,
                    iou=float(iou_matrix[i, j]),
                    containment=max(float(containment_matrix[i, j]), float(containment_matrix[j, i])),
                    mask_iou=float(mask_matrix[i, j]),
                    similarity=cosine,
                )
            )

        groups = uf.groups()
        canonical: list[Proposal] = []
        for cluster_id, members in enumerate(groups):
            member_set = set(members)
            reasons = [r for (a, b), r in pair_reasons.items() if a in member_set and b in member_set]
            fused = fuse_cluster([proposals[m] for m in members], reasons)
            fused.cluster_id = cluster_id
            # Union the masks of everything absorbed, so a fused proposal's mask
            # covers the whole object rather than just the anchor's fragment.
            if len(members) > 1 and self.config.enable_segmentation:
                merged_mask = segmentation.merge_masks([proposals[m].mask for m in members])
                if merged_mask is not None:
                    fused.mask = merged_mask
            canonical.append(fused)

        canonical.sort(key=lambda p: p.confidence, reverse=True)
        logger.debug(
            "dedup: %d proposals -> %d clusters (%d pairwise merges)",
            count,
            len(canonical),
            len(merges),
        )
        return DeduplicationResult(
            proposals=canonical,
            merges=merges,
            clusters=groups,
            input_count=count,
        )


__all__ = [
    "MERGE_IOU_CLIP",
    "DeduplicationResult",
    "Deduplicator",
    "MergeRecord",
]
