"""Inventory identity association and appearance re-identification for video.

The problem with trusting tracker IDs
-------------------------------------
The original video path used the Ultralytics tracker's ``track_id`` directly as
the inventory identity: an object counted once it had been seen in 3 frames, and
was forgotten after 5 consecutive misses. That makes inventory correctness
entirely dependent on tracker continuity, and motion-model trackers break
continuity routinely:

- **Occlusion.** Someone walks in front of the sofa; the track dies, and the
  sofa gets a fresh ID and a second inventory entry.
- **Re-entry.** The user pans across a room and pans back. The old track expired
  long ago, so every item is counted twice.
- **Fast motion.** A phone-held pan moves objects far between frames; IoU-based
  association fails and the ID switches mid-object.

Every one of these inflates the claim, which is worse than missing an item: it
makes the total indefensible.

What this module adds
---------------------
An identity layer above the tracker. Each inventory item keeps an appearance
descriptor — the mean CLIP embedding of the crops seen for it — and when a new
tracker ID appears, it is matched against the gallery of known items by cosine
similarity before being admitted as a new object.

So the tracker still does what it is good at (frame-to-frame continuity, cheap
and precise), while identity over longer gaps is decided by appearance, which
survives occlusion and re-entry. This is the standard tracking-by-appearance
arrangement used by DeepSORT and its descendants, applied to inventory identity
rather than to per-frame association.

Descriptor update
-----------------
An item's descriptor is the running mean of its observed embeddings,
renormalized to unit length. A mean is more robust than keeping only the first
or the best embedding: it averages out viewpoint and lighting variation, so
matching improves as an object is seen from more angles. Renormalizing after
each update keeps cosine similarity comparable to a single-view embedding.

Guards against over-merging
---------------------------
Appearance matching is the mechanism that creates duplicates *in the other
direction* — two genuinely distinct but identical objects (a pair of matching
dining chairs) look the same to CLIP. Two guards apply:

1. A high default similarity threshold (``reid_similarity_threshold``).
2. Items currently *alive* in the same frame are never merged, because two
   things visible simultaneously cannot be one object. This is a hard
   constraint from physics, not a tunable, and it is what makes appearance
   matching safe to use at all.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from .config import VisionConfig
from .embeddings import l2_normalize

logger = logging.getLogger(__name__)

# Why a detection was assigned to an item.
ASSIGN_TRACKER = "tracker_id"
ASSIGN_REID = "reid_embedding"
ASSIGN_NEW = "new_item"


@dataclass
class CropQuality:
    """Component scores for one candidate crop, plus the combined value.

    Kept as a record rather than a bare float so the benchmark can report which
    term drove best-frame selection, and so a poor choice is explainable.
    """

    confidence: float
    area_frac: float
    sharpness: float
    centrality: float
    score: float

    def to_dict(self) -> dict[str, float]:
        return {
            "confidence": round(self.confidence, 4),
            "area_frac": round(self.area_frac, 4),
            "sharpness": round(self.sharpness, 2),
            "centrality": round(self.centrality, 4),
            "score": round(self.score, 4),
        }


def score_crop_quality(
    crop: "np.ndarray | None",
    bbox: Sequence[float],
    confidence: float,
    frame_shape: tuple[int, int],
    config: VisionConfig,
) -> CropQuality:
    """Score how good a crop is as the representative image for an item.

    Four terms, each normalized to roughly ``[0, 1]`` before weighting:

    **Confidence** — the detector's own score.

    **Area fraction** — bbox area over frame area, square-rooted. The square
    root is deliberate: raw area fraction is dominated by a handful of huge
    objects, so linearly weighting it would make every item's best frame the one
    where the camera got closest, even if badly blurred. The root compresses
    that range.

    **Sharpness** — Laplacian variance of the crop, mapped through
    ``v / (v + threshold)``. This saturating form is used instead of a hard
    cutoff so that a slightly soft crop is merely penalized rather than
    disqualified — useful when every frame of an object is soft.

    **Centrality** — how far the box centre sits from the frame edge, as a
    fraction of the half-dimension. Objects at the frame border are usually
    clipped, and a clipped crop is a poor thumbnail even at high confidence.
    """
    frame_h, frame_w = frame_shape
    frame_area = float(max(1, frame_h * frame_w))

    x1, y1, x2, y2 = (float(v) for v in bbox[:4])
    box_area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_frac = float(np.sqrt(min(1.0, box_area / frame_area)))

    if crop is not None and crop.size > 0:
        from .preprocessing import blur_variance_of

        raw_sharpness = blur_variance_of(crop)
    else:
        raw_sharpness = 0.0
    sharpness_norm = raw_sharpness / (raw_sharpness + config.blur_variance_threshold + 1e-9)

    center_x = (x1 + x2) / 2.0
    center_y = (y1 + y2) / 2.0
    half_w = frame_w / 2.0
    half_h = frame_h / 2.0
    # 1.0 at the exact centre, 0.0 at any edge.
    dx = 1.0 - min(1.0, abs(center_x - half_w) / max(1e-9, half_w))
    dy = 1.0 - min(1.0, abs(center_y - half_h) / max(1e-9, half_h))
    centrality = float(min(dx, dy))

    score = (
        config.quality_weight_confidence * float(np.clip(confidence, 0.0, 1.0))
        + config.quality_weight_area * area_frac
        + config.quality_weight_sharpness * sharpness_norm
        + config.quality_weight_centrality * centrality
    )
    return CropQuality(
        confidence=float(confidence),
        area_frac=area_frac,
        sharpness=float(raw_sharpness),
        centrality=centrality,
        score=float(score),
    )


@dataclass
class InventoryItem:
    """One physical object, tracked across an entire video.

    An item may span several tracker IDs — that is the whole point. Every ID it
    has ever been matched to is recorded in ``track_ids``, and the count of
    additional IDs beyond the first is the observable ID-switch recovery.
    """

    item_id: int
    label: str = ""
    track_ids: list[int] = field(default_factory=list)
    last_bbox: "tuple[float, float, float, float] | None" = None
    last_seen_frame: int = -1
    first_seen_frame: int = -1
    frames_seen: int = 0
    consecutive_misses: int = 0
    confirmed: bool = False
    best_crop: "np.ndarray | None" = None
    best_quality: "CropQuality | None" = None
    best_frame: int = -1
    best_confidence: float = 0.0
    descriptor: "np.ndarray | None" = None
    embedding_count: int = 0
    label_votes: dict[str, int] = field(default_factory=dict)
    reid_events: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id_switches_absorbed(self) -> int:
        """Extra tracker IDs this item absorbed, i.e. recovered ID switches."""
        return max(0, len(self.track_ids) - 1)

    @property
    def dominant_label(self) -> str:
        """Most frequently voted class label across observations.

        Majority voting rather than the first or last label, because a
        detector's per-frame class prediction is noisy and a single bad frame
        should not name the item.
        """
        if not self.label_votes:
            return self.label
        return max(self.label_votes.items(), key=lambda kv: kv[1])[0]

    def observe_label(self, label: str) -> None:
        if label:
            self.label_votes[label] = self.label_votes.get(label, 0) + 1

    def update_descriptor(self, embedding: "np.ndarray | None") -> None:
        """Fold a new embedding into the running mean descriptor."""
        if embedding is None:
            return
        vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
        if not np.any(vector):
            return
        if self.descriptor is None:
            self.descriptor = l2_normalize(vector.reshape(1, -1))[0]
            self.embedding_count = 1
            return
        # Incremental mean, then renormalize so the descriptor stays on the
        # unit sphere and remains comparable with single-view embeddings.
        total = self.descriptor * self.embedding_count + vector
        self.embedding_count += 1
        self.descriptor = l2_normalize((total / self.embedding_count).reshape(1, -1))[0]

    def consider_crop(
        self,
        crop: "np.ndarray | None",
        quality: CropQuality,
        frame_number: int,
    ) -> bool:
        """Keep this crop if it scores better than the current best."""
        if crop is None or crop.size == 0:
            return False
        if self.best_quality is None or quality.score > self.best_quality.score:
            self.best_crop = crop
            self.best_quality = quality
            self.best_frame = frame_number
            self.best_confidence = quality.confidence
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "label": self.dominant_label,
            "track_ids": list(self.track_ids),
            "id_switches_absorbed": self.id_switches_absorbed,
            "reid_events": self.reid_events,
            "frames_seen": self.frames_seen,
            "first_seen_frame": self.first_seen_frame,
            "last_seen_frame": self.last_seen_frame,
            "confirmed": self.confirmed,
            "best_frame": self.best_frame,
            "best_confidence": round(self.best_confidence, 4),
            "best_quality": self.best_quality.to_dict() if self.best_quality else None,
            "bbox": [round(float(v), 2) for v in self.last_bbox] if self.last_bbox else None,
            "has_descriptor": self.descriptor is not None,
        }


class InventoryMemoryBank:
    """Maps tracker detections onto stable inventory identities.

    Association order per detection:

    1. **Known tracker ID.** If this ``track_id`` is already bound to an item,
       use it. Cheap and unambiguous while the tracker holds.
    2. **Appearance re-identification.** Otherwise compare the detection's
       embedding against the descriptors of items not currently visible. Above
       ``reid_similarity_threshold``, rebind: the tracker lost the object and
       gave it a new ID.
    3. **New item.** No match, so admit a new identity.

    Step 2 is skipped when embeddings are unavailable, in which case the
    behaviour reduces to the original tracker-ID semantics rather than guessing.
    """

    def __init__(self, config: VisionConfig) -> None:
        self.config = config
        self.items: dict[int, InventoryItem] = {}
        self._track_to_item: dict[int, int] = {}
        self._next_item_id = 0
        self.stats: dict[str, int] = {
            "detections": 0,
            "tracker_hits": 0,
            "reid_hits": 0,
            "new_items": 0,
            "reid_blocked_coexisting": 0,
            "reid_attempts": 0,
            "reid_attempts_with_candidates": 0,
        }
        # Best-match similarity for every re-identification attempt that had a
        # non-empty gallery, whether or not it cleared the threshold.
        #
        # This exists because a threshold that never fires is indistinguishable
        # from a feature that does not work, and both look like "0 re-id events"
        # in the output. Recording the distribution separates the two: it shows
        # the mechanism ran, how close it came, and where the threshold would
        # need to sit to change the outcome. That turns threshold choice into a
        # measurement instead of a guess.
        self.reid_similarity_samples: list[float] = []

    # -- gallery ----------------------------------------------------------

    def _reid_candidates(self, frame_number: int, live_track_ids: "set[int] | None" = None) -> list[InventoryItem]:
        """Items eligible for appearance re-identification.

        An item is excluded when it is currently visible — either because it
        was already updated in this frame, or because one of its tracker IDs is
        in ``live_track_ids``. Two objects visible at the same instant are
        necessarily distinct, so this is a physical-impossibility constraint
        rather than a tunable threshold, and it is the main thing preventing a
        row of identical chairs from collapsing into one inventory entry.

        Args:
            frame_number: Frame being processed.
            live_track_ids: Every tracker ID present in this frame, not just
                the one being assigned. Callers must pass the full set;
                omitting it weakens the coexistence guard to only those items
                already updated this frame.
        """
        live = live_track_ids or set()
        candidates: list[InventoryItem] = []
        for item in self.items.values():
            if item.descriptor is None:
                continue
            if item.last_seen_frame >= frame_number or any(t in live for t in item.track_ids):
                # Visible right now, so it cannot be the object we are trying
                # to re-identify.
                self.stats["reid_blocked_coexisting"] += 1
                continue
            candidates.append(item)

        if len(candidates) > self.config.reid_max_gallery_size:
            # Prefer recently seen items: an object off-screen for a few
            # seconds is far more likely to return than one from minutes ago.
            candidates.sort(key=lambda i: i.last_seen_frame, reverse=True)
            candidates = candidates[: self.config.reid_max_gallery_size]
        return candidates

    def _match_by_appearance(
        self,
        embedding: "np.ndarray | None",
        frame_number: int,
        live_track_ids: "set[int] | None" = None,
    ) -> "tuple[InventoryItem | None, float]":
        """Best gallery match for an embedding, if it clears the threshold.

        Similarity against the whole gallery is one matrix-vector product
        rather than a Python loop over items.
        """
        if embedding is None or not self.config.enable_reid:
            return None, 0.0

        self.stats["reid_attempts"] += 1
        candidates = self._reid_candidates(frame_number, live_track_ids)
        if not candidates:
            return None, 0.0

        gallery = np.stack([c.descriptor for c in candidates]).astype(np.float32)
        query = np.asarray(embedding, dtype=np.float32).reshape(-1)
        norm = float(np.linalg.norm(query))
        if norm == 0.0:
            return None, 0.0
        similarities = gallery @ (query / norm)

        best_index = int(np.argmax(similarities))
        best_score = float(similarities[best_index])

        self.stats["reid_attempts_with_candidates"] += 1
        if len(self.reid_similarity_samples) < 10_000:
            self.reid_similarity_samples.append(best_score)

        if best_score >= self.config.reid_similarity_threshold:
            return candidates[best_index], best_score
        return None, best_score

    # -- association ------------------------------------------------------

    def assign(
        self,
        track_id: int,
        bbox: Sequence[float],
        confidence: float,
        frame_number: int,
        crop: "np.ndarray | None" = None,
        embedding: "np.ndarray | None" = None,
        label: str = "",
        frame_shape: "tuple[int, int] | None" = None,
        live_track_ids: "set[int] | None" = None,
    ) -> tuple[InventoryItem, str]:
        """Bind one detection to an inventory item.

        Returns the item and how it was matched (one of the ``ASSIGN_*``
        constants), so the caller can count re-identification events.
        """
        self.stats["detections"] += 1

        item: "InventoryItem | None" = None
        reason = ASSIGN_NEW

        existing_item_id = self._track_to_item.get(track_id)
        if existing_item_id is not None:
            item = self.items.get(existing_item_id)
            reason = ASSIGN_TRACKER
            self.stats["tracker_hits"] += 1

        if item is None:
            matched, score = self._match_by_appearance(embedding, frame_number, live_track_ids)
            if matched is not None:
                item = matched
                reason = ASSIGN_REID
                item.reid_events += 1
                item.metadata.setdefault("reid_scores", []).append(round(score, 4))
                self._track_to_item[track_id] = item.item_id
                if track_id not in item.track_ids:
                    item.track_ids.append(track_id)
                self.stats["reid_hits"] += 1
                logger.debug(
                    "re-identified track %d as item %d (cosine %.3f) at frame %d",
                    track_id,
                    item.item_id,
                    score,
                    frame_number,
                )

        if item is None:
            item = InventoryItem(
                item_id=self._next_item_id,
                label=label,
                track_ids=[track_id],
                first_seen_frame=frame_number,
            )
            self.items[item.item_id] = item
            self._track_to_item[track_id] = item.item_id
            self._next_item_id += 1
            self.stats["new_items"] += 1
            reason = ASSIGN_NEW

        item.frames_seen += 1
        item.consecutive_misses = 0
        item.last_bbox = tuple(float(v) for v in bbox[:4])  # type: ignore[assignment]
        item.last_seen_frame = frame_number
        item.observe_label(label)
        item.update_descriptor(embedding)

        # Temporal hysteresis: an item is only admitted to the inventory after
        # being seen in enough frames. A single-frame detection at a 0.55
        # threshold is as likely to be a false positive as a real object.
        if not item.confirmed and item.frames_seen >= self.config.min_frames_to_confirm:
            item.confirmed = True

        if crop is not None and frame_shape is not None:
            quality = score_crop_quality(crop, bbox, confidence, frame_shape, self.config)
            item.consider_crop(crop, quality, frame_number)

        return item, reason

    def mark_missing(self, seen_track_ids: "set[int]", frame_number: int) -> list[int]:
        """Age out items not seen this frame; return those that went stale.

        A stale item is *not* deleted. Its descriptor stays in the gallery
        precisely so it can be re-identified later — dropping it is what caused
        the pan-away-and-return duplicate in the original implementation. Only
        the tracker-ID binding is released, since that ID may be reused for a
        different object.
        """
        stale: list[int] = []
        for item in self.items.values():
            if item.last_seen_frame >= frame_number:
                continue
            if any(t in seen_track_ids for t in item.track_ids):
                continue
            item.consecutive_misses += 1
            if item.consecutive_misses == self.config.max_missing_frames + 1:
                stale.append(item.item_id)
                for track_id in item.track_ids:
                    self._track_to_item.pop(track_id, None)
        return stale

    # -- results ----------------------------------------------------------

    def confirmed_items(self) -> list[InventoryItem]:
        """Inventory items that cleared the confirmation threshold."""
        return [i for i in self.items.values() if i.confirmed]

    def reid_similarity_distribution(self) -> dict[str, Any]:
        """Percentiles of observed best-match similarity, plus a threshold sweep.

        The sweep reports how many attempts *would* have merged at each
        candidate threshold. Without it, a run with zero re-identification
        events gives no information about whether the threshold is too strict
        or the video simply contains no re-entries.
        """
        samples = self.reid_similarity_samples
        if not samples:
            return {
                "samples": 0,
                "note": "no re-identification attempt had a non-empty gallery",
            }

        array = np.asarray(samples, dtype=np.float64)
        sweep = {
            f"{threshold:.2f}": int((array >= threshold).sum())
            for threshold in (0.70, 0.75, 0.80, 0.85, 0.90, 0.95)
        }
        return {
            "samples": int(array.size),
            "min": round(float(array.min()), 4),
            "p50": round(float(np.percentile(array, 50)), 4),
            "p90": round(float(np.percentile(array, 90)), 4),
            "max": round(float(array.max()), 4),
            "configured_threshold": self.config.reid_similarity_threshold,
            "would_match_at_threshold": sweep,
        }

    def summary(self) -> dict[str, Any]:
        """Association counters, for benchmarking video association quality."""
        confirmed = self.confirmed_items()
        distinct_track_ids = {t for item in self.items.values() for t in item.track_ids}
        return {
            "generated_track_ids": len(distinct_track_ids),
            "inventory_identities": len(self.items),
            "confirmed_identities": len(confirmed),
            "reid_events": sum(i.reid_events for i in self.items.values()),
            "id_switches_absorbed": sum(i.id_switches_absorbed for i in self.items.values()),
            "items_with_descriptor": sum(1 for i in self.items.values() if i.descriptor is not None),
            "reid_similarity": self.reid_similarity_distribution(),
            **self.stats,
        }


__all__ = [
    "ASSIGN_NEW",
    "ASSIGN_REID",
    "ASSIGN_TRACKER",
    "CropQuality",
    "InventoryItem",
    "InventoryMemoryBank",
    "score_crop_quality",
]
