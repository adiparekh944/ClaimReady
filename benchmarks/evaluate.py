#!/usr/bin/env python3
"""Ground-truth evaluation of benchmark output.

This repository ships **no annotated dataset**, so nothing here can produce
detection accuracy numbers out of the box. The framework exists so that
annotations can be added later without writing new code, and it fails loudly
rather than inventing numbers when labels are absent.

Annotation format
-----------------
A single JSON file. Keys are image paths, either absolute or relative to the
annotation file's directory:

.. code-block:: json

    {
      "images": {
        "frames/frame_00000.jpg": {
          "objects": [
            {"bbox": [120, 88, 340, 402], "label": "sofa"},
            {"bbox": [512, 300, 588, 366], "label": "lamp", "small": true}
          ]
        }
      }
    }

``bbox`` is ``[x1, y1, x2, y2]`` in original-image pixels. ``label`` is
optional and unused for class-agnostic scoring — it is recorded for readability
only. ``small`` is optional; when omitted, an object is treated as small if it
covers less than ``--small-frac`` of the frame, so small-object recall can be
reported without hand-tagging.

Optional duplicate groupings, for scoring the deduplication decision directly:

.. code-block:: json

    "duplicate_groups": [[0, 3], [5, 6, 7]]

Each group lists indices into that image's ``objects`` array that refer to the
same physical item. Absent groupings simply skip duplicate metrics.

How proposals are scored
------------------------
Detection here is class-agnostic — the pipeline deliberately discards YOLO's
labels — so matching is by geometry alone and predicted labels are ignored.
Precision is therefore expected to be low by design: the pipeline is tuned for
recall and a downstream multimodal model rejects false positives. Recall and
small-object recall are the meaningful numbers.

Usage::

    python -m benchmarks.evaluate --results benchmarks/results/latest.json \
        --annotations path/to/annotations.json
    python -m benchmarks.evaluate --results r.json --make-template ann.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Sequence

# The vision package lives under backend/ so it falls inside the Docker
# build context (see docs/computer_vision_pipeline.md).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "backend"))
sys.path.insert(0, _REPO_ROOT)

from vision import geometry
from vision.metrics import (
    COCO_IOU_THRESHOLDS,
    duplicate_metrics,
    match_predictions,
    mean_average_precision,
)

logger = logging.getLogger("cv_evaluate")

DEFAULT_SMALL_FRAC = 0.01


class AnnotationsMissing(RuntimeError):
    """Raised when accuracy metrics are requested without usable labels."""


def load_annotations(path: str) -> dict[str, Any]:
    """Read and normalize an annotation file.

    Image keys are resolved relative to the annotation file so a set of
    annotations stays portable alongside its images.
    """
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    images = payload.get("images")
    if not isinstance(images, dict) or not images:
        raise AnnotationsMissing(f"{path} contains no 'images' mapping")

    base = os.path.dirname(os.path.abspath(path))
    normalized: dict[str, Any] = {}
    for key, value in images.items():
        resolved = key if os.path.isabs(key) else os.path.normpath(os.path.join(base, key))
        normalized[resolved] = value
        # Also index by basename, so a results file recorded with a different
        # relative prefix still matches.
        normalized.setdefault(os.path.basename(key), value)
    return normalized


def _lookup(annotations: dict[str, Any], image_path: str) -> "dict[str, Any] | None":
    """Find an image's annotation by absolute path, then by basename."""
    absolute = os.path.abspath(image_path)
    for candidate in (absolute, image_path, os.path.basename(image_path)):
        if candidate in annotations:
            return annotations[candidate]
    return None


def make_template(results_path: str, output_path: str, small_frac: float = DEFAULT_SMALL_FRAC) -> str:
    """Write an empty annotation skeleton covering a results file's images.

    Pre-populating the image list is the tedious part of labelling, so this
    produces a file that only needs boxes filled in.
    """
    with open(results_path, "r", encoding="utf-8") as handle:
        results = json.load(handle)

    images = results.get("images", [])
    if not images:
        raise ValueError(f"{results_path} lists no images")

    template = {
        "_instructions": (
            "Fill in 'objects' for each image with [x1, y1, x2, y2] boxes in original "
            "pixel coordinates. 'label' is optional and unused for class-agnostic "
            "scoring. Mark 'small': true to force small-object treatment, otherwise "
            f"objects under {small_frac:.1%} of the frame are treated as small. "
            "Optionally add 'duplicate_groups': [[0, 3]] listing indices of objects "
            "that are the same physical item."
        ),
        "small_frac": small_frac,
        "images": {path: {"objects": [], "duplicate_groups": []} for path in images},
    }

    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(template, handle, indent=2)
    return output_path


def _is_small(obj: dict[str, Any], frame_area: float, small_frac: float) -> bool:
    if "small" in obj:
        return bool(obj["small"])
    if frame_area <= 0:
        return False
    return geometry.box_area(obj["bbox"]) < frame_area * small_frac


def evaluate_configuration(
    payload: dict[str, Any],
    annotations: dict[str, Any],
    iou_threshold: float = 0.5,
    small_frac: float = DEFAULT_SMALL_FRAC,
    compute_map: bool = True,
) -> dict[str, Any]:
    """Score one configuration's per-image records against annotations."""
    records = payload.get("records", [])

    total_tp = total_fp = total_fn = 0
    small_total = small_matched = 0
    matched_images = 0
    skipped: list[str] = []
    per_image: list[dict[str, Any]] = []
    all_predictions: list[Sequence[float]] = []
    all_scores: list[float] = []
    all_truth: list[Sequence[float]] = []
    duplicate_tp = duplicate_fp = duplicate_fn = duplicate_pairs = 0
    duplicate_images = 0

    for record in records:
        image_path = record.get("path", "")
        annotation = _lookup(annotations, image_path)
        if annotation is None:
            skipped.append(image_path)
            continue

        objects = annotation.get("objects", [])
        if not objects:
            skipped.append(image_path)
            continue

        truth_boxes = [obj["bbox"] for obj in objects]
        proposals = record.get("proposals", [])
        predicted_boxes = [p["bbox"] for p in proposals]
        scores = [float(p.get("confidence", 0.0)) for p in proposals]

        assignment, metrics = match_predictions(predicted_boxes, truth_boxes, iou_threshold, scores)
        total_tp += metrics.true_positives
        total_fp += metrics.false_positives
        total_fn += metrics.false_negatives
        matched_images += 1

        frame_area = float(record.get("width", 0)) * float(record.get("height", 0))
        claimed = {gt for gt in assignment if gt >= 0}
        for index, obj in enumerate(objects):
            if _is_small(obj, frame_area, small_frac):
                small_total += 1
                if index in claimed:
                    small_matched += 1

        # Pooling across images is only valid for mAP because matching is
        # per-image; the boxes themselves are never compared across images.
        if compute_map:
            all_predictions.extend(predicted_boxes)
            all_scores.extend(scores)
            all_truth.extend(truth_boxes)

        groups = annotation.get("duplicate_groups") or []
        if groups:
            # Predicted grouping: proposals matched to the same ground-truth
            # object were treated as duplicates of each other.
            by_truth: dict[int, list[int]] = {}
            for pred_index, gt_index in enumerate(assignment):
                if gt_index >= 0:
                    by_truth.setdefault(gt_index, []).append(pred_index)
            predicted_groups = [members for members in by_truth.values() if len(members) > 1]
            dup = duplicate_metrics(predicted_groups, groups, num_items=len(predicted_boxes))
            duplicate_tp += dup.true_positives
            duplicate_fp += dup.false_positives
            duplicate_fn += dup.false_negatives
            duplicate_pairs += dup.total_pairs
            duplicate_images += 1

        per_image.append(
            {
                "path": image_path,
                **metrics.to_dict(),
                "final_count": record.get("final_count"),
                "raw_count": record.get("raw_count"),
            }
        )

    if matched_images == 0:
        raise AnnotationsMissing(
            "no benchmark image matched an annotation entry; "
            "check that annotation keys match the paths in the results file"
        )

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    out: dict[str, Any] = {
        "name": payload.get("name"),
        "images_evaluated": matched_images,
        "images_skipped": len(skipped),
        "skipped_paths": skipped[:20],
        "iou_threshold": iou_threshold,
        "true_positives": total_tp,
        "false_positives": total_fp,
        "false_negatives": total_fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "objects_evaluated": total_tp + total_fn,
        "small_objects": small_total,
        "small_objects_matched": small_matched,
        "small_object_recall": round(small_matched / small_total, 4) if small_total else None,
        "per_image": per_image,
    }

    if compute_map and all_truth:
        out["map"] = mean_average_precision(all_predictions, all_truth, all_scores, COCO_IOU_THRESHOLDS)

    if duplicate_images:
        precision_d = duplicate_tp / (duplicate_tp + duplicate_fp) if (duplicate_tp + duplicate_fp) else 0.0
        recall_d = duplicate_tp / (duplicate_tp + duplicate_fn) if (duplicate_tp + duplicate_fn) else 0.0
        out["duplicates"] = {
            "images_with_groupings": duplicate_images,
            "duplicate_precision": round(precision_d, 4),
            "duplicate_recall": round(recall_d, 4),
            "duplicate_f1": round(
                (2 * precision_d * recall_d / (precision_d + recall_d)) if (precision_d + recall_d) else 0.0,
                4,
            ),
            "true_positives": duplicate_tp,
            "false_positives": duplicate_fp,
            "false_negatives": duplicate_fn,
            "total_pairs": duplicate_pairs,
        }
    else:
        out["duplicates"] = None

    return out


def main(argv: "Sequence[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(
        description="Score benchmark output against ground-truth annotations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--results", required=True, help="Benchmark JSON from run_cv_benchmark")
    parser.add_argument("--annotations", help="Ground-truth annotation JSON")
    parser.add_argument("--make-template", help="Write an empty annotation template here and exit")
    parser.add_argument("--iou", type=float, default=0.5, help="Matching IoU threshold (default: 0.5)")
    parser.add_argument(
        "--small-frac",
        type=float,
        default=DEFAULT_SMALL_FRAC,
        help=f"Frame-area fraction below which an object counts as small (default: {DEFAULT_SMALL_FRAC})",
    )
    parser.add_argument("--no-map", action="store_true", help="Skip mAP (it is the slow part)")
    parser.add_argument("--output", help="Write evaluation JSON here")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.make_template:
        path = make_template(args.results, args.make_template, args.small_frac)
        print(f"Wrote annotation template to {path}")
        print("Fill in the 'objects' arrays, then re-run with --annotations.")
        return 0

    if not args.annotations:
        print(
            "No --annotations supplied.\n\n"
            "This repository ships no annotated dataset, so precision, recall and mAP\n"
            "cannot be computed. Counting and latency metrics are already in the\n"
            "benchmark results file and need no labels.\n\n"
            "To add annotations:\n"
            f"  python -m benchmarks.evaluate --results {args.results} \\\n"
            "      --make-template benchmarks/data/annotations.json\n"
            "  # fill in the boxes, then\n"
            f"  python -m benchmarks.evaluate --results {args.results} \\\n"
            "      --annotations benchmarks/data/annotations.json\n",
            file=sys.stderr,
        )
        return 2

    with open(args.results, "r", encoding="utf-8") as handle:
        results = json.load(handle)

    annotations = load_annotations(args.annotations)

    evaluation: dict[str, Any] = {
        "results_file": os.path.abspath(args.results),
        "annotations_file": os.path.abspath(args.annotations),
        "iou_threshold": args.iou,
        "small_frac": args.small_frac,
        "configurations": {},
    }

    for name, payload in results.get("configurations", {}).items():
        try:
            evaluation["configurations"][name] = evaluate_configuration(
                payload,
                annotations,
                iou_threshold=args.iou,
                small_frac=args.small_frac,
                compute_map=not args.no_map,
            )
        except AnnotationsMissing as exc:
            logger.error("%s: %s", name, exc)
            evaluation["configurations"][name] = {"name": name, "error": str(exc)}

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(evaluation, handle, indent=2)
        print(f"Wrote evaluation to {args.output}")

    header = f"{'configuration':<20} {'imgs':>5} {'objs':>5} {'prec':>7} {'recall':>7} {'F1':>7} {'mAP50':>7} {'smRec':>7}"
    print(header)
    print("-" * len(header))
    for name, payload in evaluation["configurations"].items():
        if "error" in payload:
            print(f"{name:<20} {'ERROR: ' + payload['error'][:50]}")
            continue
        small = payload.get("small_object_recall")
        map50 = (payload.get("map") or {}).get("map@0.50")
        print(
            f"{name:<20} "
            f"{payload['images_evaluated']:>5} "
            f"{payload['objects_evaluated']:>5} "
            f"{payload['precision']:>7.3f} "
            f"{payload['recall']:>7.3f} "
            f"{payload['f1']:>7.3f} "
            f"{(f'{map50:.3f}' if map50 is not None else 'n/a'):>7} "
            f"{(f'{small:.3f}' if small is not None else 'n/a'):>7}"
        )
    print(
        "\nNote: this pipeline is class-agnostic and tuned for recall, so low precision\n"
        "is expected by design. Recall and small-object recall are the meaningful figures."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
