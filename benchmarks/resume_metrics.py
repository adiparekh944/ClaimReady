#!/usr/bin/env python3
"""Derive defensible summary metrics from benchmark output.

Purpose and hard rule
---------------------
This tool computes deltas between benchmark configurations so the effect of
each pipeline change can be stated precisely. **It only ever reports numbers
that were measured.** Every metric requiring ground truth is emitted as
``null`` with a ``"reason"`` explaining what is missing, and no value is
computed from an assumption, an extrapolation, or a default.

That constraint is the point of the file. A claim like "improved recall by 30%"
is worthless — and worse, indefensible in an interview — unless a specific
number came out of a specific measurement on a named dataset. So the output
distinguishes three tiers:

``measured_without_labels``
    Proposal counts, reduction ratios, latency, throughput, video association
    counts. Directly observed; always available.

``measured_with_labels``
    Precision, recall, F1, mAP, small-object recall, duplicate F1. Present only
    when an evaluation file from :mod:`benchmarks.evaluate` is supplied.

``unavailable``
    Everything that was asked for but cannot be computed, with the reason.

Every reported figure carries the sample size it came from, because "38% fewer
duplicate proposals" means something different over 6 images than over 600.

Usage::

    python -m benchmarks.resume_metrics --results benchmarks/results/latest.json
    python -m benchmarks.resume_metrics --results r.json --evaluation e.json
    python -m benchmarks.resume_metrics --results r.json --baseline A_baseline --candidate D_full
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Sequence

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("resume_metrics")

# Metrics that cannot exist without annotations, and why.
LABEL_DEPENDENT = {
    "precision": "requires ground-truth boxes",
    "recall": "requires ground-truth boxes",
    "f1": "requires ground-truth boxes",
    "map@0.50": "requires ground-truth boxes",
    "map@0.50:0.95": "requires ground-truth boxes",
    "small_object_recall": "requires ground-truth boxes tagged or measurable as small",
    "duplicate_precision": "requires duplicate_groups annotations",
    "duplicate_recall": "requires duplicate_groups annotations",
    "duplicate_f1": "requires duplicate_groups annotations",
}


def relative_change(baseline: "float | None", candidate: "float | None") -> "float | None":
    """Fractional change from baseline to candidate, or ``None`` if undefined.

    Returns ``None`` rather than 0 or infinity when the baseline is zero or
    missing, so an undefined comparison cannot be mistaken for "no change".
    """
    if baseline is None or candidate is None:
        return None
    if baseline == 0:
        return None
    return round((candidate - baseline) / abs(baseline), 4)


def _get(payload: dict[str, Any], *path: str, default: Any = None) -> Any:
    """Nested dictionary lookup that tolerates missing intermediate keys."""
    current: Any = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def compare_counting(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Proposal-count and latency deltas. Needs no annotations."""
    b_stats = baseline.get("proposal_statistics", {})
    c_stats = candidate.get("proposal_statistics", {})
    b_latency = _get(baseline, "latency", "total_latency", default={})
    c_latency = _get(candidate, "latency", "total_latency", default={})

    b_images = baseline.get("images_evaluated", 0)
    c_images = candidate.get("images_evaluated", 0)

    b_final = b_stats.get("final_total")
    c_final = c_stats.get("final_total")
    b_raw = b_stats.get("raw_total")
    c_raw = c_stats.get("raw_total")

    out: dict[str, Any] = {
        "images_evaluated": c_images,
        "images_evaluated_baseline": b_images,
        "sample_size_warning": (
            f"only {c_images} images evaluated; too small for a general claim"
            if c_images < 25
            else None
        ),
        "raw_proposals": {"baseline": b_raw, "candidate": c_raw},
        "final_proposals": {"baseline": b_final, "candidate": c_final},
        "mean_final_per_image": {
            "baseline": b_stats.get("mean_final_per_image"),
            "candidate": c_stats.get("mean_final_per_image"),
        },
        "proposal_reduction_ratio": {
            "baseline": b_stats.get("reduction_ratio"),
            "candidate": c_stats.get("reduction_ratio"),
        },
        # How many more raw candidates the enhanced detector surfaced. Higher
        # is only good if dedup still collapses them, which the next figure
        # shows.
        "raw_proposal_change": relative_change(b_raw, c_raw),
        "final_proposal_change": relative_change(b_final, c_final),
        "duplicates_removed": {
            "baseline": b_stats.get("duplicates_removed"),
            "candidate": c_stats.get("duplicates_removed"),
        },
        "latency_s": {
            "baseline_mean": b_latency.get("mean"),
            "candidate_mean": c_latency.get("mean"),
            "baseline_p50": b_latency.get("p50"),
            "candidate_p50": c_latency.get("p50"),
            "baseline_p90": b_latency.get("p90"),
            "candidate_p90": c_latency.get("p90"),
        },
        "latency_change": relative_change(b_latency.get("mean"), c_latency.get("mean")),
        "throughput_images_per_s": {
            "baseline": baseline.get("throughput_images_per_s"),
            "candidate": candidate.get("throughput_images_per_s"),
        },
        "mean_latency_by_stage": {
            "baseline": _get(baseline, "latency", "mean_by_stage", default={}),
            "candidate": _get(candidate, "latency", "mean_by_stage", default={}),
        },
        "merge_reasons": {
            "baseline": baseline.get("merge_reasons", {}),
            "candidate": candidate.get("merge_reasons", {}),
        },
        "tiled_images": {
            "baseline": baseline.get("tiled_images"),
            "candidate": candidate.get("tiled_images"),
        },
        "small_objects_detected": {
            "baseline": baseline.get("small_objects_total"),
            "candidate": candidate.get("small_objects_total"),
        },
        "peak_rss_mb": {
            "baseline": baseline.get("peak_rss_mb"),
            "candidate": candidate.get("peak_rss_mb"),
        },
        "peak_gpu_mb": {
            "baseline": baseline.get("peak_gpu_mb"),
            "candidate": candidate.get("peak_gpu_mb"),
        },
    }
    return out


def compare_accuracy(
    baseline_eval: "dict[str, Any] | None",
    candidate_eval: "dict[str, Any] | None",
) -> dict[str, Any]:
    """Accuracy deltas, or an explicit unavailability report."""
    if not baseline_eval or not candidate_eval:
        return {
            "available": False,
            "reason": (
                "no evaluation file supplied. Detection accuracy requires ground-truth "
                "annotations, which this repository does not ship. Generate a template "
                "with benchmarks/evaluate.py --make-template, label it, then pass the "
                "evaluation output via --evaluation."
            ),
            "metrics": {name: None for name in LABEL_DEPENDENT},
            "unavailable_reasons": dict(LABEL_DEPENDENT),
        }

    def pick(payload: dict[str, Any], key: str) -> "float | None":
        if key in ("map@0.50", "map@0.50:0.95"):
            return _get(payload, "map", key)
        if key.startswith("duplicate_"):
            return _get(payload, "duplicates", key)
        return payload.get(key)

    metrics: dict[str, Any] = {}
    for name in LABEL_DEPENDENT:
        b_value = pick(baseline_eval, name)
        c_value = pick(candidate_eval, name)
        metrics[name] = {
            "baseline": b_value,
            "candidate": c_value,
            "relative_change": relative_change(b_value, c_value),
            "absolute_change": (
                round(c_value - b_value, 4) if (b_value is not None and c_value is not None) else None
            ),
        }

    return {
        "available": True,
        "images_evaluated": candidate_eval.get("images_evaluated"),
        "objects_evaluated": candidate_eval.get("objects_evaluated"),
        "small_objects_evaluated": candidate_eval.get("small_objects"),
        "iou_threshold": candidate_eval.get("iou_threshold"),
        "metrics": metrics,
    }


def summarize_video(video_payload: "dict[str, Any] | None") -> dict[str, Any]:
    """Video association summary, from a tracking result JSON if provided."""
    if not video_payload:
        return {
            "available": False,
            "reason": (
                "no video tracking result supplied. Produce one with "
                "benchmarks/run_video_benchmark.py, which reports tracker IDs, "
                "inventory identities and re-identification counts."
            ),
        }

    with_reid = video_payload.get("with_reid", {})
    without_reid = video_payload.get("without_reid", {})

    b_identities = without_reid.get("inventory_identities")
    c_identities = with_reid.get("inventory_identities")

    return {
        "available": True,
        "frames_processed": with_reid.get("frames_processed"),
        "generated_track_ids": with_reid.get("generated_track_ids"),
        "inventory_identities": {
            "tracker_ids_only": b_identities,
            "with_reid": c_identities,
        },
        "identity_reduction": relative_change(b_identities, c_identities),
        "reid_events": with_reid.get("reid_events"),
        "id_switches_absorbed": with_reid.get("id_switches_absorbed"),
        "note": (
            "Identity counts are directly observed. Whether each merge was *correct* "
            "requires labelling the true object count per video, which is not shipped."
        ),
    }


def build_report(
    results: dict[str, Any],
    baseline_name: str,
    candidate_name: str,
    evaluation: "dict[str, Any] | None" = None,
    video: "dict[str, Any] | None" = None,
) -> dict[str, Any]:
    """Assemble the full three-tier report."""
    configurations = results.get("configurations", {})
    for name in (baseline_name, candidate_name):
        if name not in configurations:
            raise KeyError(f"configuration {name!r} not in results; have {list(configurations)}")

    baseline = configurations[baseline_name]
    candidate = configurations[candidate_name]

    eval_configs = (evaluation or {}).get("configurations", {})
    baseline_eval = eval_configs.get(baseline_name)
    candidate_eval = eval_configs.get(candidate_name)
    if baseline_eval and "error" in baseline_eval:
        baseline_eval = None
    if candidate_eval and "error" in candidate_eval:
        candidate_eval = None

    return {
        "generated_from": {
            "results_file": results.get("_source_path"),
            "generated_at": results.get("generated_at"),
            "environment": results.get("environment", {}),
            "model_path": results.get("model_path"),
        },
        "comparison": {"baseline": baseline_name, "candidate": candidate_name},
        "configuration_descriptions": {
            baseline_name: baseline.get("description"),
            candidate_name: candidate.get("description"),
        },
        "measured_without_labels": compare_counting(baseline, candidate),
        "measured_with_labels": compare_accuracy(baseline_eval, candidate_eval),
        "video_association": summarize_video(video),
        "all_configurations": {
            name: {
                "description": payload.get("description"),
                "mode": payload.get("mode"),
                "images": payload.get("images_evaluated"),
                "proposal_statistics": payload.get("proposal_statistics"),
                "mean_latency_s": _get(payload, "latency", "total_latency", "mean"),
                "merge_reasons": payload.get("merge_reasons"),
            }
            for name, payload in configurations.items()
        },
    }


def _fmt_pct(value: "float | None") -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:+.1f}%"


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def print_report(report: dict[str, Any]) -> None:
    """Print the report, keeping measured and unavailable strictly separated."""
    comparison = report["comparison"]
    counting = report["measured_without_labels"]
    accuracy = report["measured_with_labels"]
    video = report["video_association"]

    print("=" * 78)
    print(f"RESUME METRIC CANDIDATES  ({comparison['baseline']} -> {comparison['candidate']})")
    print("=" * 78)

    env = report["generated_from"].get("environment", {})
    print(f"\nMeasured on: {env.get('platform', 'unknown')}")
    print(f"Model: {report['generated_from'].get('model_path')}")
    print(f"Images: {counting['images_evaluated']}")
    if counting.get("sample_size_warning"):
        print(f"  !! {counting['sample_size_warning']}")

    print("\n--- MEASURED (no labels needed) ---")
    print(f"  raw proposals       {_fmt(counting['raw_proposals']['baseline']):>10} -> {_fmt(counting['raw_proposals']['candidate']):>10}  ({_fmt_pct(counting['raw_proposal_change'])})")
    print(f"  final proposals     {_fmt(counting['final_proposals']['baseline']):>10} -> {_fmt(counting['final_proposals']['candidate']):>10}  ({_fmt_pct(counting['final_proposal_change'])})")
    print(f"  mean final / image  {_fmt(counting['mean_final_per_image']['baseline']):>10} -> {_fmt(counting['mean_final_per_image']['candidate']):>10}")
    print(f"  proposal reduction  {_fmt_pct(counting['proposal_reduction_ratio']['baseline']):>10} -> {_fmt_pct(counting['proposal_reduction_ratio']['candidate']):>10}")
    print(f"  mean latency (s)    {_fmt(counting['latency_s']['baseline_mean']):>10} -> {_fmt(counting['latency_s']['candidate_mean']):>10}  ({_fmt_pct(counting['latency_change'])})")
    print(f"  p50 latency (s)     {_fmt(counting['latency_s']['baseline_p50']):>10} -> {_fmt(counting['latency_s']['candidate_p50']):>10}")
    print(f"  throughput (img/s)  {_fmt(counting['throughput_images_per_s']['baseline']):>10} -> {_fmt(counting['throughput_images_per_s']['candidate']):>10}")
    print(f"  small objects found {_fmt(counting['small_objects_detected']['baseline']):>10} -> {_fmt(counting['small_objects_detected']['candidate']):>10}")
    if counting["merge_reasons"]["candidate"]:
        print(f"  merge reasons (candidate): {counting['merge_reasons']['candidate']}")

    stages = counting["mean_latency_by_stage"]["candidate"]
    if stages:
        print("\n  latency breakdown by stage (candidate, mean s):")
        for stage, value in sorted(stages.items(), key=lambda kv: -kv[1]):
            if stage != "total":
                print(f"    {stage:<22} {value:.4f}")

    print("\n--- MEASURED (labels required) ---")
    if not accuracy.get("available"):
        print(f"  UNAVAILABLE: {accuracy['reason']}")
        print("  The following cannot be reported:")
        for name, reason in accuracy["unavailable_reasons"].items():
            print(f"    {name:<24} {reason}")
    else:
        print(f"  images={accuracy['images_evaluated']} objects={accuracy['objects_evaluated']} IoU={accuracy['iou_threshold']}")
        for name, values in accuracy["metrics"].items():
            if values["baseline"] is None and values["candidate"] is None:
                continue
            print(
                f"  {name:<24} {_fmt(values['baseline']):>8} -> {_fmt(values['candidate']):>8}  "
                f"({_fmt_pct(values['relative_change'])})"
            )

    print("\n--- VIDEO ASSOCIATION ---")
    if not video.get("available"):
        print(f"  UNAVAILABLE: {video['reason']}")
    else:
        identities = video["inventory_identities"]
        print(f"  frames processed        {_fmt(video['frames_processed'])}")
        print(f"  tracker IDs generated   {_fmt(video['generated_track_ids'])}")
        print(f"  identities (tracker)    {_fmt(identities['tracker_ids_only'])}")
        print(f"  identities (with re-id) {_fmt(identities['with_reid'])}  ({_fmt_pct(video['identity_reduction'])})")
        print(f"  re-id events            {_fmt(video['reid_events'])}")
        print(f"  ID switches absorbed    {_fmt(video['id_switches_absorbed'])}")

    print("\n" + "=" * 78)
    print("Every number above was measured on this machine from the named files.")
    print("Fields marked UNAVAILABLE must not be stated as results anywhere.")
    print("=" * 78)


def main(argv: "Sequence[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(
        description="Derive measured summary metrics from benchmark output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--results", required=True, help="Benchmark JSON from run_cv_benchmark")
    parser.add_argument("--evaluation", help="Evaluation JSON from evaluate.py (enables accuracy metrics)")
    parser.add_argument("--video", help="Video tracking comparison JSON from run_video_benchmark")
    parser.add_argument("--baseline", default="A_baseline", help="Baseline configuration name")
    parser.add_argument("--candidate", default="D_full", help="Candidate configuration name")
    parser.add_argument("--output", help="Write the report JSON here")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    with open(args.results, "r", encoding="utf-8") as handle:
        results = json.load(handle)
    results["_source_path"] = os.path.abspath(args.results)

    evaluation = None
    if args.evaluation:
        with open(args.evaluation, "r", encoding="utf-8") as handle:
            evaluation = json.load(handle)

    video = None
    if args.video:
        with open(args.video, "r", encoding="utf-8") as handle:
            video = json.load(handle)

    try:
        report = build_report(results, args.baseline, args.candidate, evaluation, video)
    except KeyError as exc:
        parser.error(str(exc))

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
        print(f"Wrote report to {args.output}\n")

    print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
