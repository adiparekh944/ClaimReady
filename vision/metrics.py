"""Evaluation metrics for proposals, deduplication and video association.

Scope and honesty
-----------------
Detection metrics need ground truth. This repository ships no annotated
dataset, so every function that requires labels raises or returns ``None``
rather than substituting a proxy. Functions that need no labels — proposal
counts, latency, reduction ratios — work unconditionally. The benchmark reports
the two groups separately so an unlabelled run cannot be mistaken for an
evaluated one.

Three metric families
---------------------
**Detection quality** (needs boxes): greedy IoU matching gives precision,
recall and F1 at a threshold; averaging precision over recall gives AP, and
averaging AP over IoU thresholds 0.50:0.05:0.95 gives the COCO-style
mAP@0.5:0.95.

**Deduplication quality** (needs duplicate groupings): treats dedup as a
pairwise decision problem. For every pair of raw proposals, ground truth says
whether they are the same object and the system says whether it merged them.
This gives duplicate precision, recall and F1. Pair-level rather than
cluster-level because it degrades gracefully — one wrong merge in a large
cluster costs a few pairs rather than invalidating the whole cluster.

**Video association** (partially label-free): the ratio of tracker IDs to
inventory identities, re-identification counts and absorbed ID switches are all
observable without labels. Judging whether a merge was *correct* needs labels,
so the correctness metrics are separate and optional.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from . import geometry

logger = logging.getLogger(__name__)

# COCO's standard IoU sweep for mAP@0.5:0.95.
COCO_IOU_THRESHOLDS = tuple(round(0.50 + 0.05 * i, 2) for i in range(10))


@dataclass
class DetectionMetrics:
    """Precision/recall/F1 at one IoU threshold."""

    iou_threshold: float
    true_positives: int
    false_positives: int
    false_negatives: int
    num_predictions: int
    num_ground_truth: int

    @property
    def precision(self) -> float:
        denominator = self.true_positives + self.false_positives
        return self.true_positives / denominator if denominator else 0.0

    @property
    def recall(self) -> float:
        denominator = self.true_positives + self.false_negatives
        return self.true_positives / denominator if denominator else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return (2 * p * r / (p + r)) if (p + r) else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "iou_threshold": self.iou_threshold,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "num_predictions": self.num_predictions,
            "num_ground_truth": self.num_ground_truth,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
        }


def match_predictions(
    predictions: Sequence[Sequence[float]],
    ground_truth: Sequence[Sequence[float]],
    iou_threshold: float = 0.5,
    scores: "Sequence[float] | None" = None,
) -> tuple[list[int], DetectionMetrics]:
    """Greedily match predicted boxes to ground truth by IoU.

    Predictions are considered in descending confidence order, each claiming
    the best unclaimed ground-truth box above the threshold. This is the
    standard COCO/VOC matching protocol; the confidence ordering is what makes
    it well-defined, since a lower-confidence prediction should not be able to
    steal a match from a higher-confidence one.

    Returns:
        ``(assignment, metrics)`` where ``assignment[i]`` is the ground-truth
        index matched to prediction ``i``, or ``-1`` if unmatched.
    """
    num_pred = len(predictions)
    num_gt = len(ground_truth)
    assignment = [-1] * num_pred

    if num_pred == 0 or num_gt == 0:
        return assignment, DetectionMetrics(
            iou_threshold=iou_threshold,
            true_positives=0,
            false_positives=num_pred,
            false_negatives=num_gt,
            num_predictions=num_pred,
            num_ground_truth=num_gt,
        )

    iou_matrix = geometry.pairwise_iou(predictions, ground_truth)
    order = (
        list(range(num_pred))
        if scores is None
        else sorted(range(num_pred), key=lambda i: scores[i], reverse=True)
    )

    claimed: set[int] = set()
    true_positives = 0
    for pred_index in order:
        best_gt = -1
        best_iou = iou_threshold
        for gt_index in range(num_gt):
            if gt_index in claimed:
                continue
            value = float(iou_matrix[pred_index, gt_index])
            if value >= best_iou:
                best_iou = value
                best_gt = gt_index
        if best_gt >= 0:
            assignment[pred_index] = best_gt
            claimed.add(best_gt)
            true_positives += 1

    return assignment, DetectionMetrics(
        iou_threshold=iou_threshold,
        true_positives=true_positives,
        false_positives=num_pred - true_positives,
        false_negatives=num_gt - true_positives,
        num_predictions=num_pred,
        num_ground_truth=num_gt,
    )


def average_precision(
    predictions: Sequence[Sequence[float]],
    ground_truth: Sequence[Sequence[float]],
    scores: Sequence[float],
    iou_threshold: float = 0.5,
) -> float:
    """Average precision at one IoU threshold, by all-point interpolation.

    Walks predictions in descending confidence, accumulating a
    precision-recall curve, then integrates it. Uses the all-point
    interpolation COCO adopted rather than the older 11-point VOC sampling,
    which is coarse enough to be misleading at low object counts.
    """
    if len(predictions) != len(scores):
        raise ValueError(f"got {len(predictions)} predictions but {len(scores)} scores")
    num_gt = len(ground_truth)
    if num_gt == 0:
        return 0.0
    if not predictions:
        return 0.0

    iou_matrix = geometry.pairwise_iou(predictions, ground_truth)
    order = sorted(range(len(predictions)), key=lambda i: scores[i], reverse=True)

    claimed: set[int] = set()
    tps = np.zeros(len(order), dtype=np.float64)
    fps = np.zeros(len(order), dtype=np.float64)

    for position, pred_index in enumerate(order):
        best_gt, best_iou = -1, iou_threshold
        for gt_index in range(num_gt):
            if gt_index in claimed:
                continue
            value = float(iou_matrix[pred_index, gt_index])
            if value >= best_iou:
                best_iou, best_gt = value, gt_index
        if best_gt >= 0:
            claimed.add(best_gt)
            tps[position] = 1.0
        else:
            fps[position] = 1.0

    cumulative_tp = np.cumsum(tps)
    cumulative_fp = np.cumsum(fps)
    recalls = cumulative_tp / num_gt
    precisions = cumulative_tp / np.maximum(cumulative_tp + cumulative_fp, 1e-9)

    # Make precision monotonically non-increasing as recall grows, so a dip
    # followed by a recovery does not understate AP.
    precisions = np.maximum.accumulate(precisions[::-1])[::-1]

    recalls = np.concatenate(([0.0], recalls))
    precisions = np.concatenate(([precisions[0] if precisions.size else 0.0], precisions))
    return float(np.sum(np.diff(recalls) * precisions[1:]))


def mean_average_precision(
    predictions: Sequence[Sequence[float]],
    ground_truth: Sequence[Sequence[float]],
    scores: Sequence[float],
    iou_thresholds: Sequence[float] = COCO_IOU_THRESHOLDS,
) -> dict[str, float]:
    """AP at each threshold plus the mean, i.e. mAP@0.5:0.95."""
    per_threshold = {
        f"ap@{threshold:.2f}": average_precision(predictions, ground_truth, scores, threshold)
        for threshold in iou_thresholds
    }
    values = list(per_threshold.values())
    out = {k: round(v, 4) for k, v in per_threshold.items()}
    out["map@0.50:0.95"] = round(float(np.mean(values)) if values else 0.0, 4)
    out["map@0.50"] = round(per_threshold.get("ap@0.50", 0.0), 4)
    return out


@dataclass
class DuplicateMetrics:
    """Pairwise duplicate-detection quality.

    A "positive" is the claim that two raw proposals depict the same physical
    object. Precision is how many claimed merges were right; recall is how many
    genuine duplicate pairs were caught.
    """

    true_positives: int
    false_positives: int
    false_negatives: int
    total_pairs: int

    @property
    def precision(self) -> float:
        denominator = self.true_positives + self.false_positives
        return self.true_positives / denominator if denominator else 0.0

    @property
    def recall(self) -> float:
        denominator = self.true_positives + self.false_negatives
        return self.true_positives / denominator if denominator else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return (2 * p * r / (p + r)) if (p + r) else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "duplicate_precision": round(self.precision, 4),
            "duplicate_recall": round(self.recall, 4),
            "duplicate_f1": round(self.f1, 4),
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "total_pairs": self.total_pairs,
        }


def _pairs_from_groups(groups: Iterable[Sequence[int]]) -> set[tuple[int, int]]:
    """Every unordered within-group pair, as sorted tuples."""
    pairs: set[tuple[int, int]] = set()
    for group in groups:
        members = sorted(group)
        for i, a in enumerate(members):
            for b in members[i + 1 :]:
                pairs.add((a, b))
    return pairs


def duplicate_metrics(
    predicted_clusters: Iterable[Sequence[int]],
    ground_truth_clusters: Iterable[Sequence[int]],
    num_items: int,
) -> DuplicateMetrics:
    """Score a clustering against a reference clustering, pair by pair.

    Args:
        predicted_clusters: Index groups the system merged.
        ground_truth_clusters: Index groups that truly are the same object.
        num_items: Total raw proposals, which fixes the pair universe.
    """
    if num_items < 0:
        raise ValueError("num_items must be non-negative")

    predicted_pairs = _pairs_from_groups(predicted_clusters)
    truth_pairs = _pairs_from_groups(ground_truth_clusters)
    total_pairs = num_items * (num_items - 1) // 2

    true_positives = len(predicted_pairs & truth_pairs)
    return DuplicateMetrics(
        true_positives=true_positives,
        false_positives=len(predicted_pairs - truth_pairs),
        false_negatives=len(truth_pairs - predicted_pairs),
        total_pairs=total_pairs,
    )


def association_metrics(
    generated_track_ids: int,
    inventory_identities: int,
    reid_events: int,
    id_switches_absorbed: int,
    true_object_count: "int | None" = None,
) -> dict[str, Any]:
    """Video association statistics.

    ``generated_track_ids`` above ``inventory_identities`` means the tracker
    fragmented objects and re-identification stitched them back. The
    ``identity_inflation`` figures are only computed when a true object count is
    supplied; without labels they are reported as ``None`` rather than guessed.
    """
    out: dict[str, Any] = {
        "generated_track_ids": generated_track_ids,
        "inventory_identities": inventory_identities,
        "reid_events": reid_events,
        "id_switches_absorbed": id_switches_absorbed,
        "track_id_to_identity_ratio": (
            round(generated_track_ids / inventory_identities, 4) if inventory_identities else None
        ),
    }

    if true_object_count is None or true_object_count <= 0:
        out["true_object_count"] = None
        out["identity_inflation"] = None
        out["tracker_only_inflation"] = None
        out["duplicate_entries"] = None
        return out

    out["true_object_count"] = true_object_count
    out["identity_inflation"] = round(inventory_identities / true_object_count, 4)
    out["tracker_only_inflation"] = round(generated_track_ids / true_object_count, 4)
    out["duplicate_entries"] = max(0, inventory_identities - true_object_count)
    return out


@dataclass
class LatencyStats:
    """Aggregated per-stage latency over a set of images."""

    stage_totals: dict[str, float] = field(default_factory=dict)
    per_image: list[dict[str, float]] = field(default_factory=list)

    def add(self, timings: Mapping[str, float]) -> None:
        self.per_image.append(dict(timings))
        for stage, value in timings.items():
            self.stage_totals[stage] = self.stage_totals.get(stage, 0.0) + float(value)

    @property
    def count(self) -> int:
        return len(self.per_image)

    def mean_by_stage(self) -> dict[str, float]:
        if not self.count:
            return {}
        return {stage: round(total / self.count, 4) for stage, total in sorted(self.stage_totals.items())}

    def percentiles(self, stage: str = "total") -> dict[str, float]:
        """Median, p90 and p95 for one stage.

        Percentiles matter more than the mean for a request path: a mean hides
        the tail that users actually notice. Reported only when there are
        enough samples for the figure to mean anything.
        """
        values = [t.get(stage, 0.0) for t in self.per_image if stage in t]
        if not values:
            return {}
        array = np.asarray(values, dtype=np.float64)
        out = {
            "mean": round(float(array.mean()), 4),
            "min": round(float(array.min()), 4),
            "max": round(float(array.max()), 4),
            "p50": round(float(np.percentile(array, 50)), 4),
        }
        if len(values) >= 10:
            out["p90"] = round(float(np.percentile(array, 90)), 4)
        if len(values) >= 20:
            out["p95"] = round(float(np.percentile(array, 95)), 4)
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "images": self.count,
            "mean_by_stage": self.mean_by_stage(),
            "total_latency": self.percentiles("total"),
        }


def proposal_statistics(raw_counts: Sequence[int], final_counts: Sequence[int]) -> dict[str, Any]:
    """Label-free proposal counting statistics.

    These need no ground truth, so they are always available. They quantify how
    much redundancy the fusion and dedup stages removed, but say nothing about
    whether the survivors are *correct* — that requires annotations.
    """
    if len(raw_counts) != len(final_counts):
        raise ValueError(f"got {len(raw_counts)} raw counts but {len(final_counts)} final counts")
    if not raw_counts:
        return {
            "images": 0,
            "raw_total": 0,
            "final_total": 0,
            "mean_raw_per_image": 0.0,
            "mean_final_per_image": 0.0,
            "duplicates_removed": 0,
            "reduction_ratio": None,
        }

    raw = np.asarray(raw_counts, dtype=np.float64)
    final = np.asarray(final_counts, dtype=np.float64)
    raw_total = float(raw.sum())
    final_total = float(final.sum())
    return {
        "images": len(raw_counts),
        "raw_total": int(raw_total),
        "final_total": int(final_total),
        "mean_raw_per_image": round(float(raw.mean()), 2),
        "mean_final_per_image": round(float(final.mean()), 2),
        "median_final_per_image": round(float(np.median(final)), 2),
        "duplicates_removed": int(raw_total - final_total),
        "reduction_ratio": round(1.0 - (final_total / raw_total), 4) if raw_total > 0 else None,
    }


__all__ = [
    "COCO_IOU_THRESHOLDS",
    "DetectionMetrics",
    "DuplicateMetrics",
    "LatencyStats",
    "association_metrics",
    "average_precision",
    "duplicate_metrics",
    "match_predictions",
    "mean_average_precision",
    "proposal_statistics",
]
