#!/usr/bin/env python3
"""Video association benchmark: tracker IDs alone versus appearance re-identification.

Runs the same video twice — once with ``enable_reid`` off, reproducing the
original tracker-ID-only behaviour, and once with it on — and reports how many
inventory identities each produced.

What this measures, and what it does not
----------------------------------------
Directly observed, no labels needed:

- tracker IDs the tracker generated
- inventory identities each configuration produced
- re-identification events and absorbed ID switches

Fewer identities from the same tracker output means re-identification collapsed
what would have been duplicate inventory entries. That is a real, measured
effect on the output.

**Whether each collapse was correct** is a separate question that needs the true
object count for the video. Pass ``--true-object-count`` if you have counted it
by hand; otherwise correctness metrics are reported as unavailable rather than
inferred from the identity reduction. A drop in identity count is consistent
with both correct de-duplication and incorrect over-merging, and the counts
alone cannot distinguish them.

Usage::

    python -m benchmarks.run_video_benchmark --video backend/testtt.mp4
    python -m benchmarks.run_video_benchmark --video v.mp4 --true-object-count 12
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import Any, Sequence

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.config import config_for_mode
from vision.metrics import association_metrics
from vision.tracking import VideoInventoryTracker

logger = logging.getLogger("video_benchmark")

DEFAULT_RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def run_variant(
    video_path: str,
    enable_reid: bool,
    model_path: str,
    target_fps: float,
    max_frames: "int | None",
    reid_threshold: float,
) -> dict[str, Any]:
    """Track a video with re-identification either on or off."""
    config = config_for_mode(
        "BALANCED",
        enable_reid=enable_reid,
        reid_similarity_threshold=reid_threshold,
    )
    tracker = VideoInventoryTracker(config, model_path=model_path)

    started = time.perf_counter()
    result = tracker.process_video(video_path, target_fps=target_fps, max_frames=max_frames, progress_every=0)
    elapsed = time.perf_counter() - started

    association = dict(result.association)
    association.update(
        {
            "enable_reid": enable_reid,
            "frames_processed": result.frames_processed,
            "frames_read": result.frames_read,
            "wall_clock_s": round(elapsed, 3),
            "seconds_per_frame": round(elapsed / result.frames_processed, 4) if result.frames_processed else None,
        }
    )
    return {
        "association": association,
        "items": [item.to_dict() for item in result.items],
    }


def main(argv: "Sequence[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare tracker-ID-only inventory against appearance re-identification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--video", required=True, help="Video file to process")
    parser.add_argument(
        "--model",
        default=os.environ.get("CR_VIDEO_MODEL_PATH", "yolo11l.pt"),
        help="Detector weights (default: yolo11l.pt, matching production video path)",
    )
    parser.add_argument("--target-fps", type=float, default=10.0, help="Processing frame rate (default: 10)")
    parser.add_argument("--max-frames", type=int, help="Cap on frames processed")
    parser.add_argument(
        "--reid-threshold",
        type=float,
        default=0.90,
        help="Cosine similarity required to re-identify (default: 0.90)",
    )
    parser.add_argument(
        "--true-object-count",
        type=int,
        help="Hand-counted number of distinct physical objects, enabling correctness metrics",
    )
    parser.add_argument("--output", help="Write JSON here (default: benchmarks/results/video_<timestamp>.json)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    if not os.path.isfile(args.video):
        parser.error(f"video not found: {args.video}")

    logger.info("tracking without re-identification (tracker IDs only)")
    without = run_variant(
        args.video, False, args.model, args.target_fps, args.max_frames, args.reid_threshold
    )
    logger.info("tracking with appearance re-identification")
    with_reid = run_variant(
        args.video, True, args.model, args.target_fps, args.max_frames, args.reid_threshold
    )

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "video": os.path.abspath(args.video),
        "model_path": args.model,
        "target_fps": args.target_fps,
        "reid_threshold": args.reid_threshold,
        "without_reid": without["association"],
        "with_reid": with_reid["association"],
        "items_with_reid": with_reid["items"],
        "items_without_reid": without["items"],
        "correctness": association_metrics(
            generated_track_ids=with_reid["association"].get("generated_track_ids", 0),
            inventory_identities=with_reid["association"].get("inventory_identities", 0),
            reid_events=with_reid["association"].get("reid_events", 0),
            id_switches_absorbed=with_reid["association"].get("id_switches_absorbed", 0),
            true_object_count=args.true_object_count,
        ),
        "note": (
            "Identity counts are directly measured. A reduction is consistent with both "
            "correct de-duplication and incorrect over-merging; distinguishing them "
            "requires --true-object-count."
        ),
    }

    output_path = args.output
    if output_path is None:
        os.makedirs(DEFAULT_RESULTS_DIR, exist_ok=True)
        output_path = os.path.join(DEFAULT_RESULTS_DIR, f"video_{time.strftime('%Y%m%d_%H%M%S')}.json")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    print(f"\nWrote results to {output_path}\n")

    b = payload["without_reid"]
    c = payload["with_reid"]
    print(f"{'metric':<28} {'tracker only':>14} {'with re-id':>14}")
    print("-" * 58)
    for key in (
        "frames_processed",
        "generated_track_ids",
        "inventory_identities",
        "confirmed_identities",
        "reid_events",
        "id_switches_absorbed",
        "wall_clock_s",
    ):
        print(f"{key:<28} {str(b.get(key, 'n/a')):>14} {str(c.get(key, 'n/a')):>14}")

    correctness = payload["correctness"]
    if correctness.get("true_object_count") is None:
        print(
            "\nCorrectness metrics unavailable: pass --true-object-count with a "
            "hand-counted\nnumber of distinct objects to compute identity inflation "
            "and duplicate entries."
        )
    else:
        print(f"\ntrue objects: {correctness['true_object_count']}")
        print(f"  identity inflation (with re-id):   {correctness['identity_inflation']}")
        print(f"  identity inflation (tracker only): {correctness['tracker_only_inflation']}")
        print(f"  duplicate inventory entries:       {correctness['duplicate_entries']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
