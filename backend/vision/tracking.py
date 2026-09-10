"""Video inventory tracking: YOLO tracker plus appearance re-identification.

This wraps Ultralytics' tracker and feeds its output through
:class:`vision.association.InventoryMemoryBank`, so inventory identity survives
the tracker losing an object. See that module for why tracker IDs alone are not
sufficient.

Division of labour
------------------
The tracker handles frame-to-frame association, which it does cheaply and
precisely using motion and overlap. The memory bank handles identity across
gaps, using appearance. Neither replaces the other: appearance matching every
frame would be wasteful and less precise than IoU when the object has barely
moved, while motion models cannot bridge a ten-second occlusion.

Embedding cost control
----------------------
A full CLIP pass on every detection in every frame would dominate runtime — a
30-second clip at 20 FPS with 10 objects per frame is 6,000 crops. Two
restrictions keep it bounded:

1. Embeddings are computed only for detections that *need* an identity
   decision: an unrecognized tracker ID, or a periodic refresh of a known one.
   A track the tracker is confidently holding needs no appearance check.
2. All crops needing an embedding in a given frame go through the encoder as a
   single batch.

The refresh interval exists so an item's descriptor keeps improving as it is
seen from new angles, rather than being fixed by whatever the first frame
happened to show.

Unlike the image pipeline, this path uses YOLO's **class labels**. Video items
get a majority-voted class name, which the downstream pricing stage uses as a
prior. That mirrors the original behaviour and is preserved.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

import numpy as np

from . import segmentation
from .association import ASSIGN_REID, InventoryItem, InventoryMemoryBank
from .config import VisionConfig
from .detector import load_model
from .embeddings import EmbeddingExtractor

logger = logging.getLogger(__name__)


@dataclass
class FrameDetections:
    """Tracker output for one frame, already filtered of excluded classes."""

    frame_number: int
    track_ids: list[int] = field(default_factory=list)
    boxes: list[tuple[float, float, float, float]] = field(default_factory=list)
    confidences: list[float] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.track_ids)

    @property
    def live_track_ids(self) -> set[int]:
        return set(self.track_ids)


@dataclass
class TrackingResult:
    """Final inventory plus association statistics for a whole video."""

    items: list[InventoryItem]
    frames_processed: int = 0
    frames_read: int = 0
    association: dict[str, Any] = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)

    @property
    def confirmed_count(self) -> int:
        return len(self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "frames_read": self.frames_read,
            "frames_processed": self.frames_processed,
            "confirmed_identities": self.confirmed_count,
            "association": dict(self.association),
            "timings": dict(self.timings),
            "items": [i.to_dict() for i in self.items],
        }


class VideoInventoryTracker:
    """Builds a de-duplicated inventory from a video.

    Args:
        config: Perception configuration. ``tracker_confidence``,
            ``min_frames_to_confirm``, ``max_missing_frames`` and
            ``reid_similarity_threshold`` are the relevant fields.
        model_path: Detector weights. Defaults to a detection (non-seg)
            checkpoint, since the video path uses class labels and boxes but
            not masks.
        embed_refresh_interval: How many frames between descriptor refreshes
            for an already-associated track. Higher is cheaper but adapts more
            slowly to new viewpoints.
    """

    def __init__(
        self,
        config: VisionConfig,
        model_path: str = "yolo11l.pt",
        model: "Any | None" = None,
        embedder: "EmbeddingExtractor | None" = None,
        embed_refresh_interval: int = 15,
    ) -> None:
        if embed_refresh_interval <= 0:
            raise ValueError("embed_refresh_interval must be positive")
        self.config = config
        self.model_path = model_path
        self._model = model
        self._embedder = embedder
        self.embed_refresh_interval = embed_refresh_interval
        self.bank = InventoryMemoryBank(config)
        self._last_embedded_frame: dict[int, int] = {}

    @property
    def model(self) -> Any:
        if self._model is None:
            self._model = load_model(self.model_path)
        return self._model

    @property
    def embedder(self) -> "EmbeddingExtractor | None":
        if not (self.config.enable_embeddings and self.config.enable_reid):
            return None
        if self._embedder is None:
            self._embedder = EmbeddingExtractor(
                model_name=self.config.embedding_model,
                pretrained=self.config.embedding_pretrained,
                device=self.config.embedding_device,
                batch_size=self.config.embedding_batch_size,
            )
        return self._embedder

    def _track_frame(self, frame: np.ndarray, frame_number: int) -> FrameDetections:
        """Run the tracker on one frame and drop excluded classes."""
        results = self.model.track(
            frame,
            persist=True,
            conf=self.config.tracker_confidence,
            iou=self.config.tracker_iou,
            imgsz=min(self.config.scales),
            verbose=False,
        )
        detections = FrameDetections(frame_number=frame_number)
        if not results:
            return detections

        result = results[0]
        boxes = result.boxes
        # Without IDs the tracker has not established any tracks this frame, so
        # there is nothing to associate.
        if boxes is None or boxes.id is None:
            return detections

        xyxy = boxes.xyxy.cpu().numpy()
        ids = boxes.id.cpu().numpy().astype(int)
        confs = boxes.conf.cpu().numpy()
        class_ids = boxes.cls.cpu().numpy().astype(int)
        names = result.names or {}

        for box, track_id, conf, class_id in zip(xyxy, ids, confs, class_ids):
            label = str(names.get(int(class_id), str(class_id)))
            if label in self.config.excluded_classes:
                continue
            detections.track_ids.append(int(track_id))
            detections.boxes.append((float(box[0]), float(box[1]), float(box[2]), float(box[3])))
            detections.confidences.append(float(conf))
            detections.labels.append(label)
        return detections

    def _needs_embedding(self, track_id: int, frame_number: int) -> bool:
        """Whether this detection warrants an appearance embedding.

        True for tracks the bank has never bound (an identity decision is
        needed) and periodically for known tracks (descriptor refresh).
        """
        if track_id not in self.bank._track_to_item:
            return True
        last = self._last_embedded_frame.get(track_id)
        if last is None:
            return True
        return (frame_number - last) >= self.embed_refresh_interval

    def process_frame(self, frame: np.ndarray, frame_number: int) -> FrameDetections:
        """Track, embed selectively, and associate one frame."""
        detections = self._track_frame(frame, frame_number)
        frame_shape = (frame.shape[0], frame.shape[1])

        crops: list["np.ndarray | None"] = [
            segmentation.extract_bbox_crop(frame, box) for box in detections.boxes
        ]

        # Batch every crop that needs an embedding into one encoder call.
        embeddings: list["np.ndarray | None"] = [None] * len(detections)
        embedder = self.embedder
        if embedder is not None and len(detections):
            wanted = [
                i
                for i, track_id in enumerate(detections.track_ids)
                if self._needs_embedding(track_id, frame_number)
                and crops[i] is not None
                and crops[i].size > 0
            ]
            if wanted:
                matrix = embedder.embed_crops([crops[i] for i in wanted])
                for position, index in enumerate(wanted):
                    embeddings[index] = matrix[position]
                    self._last_embedded_frame[detections.track_ids[index]] = frame_number

        live = detections.live_track_ids
        for index, track_id in enumerate(detections.track_ids):
            self.bank.assign(
                track_id=track_id,
                bbox=detections.boxes[index],
                confidence=detections.confidences[index],
                frame_number=frame_number,
                crop=crops[index],
                embedding=embeddings[index],
                label=detections.labels[index],
                frame_shape=frame_shape,
                live_track_ids=live,
            )

        self.bank.mark_missing(live, frame_number)
        return detections

    def process_video(
        self,
        video_path: str,
        target_fps: float = 20.0,
        max_frames: "int | None" = None,
        progress_every: int = 50,
    ) -> TrackingResult:
        """Build an inventory from a video file.

        Args:
            video_path: Readable path or URL accepted by ``cv2.VideoCapture``.
            target_fps: Frames are skipped to approximate this rate. Objects
                persist for many frames, so processing every frame of a 30 FPS
                clip buys almost no new information for 50% more compute.
            max_frames: Optional cap on frames *processed*, for benchmarking.
            progress_every: Log cadence, in processed frames.
        """
        import time

        import cv2

        capture = cv2.VideoCapture(video_path)
        if not capture.isOpened():
            raise ValueError(f"could not open video: {video_path}")

        try:
            source_fps = capture.get(cv2.CAP_PROP_FPS) or target_fps
            frame_skip = max(1, round(source_fps / target_fps)) if source_fps > target_fps else 1

            started = time.perf_counter()
            frames_read = 0
            frames_processed = 0

            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                frames_read += 1
                if (frames_read - 1) % frame_skip != 0:
                    continue

                self.process_frame(frame, frames_processed)
                frames_processed += 1

                if progress_every and frames_processed % progress_every == 0:
                    logger.info(
                        "frame %d: %d inventory identities so far",
                        frames_processed,
                        len(self.bank.items),
                    )
                if max_frames is not None and frames_processed >= max_frames:
                    break

            elapsed = time.perf_counter() - started
        finally:
            capture.release()

        items = sorted(self.bank.confirmed_items(), key=lambda i: i.item_id)
        result = TrackingResult(
            items=items,
            frames_processed=frames_processed,
            frames_read=frames_read,
            association=self.bank.summary(),
            timings={
                "total": round(elapsed, 3),
                "per_frame": round(elapsed / frames_processed, 4) if frames_processed else 0.0,
            },
        )
        logger.info(
            "tracked %d frames -> %d confirmed identities from %d tracker IDs (%d re-id events)",
            frames_processed,
            result.confirmed_count,
            result.association.get("generated_track_ids", 0),
            result.association.get("reid_events", 0),
        )
        return result


__all__ = ["FrameDetections", "TrackingResult", "VideoInventoryTracker"]
