#!/usr/bin/env python3
"""Ablation benchmark for the ClaimReady perception pipeline.

Runs named configurations over a directory of images and records proposal
counts and a per-stage latency breakdown for each. Results are written as JSON
for :mod:`benchmarks.resume_metrics` to diff.

Configurations
--------------
``A_baseline``
    The original pipeline: single scale, two low-confidence passes, greedy IoU
    suppression. No fusion, masks or appearance. This is the control.
``B_multiscale_wbf``
    Multi-scale detection with weighted box fusion, still geometry-only.
    Isolates what multi-scale plus WBF contribute.
``C_embeddings``
    Adds CLIP appearance embeddings to the deduplication decision.
``D_full``
    Everything: ACCURATE scales, tiled inference, masks, embeddings.

Comparing A to B isolates fusion, B to C isolates appearance, and C to D
isolates tiling and the third scale.

What this measures without annotations
--------------------------------------
Proposal counts, reduction ratios and latency need no labels and are always
reported. Precision, recall and mAP require ground truth; supply it with
``--annotations`` and :mod:`benchmarks.evaluate` will compute them. Without
labels those fields are reported as unavailable rather than estimated.

Usage::

    python -m benchmarks.run_cv_benchmark --images path/to/images
    python -m benchmarks.run_cv_benchmark --images imgs --configs A_baseline D_full
    python -m benchmarks.run_cv_benchmark --images imgs --visualize --limit 5
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

# Allow `python benchmarks/run_cv_benchmark.py` as well as `-m`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np

from vision.config import EmbeddingCropMode, PipelineMode, VisionConfig, config_for_mode
from vision.metrics import LatencyStats, proposal_statistics
from vision.pipeline import PipelineResult, VisionPipeline

logger = logging.getLogger("cv_benchmark")

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff")

DEFAULT_RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


@dataclass
class BenchmarkConfig:
    """One named ablation configuration."""

    name: str
    description: str
    mode: PipelineMode
    overrides: dict[str, Any] = field(default_factory=dict)
    # When set, the pipeline's baseline path is used instead of the enhanced
    # one, so the control is the real original algorithm rather than an
    # approximation of it.
    use_baseline_path: bool = False

    def build(self, model_path: str) -> VisionConfig:
        overrides = dict(self.overrides)
        overrides["model_path"] = model_path
        return config_for_mode(self.mode, **overrides)


def default_configs() -> dict[str, BenchmarkConfig]:
    """The four-way ablation described in the module docstring."""
    return {
        "A_baseline": BenchmarkConfig(
            name="A_baseline",
            description="Original pipeline: single scale, greedy IoU suppression, no fusion/masks/embeddings",
            mode=PipelineMode.FAST,
            use_baseline_path=True,
        ),
        "B_multiscale_wbf": BenchmarkConfig(
            name="B_multiscale_wbf",
            description="Multi-scale proposals + weighted box fusion, geometry-only dedup",
            mode=PipelineMode.BALANCED,
            overrides={
                "enable_embeddings": False,
                "enable_segmentation": False,
                "enable_fragment_union": False,
            },
        ),
        "C_embeddings": BenchmarkConfig(
            name="C_embeddings",
            description="B plus CLIP appearance embeddings in the dedup decision",
            mode=PipelineMode.BALANCED,
            overrides={"enable_embeddings": True, "enable_segmentation": False},
        ),
        "D_full": BenchmarkConfig(
            name="D_full",
            description="Full pipeline: ACCURATE scales, tiled inference, masks, embeddings",
            mode=PipelineMode.ACCURATE,
            overrides={},
        ),
    }


def extra_configs() -> dict[str, BenchmarkConfig]:
    """Optional configurations for focused questions.

    ``E_masked_crops`` and ``F_bbox_crops`` answer Phase 6's question of
    whether embedding masked crops beats embedding plain bbox crops. They are
    opt-in because they double runtime without adding to the main ablation.
    """
    return {
        "E_masked_crops": BenchmarkConfig(
            name="E_masked_crops",
            description="BALANCED with masked-crop embeddings (background suppressed)",
            mode=PipelineMode.BALANCED,
            overrides={"embedding_crop_mode": EmbeddingCropMode.MASKED},
        ),
        "F_bbox_crops": BenchmarkConfig(
            name="F_bbox_crops",
            description="BALANCED with plain bbox-crop embeddings",
            mode=PipelineMode.BALANCED,
            overrides={"embedding_crop_mode": EmbeddingCropMode.BBOX},
        ),
        "G_both_crops": BenchmarkConfig(
            name="G_both_crops",
            description="BALANCED averaging bbox and masked crop embeddings",
            mode=PipelineMode.BALANCED,
            overrides={"embedding_crop_mode": EmbeddingCropMode.BOTH},
        ),
        "H_fast": BenchmarkConfig(
            name="H_fast",
            description="FAST mode through the enhanced code path",
            mode=PipelineMode.FAST,
            overrides={},
        ),
    }


def all_configs() -> dict[str, BenchmarkConfig]:
    return {**default_configs(), **extra_configs()}


def find_images(paths: Sequence[str], limit: "int | None" = None) -> list[str]:
    """Collect image files from files and/or directories, sorted for determinism."""
    found: list[str] = []
    for path in paths:
        if os.path.isfile(path):
            if path.lower().endswith(IMAGE_EXTENSIONS):
                found.append(path)
            else:
                logger.warning("skipping non-image file %s", path)
        elif os.path.isdir(path):
            for root, _dirs, files in os.walk(path):
                for name in sorted(files):
                    if name.lower().endswith(IMAGE_EXTENSIONS):
                        found.append(os.path.join(root, name))
        else:
            logger.warning("path does not exist: %s", path)

    found = sorted(set(found))
    if limit is not None:
        found = found[:limit]
    return found


def extract_video_frames(
    video_path: str,
    output_dir: str,
    every_n: int = 30,
    limit: "int | None" = None,
) -> list[str]:
    """Sample frames from a video into an image directory.

    Provided because this repository ships a room video but no image dataset,
    so a benchmark corpus can be produced from what is actually here.
    """
    os.makedirs(output_dir, exist_ok=True)
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise ValueError(f"could not open video: {video_path}")

    written: list[str] = []
    try:
        index = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if index % every_n == 0:
                path = os.path.join(output_dir, f"frame_{index:05d}.jpg")
                if cv2.imwrite(path, frame):
                    written.append(path)
                if limit is not None and len(written) >= limit:
                    break
            index += 1
    finally:
        capture.release()

    logger.info("extracted %d frames from %s into %s", len(written), video_path, output_dir)
    return written


def peak_memory_mb() -> "float | None":
    """Peak resident set size in MB, or ``None`` if unavailable.

    Uses ``resource.getrusage``, whose units differ by platform: bytes on
    macOS, kilobytes on Linux. Reported as a process-wide peak, so it includes
    model weights and is not attributable to a single stage.
    """
    try:
        import resource
    except ImportError:
        return None
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if usage <= 0:
        return None
    divisor = 1024 * 1024 if platform.system() == "Darwin" else 1024
    return round(usage / divisor, 1)


def gpu_peak_memory_mb() -> "float | None":
    """Peak CUDA memory in MB, or ``None`` when CUDA is not in use.

    Only CUDA exposes a reliable peak counter. Apple MPS has no equivalent
    API, so this returns ``None`` on Macs rather than reporting a wrong number.
    """
    try:
        import torch
    except ImportError:
        return None
    if not torch.cuda.is_available():
        return None
    return round(torch.cuda.max_memory_allocated() / (1024 * 1024), 1)


@dataclass
class ImageRecord:
    """Per-image outcome for one configuration."""

    path: str
    width: int
    height: int
    megapixels: float
    raw_count: int
    final_count: int
    prefused_count: int
    embedded_count: int
    tiled: bool
    timings: dict[str, float]
    merge_reasons: dict[str, int] = field(default_factory=dict)
    counts_by_source: dict[str, int] = field(default_factory=dict)
    counts_by_scale: dict[str, int] = field(default_factory=dict)
    small_object_count: int = 0
    quality: "dict[str, Any] | None" = None
    proposals: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "width": self.width,
            "height": self.height,
            "megapixels": round(self.megapixels, 3),
            "raw_count": self.raw_count,
            "prefused_count": self.prefused_count,
            "embedded_count": self.embedded_count,
            "final_count": self.final_count,
            "tiled": self.tiled,
            "small_object_count": self.small_object_count,
            "timings": dict(self.timings),
            "merge_reasons": dict(self.merge_reasons),
            "counts_by_source": dict(self.counts_by_source),
            "counts_by_scale": dict(self.counts_by_scale),
            "quality": self.quality,
            "proposals": self.proposals,
        }


def _record_from_result(path: str, result: PipelineResult) -> ImageRecord:
    height, width = result.image_shape
    detection = result.detection
    return ImageRecord(
        path=path,
        width=width,
        height=height,
        megapixels=(width * height) / 1e6,
        raw_count=result.raw_count,
        final_count=result.final_count,
        prefused_count=result.prefused_count,
        embedded_count=result.embedding_count,
        tiled=result.tiled,
        timings=dict(result.timings),
        merge_reasons=result.dedup.reason_counts() if result.dedup else {},
        counts_by_source=detection.counts_by_source() if detection else {},
        counts_by_scale={str(k): v for k, v in detection.counts_by_scale().items()} if detection else {},
        small_object_count=detection.small_object_count if detection else 0,
        quality=detection.quality.to_dict() if detection and detection.quality else None,
        proposals=[p.to_dict() for p in result.proposals],
    )


def run_configuration(
    config_spec: BenchmarkConfig,
    image_paths: Sequence[str],
    model_path: str,
    visualize: bool = False,
    debug_dir: str = "artifacts/cv_debug",
    warmup: bool = True,
) -> dict[str, Any]:
    """Run one configuration across every image."""
    vision_config = config_spec.build(model_path)
    if visualize:
        vision_config = vision_config.with_overrides(debug_visualization=True)

    pipeline = VisionPipeline(vision_config)

    if warmup and image_paths:
        # Load weights and let any lazy kernels compile before timing starts,
        # otherwise the first image absorbs tens of seconds of setup and the
        # latency numbers are meaningless.
        probe = cv2.imread(image_paths[0])
        if probe is not None:
            pipeline.warmup()
            try:
                if config_spec.use_baseline_path:
                    pipeline.process_baseline(probe)
                else:
                    pipeline.process_image(probe)
            except Exception as exc:  # pragma: no cover - warmup must never fail the run
                logger.warning("warmup failed for %s: %s", config_spec.name, exc)

    latency = LatencyStats()
    records: list[ImageRecord] = []
    failures: list[dict[str, str]] = []
    started = time.perf_counter()

    for index, path in enumerate(image_paths, start=1):
        image = cv2.imread(path)
        if image is None:
            logger.warning("could not read %s", path)
            failures.append({"path": path, "error": "unreadable"})
            continue
        try:
            if config_spec.use_baseline_path:
                result = pipeline.process_baseline(image)
            else:
                result = pipeline.process_image(image)
        except Exception as exc:
            logger.exception("failed on %s", path)
            failures.append({"path": path, "error": str(exc)})
            continue

        records.append(_record_from_result(path, result))
        latency.add(result.timings)

        if visualize:
            from vision import visualization as vis

            stem = f"{config_spec.name}_{os.path.splitext(os.path.basename(path))[0]}"
            vis.render_pipeline_stages(image, result, debug_dir, stem)

        if index % 10 == 0:
            logger.info("[%s] %d/%d images", config_spec.name, index, len(image_paths))

    wall_clock = time.perf_counter() - started
    raw_counts = [r.raw_count for r in records]
    final_counts = [r.final_count for r in records]

    aggregate_reasons: dict[str, int] = {}
    for record in records:
        for reason, count in record.merge_reasons.items():
            aggregate_reasons[reason] = aggregate_reasons.get(reason, 0) + count

    return {
        "name": config_spec.name,
        "description": config_spec.description,
        "mode": vision_config.mode.value,
        "uses_baseline_path": config_spec.use_baseline_path,
        "config": vision_config.summary(),
        "images_evaluated": len(records),
        "failures": failures,
        "proposal_statistics": proposal_statistics(raw_counts, final_counts),
        "latency": latency.to_dict(),
        "throughput_images_per_s": round(len(records) / wall_clock, 4) if wall_clock > 0 else None,
        "wall_clock_s": round(wall_clock, 3),
        "merge_reasons": dict(sorted(aggregate_reasons.items())),
        "tiled_images": sum(1 for r in records if r.tiled),
        "small_objects_total": sum(r.small_object_count for r in records),
        "peak_rss_mb": peak_memory_mb(),
        "peak_gpu_mb": gpu_peak_memory_mb(),
        "records": [r.to_dict() for r in records],
    }


def environment_info() -> dict[str, Any]:
    """Machine and library versions, so results are interpretable later."""
    info: dict[str, Any] = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "cpu_count": os.cpu_count(),
    }
    try:
        import torch

        info["torch"] = torch.__version__
        info["cuda_available"] = bool(torch.cuda.is_available())
        mps = getattr(torch.backends, "mps", None)
        info["mps_available"] = bool(mps is not None and mps.is_available())
        if torch.cuda.is_available():
            info["gpu_name"] = torch.cuda.get_device_name(0)
    except ImportError:
        info["torch"] = None
    try:
        import ultralytics

        info["ultralytics"] = ultralytics.__version__
    except ImportError:
        info["ultralytics"] = None
    info["opencv"] = cv2.__version__
    return info


def main(argv: "Sequence[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ablation benchmark for the ClaimReady perception pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--images",
        nargs="+",
        required=False,
        help="Image files and/or directories to evaluate",
    )
    parser.add_argument(
        "--from-video",
        help="Extract frames from this video and use them as the image set",
    )
    parser.add_argument(
        "--frame-interval",
        type=int,
        default=30,
        help="With --from-video, keep every Nth frame (default: 30)",
    )
    parser.add_argument("--limit", type=int, help="Evaluate at most this many images")
    parser.add_argument(
        "--configs",
        nargs="+",
        default=list(default_configs()),
        help=f"Configurations to run. Available: {', '.join(all_configs())}",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("CR_VISION_MODEL_PATH", "yolo11x-seg.pt"),
        help="YOLO weights (default: yolo11x-seg.pt, matching production)",
    )
    parser.add_argument("--output", help="Write JSON results here (default: benchmarks/results/<timestamp>.json)")
    parser.add_argument("--visualize", action="store_true", help="Also write per-stage debug renders")
    parser.add_argument("--debug-dir", default="artifacts/cv_debug", help="Where renders go")
    parser.add_argument("--no-warmup", action="store_true", help="Skip the warmup pass (latency will include setup)")
    parser.add_argument("--quiet", action="store_true", help="Only log warnings and errors")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    image_paths: list[str] = []
    if args.from_video:
        frame_dir = os.path.join(DEFAULT_RESULTS_DIR, "frames", os.path.splitext(os.path.basename(args.from_video))[0])
        image_paths = extract_video_frames(
            args.from_video, frame_dir, every_n=args.frame_interval, limit=args.limit
        )
    if args.images:
        image_paths.extend(find_images(args.images, limit=args.limit))

    image_paths = sorted(set(image_paths))
    if args.limit is not None:
        image_paths = image_paths[: args.limit]

    if not image_paths:
        parser.error("no images found; pass --images and/or --from-video")

    available = all_configs()
    unknown = [name for name in args.configs if name not in available]
    if unknown:
        parser.error(f"unknown configuration(s) {unknown}; available: {', '.join(available)}")

    logger.info("benchmarking %d images across %d configurations", len(image_paths), len(args.configs))

    results: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "environment": environment_info(),
        "model_path": args.model,
        "image_count": len(image_paths),
        "images": image_paths,
        "configurations": {},
        "annotations_available": False,
        "note": (
            "Proposal counts and latency are measured directly and need no labels. "
            "Precision/recall/mAP require ground truth; run benchmarks/evaluate.py "
            "with --annotations to compute them."
        ),
    }

    for name in args.configs:
        logger.info("running configuration %s", name)
        results["configurations"][name] = run_configuration(
            available[name],
            image_paths,
            model_path=args.model,
            visualize=args.visualize,
            debug_dir=args.debug_dir,
            warmup=not args.no_warmup,
        )

    output_path = args.output
    if output_path is None:
        os.makedirs(DEFAULT_RESULTS_DIR, exist_ok=True)
        output_path = os.path.join(DEFAULT_RESULTS_DIR, f"benchmark_{time.strftime('%Y%m%d_%H%M%S')}.json")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)

    print(f"\nWrote results to {output_path}\n")
    print_summary(results)
    return 0


def print_summary(results: dict[str, Any]) -> None:
    """Human-readable digest of a results file."""
    header = f"{'configuration':<20} {'imgs':>5} {'raw':>7} {'final':>7} {'reduct':>8} {'mean s':>8} {'p50 s':>8}"
    print(header)
    print("-" * len(header))
    for name, payload in results.get("configurations", {}).items():
        stats = payload.get("proposal_statistics", {})
        latency = payload.get("latency", {}).get("total_latency", {})
        reduction = stats.get("reduction_ratio")
        print(
            f"{name:<20} "
            f"{payload.get('images_evaluated', 0):>5} "
            f"{stats.get('raw_total', 0):>7} "
            f"{stats.get('final_total', 0):>7} "
            f"{(f'{reduction * 100:.1f}%' if reduction is not None else 'n/a'):>8} "
            f"{latency.get('mean', 0):>8.3f} "
            f"{latency.get('p50', 0):>8.3f}"
        )
    print(
        "\nPrecision/recall/mAP are not shown: they require ground-truth "
        "annotations (see benchmarks/evaluate.py)."
    )


if __name__ == "__main__":
    raise SystemExit(main())
