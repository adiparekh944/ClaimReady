"""Box fusion operators and the coarse geometric pre-fusion pass.

This module owns the *operators* that collapse a group of boxes into one, plus
a cheap high-IoU-only clustering pass. The decision of which proposals describe
the same physical object — using appearance, masks and geometry together —
lives in :mod:`vision.deduplication`. Keeping the operators separate from the
policy means there is exactly one place where "are these the same item?" is
answered.

Why not just take the union
---------------------------
The original pipeline merged overlapping boxes by taking their outer union and
keeping the maximum confidence. That is the wrong operator in the common case.
When two passes localize the same object slightly differently, the union is
strictly larger than either estimate, so repeated merges inflate boxes outward
and drag background into the crop that gets sent for identification.
Confidence-weighted averaging instead pulls the estimate toward the detections
the model was most sure about — the Weighted Box Fusion result of Solovyev et
al., *Weighted boxes fusion: Ensembling boxes from different object detection
models* (2019).

Union is still correct for one situation this data produces often: a genuinely
fragmented detection, where a low-confidence pass fires on a chair's arm and its
seat separately. Averaging two fragments yields a box covering neither. So union
is retained as an operator, but it is only selected when appearance evidence
supports it.

Three operators, three situations
---------------------------------
``weighted_box_fusion``
    Confidence-weighted coordinate average. For clusters where the members
    agree on where the object is.
``union_fusion``
    Outer envelope. For clusters of fragments of one larger object.
``select_by_confidence``
    Pick a representative member unchanged. For nested clusters, where any
    average or envelope would describe neither box.
"""

from __future__ import annotations

import logging
from typing import Sequence

import numpy as np

from . import geometry
from .config import VisionConfig
from .proposals import Proposal, UnionFind, boxes_array

logger = logging.getLogger(__name__)

# Merge reasons recorded on canonical proposals for debugging and evaluation.
MERGE_WBF = "wbf"
MERGE_IOU = "iou"
MERGE_CONTAINMENT = "containment"
MERGE_CONTAINMENT_CLIP = "containment+clip"
MERGE_FRAGMENT_UNION = "fragment_union"
MERGE_MASK_OVERLAP = "mask_overlap"
MERGE_CLIP = "clip"

# Which operator to apply for a given reason. A cluster whose members were
# matched for several reasons resolves via OPERATOR_PRIORITY below.
_UNION_REASONS = frozenset({MERGE_FRAGMENT_UNION})
_SELECT_REASONS = frozenset({MERGE_CONTAINMENT, MERGE_CONTAINMENT_CLIP})

# A union anywhere in the cluster means it describes fragments, which dominates:
# averaging fragments would lose the object. Nesting comes next, and plain
# overlap averaging is the default. Resolving per cluster rather than per pair
# keeps the outcome independent of the order pairs were visited.
OPERATOR_PRIORITY = ("union", "select", "wbf")


def weighted_box_fusion(
    boxes: "np.ndarray | Sequence[Sequence[float]]",
    scores: "np.ndarray | Sequence[float]",
) -> tuple[tuple[float, float, float, float], float]:
    """Fuse boxes into one confidence-weighted box.

    Each coordinate becomes ``sum(score_i * coord_i) / sum(score_i)``. The fused
    confidence is the *mean* of member scores, following the WBF convention: it
    rewards agreement between passes rather than letting one stray
    high-confidence box dominate a cluster of weak ones.

    Falls back to an unweighted mean when every score is zero, so a cluster of
    zero-confidence boxes still yields a usable box instead of dividing by zero.
    """
    arr = np.asarray(boxes, dtype=np.float64)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    arr = arr[:, :4]
    if arr.shape[0] == 0:
        raise ValueError("weighted_box_fusion requires at least one box")

    weights = np.asarray(scores, dtype=np.float64).reshape(-1)
    if weights.shape[0] != arr.shape[0]:
        raise ValueError(f"got {arr.shape[0]} boxes but {weights.shape[0]} scores")

    if arr.shape[0] == 1:
        # Short-circuit the single-member case so it is returned bit-exact.
        # Dividing by the weight and multiplying back introduces float drift
        # (a coordinate of 3.0 comes back as 2.9999999999999996), which is
        # harmless for pixels but makes equality checks noisy for no benefit.
        return (float(arr[0, 0]), float(arr[0, 1]), float(arr[0, 2]), float(arr[0, 3])), float(weights[0])

    weights = np.clip(weights, 0.0, None)
    total = float(weights.sum())
    if total <= 0.0:
        fused = arr.mean(axis=0)
        return (float(fused[0]), float(fused[1]), float(fused[2]), float(fused[3])), 0.0

    fused = (arr * weights[:, None]).sum(axis=0) / total
    return (
        (float(fused[0]), float(fused[1]), float(fused[2]), float(fused[3])),
        float(weights.mean()),
    )


def union_fusion(
    boxes: Sequence[Sequence[float]],
    scores: Sequence[float],
) -> tuple[tuple[float, float, float, float], float]:
    """Outer envelope of a cluster of fragments.

    Confidence is the maximum rather than the mean: a fragmented object is at
    least as likely to be real as its most convincing piece, and averaging would
    penalize an object precisely because the detector saw it in pieces.
    """
    if not len(boxes):
        raise ValueError("union_fusion requires at least one box")
    return geometry.union_box(boxes), float(max(scores))


def select_by_confidence(
    members: Sequence[Proposal],
) -> tuple[tuple[float, float, float, float], float, Proposal]:
    """Choose one member to represent a nested cluster.

    Ties on confidence go to the *larger* box. For downstream identification a
    slightly generous crop is recoverable, whereas a crop tighter than the
    object is not.
    """
    if not members:
        raise ValueError("select_by_confidence requires at least one proposal")
    best = max(members, key=lambda m: (m.confidence, m.area))
    return best.bbox, best.confidence, best


def choose_operator(reasons: "set[str] | frozenset[str]") -> str:
    """Resolve a cluster's merge reasons to a single operator name."""
    if reasons & _UNION_REASONS:
        return "union"
    if reasons and reasons <= _SELECT_REASONS:
        return "select"
    return "wbf"


def fuse_cluster(
    members: Sequence[Proposal],
    reasons: "Sequence[str] | None" = None,
) -> Proposal:
    """Collapse one cluster into a single canonical proposal.

    The operator is chosen from the cluster's merge reasons via
    :func:`choose_operator`. The highest-confidence member acts as the anchor:
    its ``proposal_id``, mask, embedding and metadata carry forward, so work
    already done is not discarded.
    """
    if not members:
        raise ValueError("fuse_cluster requires at least one proposal")

    if len(members) == 1:
        only = members[0]
        only.is_canonical = True
        if reasons:
            only.merge_reason = reasons[0]
        return only

    reason_set = set(reasons or ())
    operator = choose_operator(reason_set)
    member_boxes = [m.bbox for m in members]
    member_scores = [m.confidence for m in members]

    if operator == "union":
        bbox, confidence = union_fusion(member_boxes, member_scores)
        anchor = max(members, key=lambda m: m.confidence)
        reason = MERGE_FRAGMENT_UNION
    elif operator == "select":
        bbox, confidence, anchor = select_by_confidence(members)
        reason = MERGE_CONTAINMENT_CLIP if MERGE_CONTAINMENT_CLIP in reason_set else MERGE_CONTAINMENT
    else:
        bbox, confidence = weighted_box_fusion(member_boxes, member_scores)
        anchor = max(members, key=lambda m: m.confidence)
        # Preserve a more specific reason when one was recorded; otherwise the
        # cluster was matched purely on overlap.
        specific = reason_set - {MERGE_IOU, MERGE_WBF}
        reason = sorted(specific)[0] if specific else MERGE_WBF

    canonical = Proposal(
        bbox=bbox,
        confidence=confidence,
        proposal_id=anchor.proposal_id,
        source_pass=anchor.source_pass,
        source_scale=anchor.source_scale,
        mask=anchor.mask,
        embedding=anchor.embedding,
        origin=anchor.origin,
        merge_reason=reason,
        merged_from=sorted(m.proposal_id for m in members if m.proposal_id != anchor.proposal_id),
        metadata=dict(anchor.metadata),
    )
    canonical.is_canonical = True
    canonical.metadata["cluster_size"] = len(members)
    canonical.metadata["cluster_reasons"] = sorted(reason_set)
    canonical.metadata["fusion_operator"] = operator
    return canonical


def fuse_by_iou(proposals: Sequence[Proposal], iou_threshold: float) -> list[Proposal]:
    """Coarse pre-fusion pass: cluster on high IoU alone, then apply WBF.

    This runs *before* embeddings in the pipeline. High-IoU agreement is
    unambiguous — two boxes covering 55%+ of their union are two views of one
    object regardless of appearance — so it needs no appearance model and can
    safely collapse the flood of near-identical boxes that multi-scale
    inference at very low confidence produces.

    The purpose is coarse-to-fine cost control. Embedding inference is linear in
    proposal count, and the proposal cap has to be applied before it; capping
    raw detector output by confidence alone would happily keep three copies of
    one object while discarding a distinct one. Collapsing exact agreement first
    means the cap operates on distinct candidates.

    Ambiguous cases (nesting, fragments) are deliberately left alone here and
    resolved in :mod:`vision.deduplication` once appearance is available.
    """
    count = len(proposals)
    if count == 0:
        return []
    if count == 1:
        proposals[0].cluster_id = 0
        proposals[0].is_canonical = True
        return list(proposals)

    boxes = boxes_array(proposals)
    iou_matrix = geometry.pairwise_iou(boxes, boxes)

    # Only the upper triangle above threshold can merge, so the Python-level
    # loop touches far fewer than N^2 pairs while the matrix itself is
    # computed vectorized.
    rows, cols = np.where(np.triu(iou_matrix >= iou_threshold, k=1))

    uf = UnionFind(count)
    for i, j in zip(rows.tolist(), cols.tolist()):
        uf.union(i, j)

    fused: list[Proposal] = []
    for cluster_id, members in enumerate(uf.groups()):
        canonical = fuse_cluster(
            [proposals[m] for m in members],
            [MERGE_WBF] * max(0, len(members) - 1),
        )
        canonical.cluster_id = cluster_id
        fused.append(canonical)

    fused.sort(key=lambda p: p.confidence, reverse=True)
    logger.debug("iou pre-fusion: %d proposals -> %d clusters", count, len(fused))
    return fused


def greedy_iou_suppression(proposals: Sequence[Proposal], iou_threshold: float) -> list[Proposal]:
    """Baseline suppression, retained so the ablation has an honest control.

    Reproduces the original ``fast_deduplication`` behaviour: sort by
    confidence, keep a box unless it overlaps something already kept. Note this
    is order-dependent and *discards* rather than fuses — it keeps whichever box
    sorted first, so the surviving box is one detector's estimate rather than a
    consensus. That is exactly the weakness the rest of this module addresses,
    and configuration ``A`` in the benchmark measures it.
    """
    if not proposals:
        return []

    ordered = sorted(proposals, key=lambda p: p.confidence, reverse=True)
    kept: list[Proposal] = []
    for candidate in ordered:
        if any(geometry.iou(candidate.bbox, k.bbox) > iou_threshold for k in kept):
            continue
        candidate.is_canonical = True
        candidate.cluster_id = len(kept)
        candidate.merge_reason = MERGE_IOU
        kept.append(candidate)
    return kept


__all__ = [
    "MERGE_CLIP",
    "MERGE_CONTAINMENT",
    "MERGE_CONTAINMENT_CLIP",
    "MERGE_FRAGMENT_UNION",
    "MERGE_IOU",
    "MERGE_MASK_OVERLAP",
    "MERGE_WBF",
    "OPERATOR_PRIORITY",
    "choose_operator",
    "fuse_by_iou",
    "fuse_cluster",
    "greedy_iou_suppression",
    "select_by_confidence",
    "union_fusion",
    "weighted_box_fusion",
]
