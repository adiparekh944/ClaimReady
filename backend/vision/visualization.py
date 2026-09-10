"""Debug renders of each pipeline stage.

Purpose
-------
The dedup rule combines five signals across three stages. When it makes a wrong
call, a JSON dump of box coordinates is nearly useless for working out why.
These renders make the failure visible: which pass produced a box, which
proposals were grouped, and which rule fired.

Output goes to ``artifacts/cv_debug/``, which is gitignored. Renders are
generated on demand and never committed.

Colour conventions
------------------
Stage renders colour boxes by *source pass*, so the contribution of each
detector pass is visible at a glance. Cluster renders colour by ``cluster_id``
from a fixed palette, so members of one cluster share a colour and the grouping
can be checked by eye.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Sequence

import cv2
import numpy as np

from .proposals import (
    SOURCE_ENHANCED,
    SOURCE_FULL_FRAME,
    SOURCE_SECONDARY,
    SOURCE_TILE,
    Proposal,
)

logger = logging.getLogger(__name__)

# BGR. Chosen to stay distinguishable against typical indoor photos and to
# survive grayscale printing at different luminances.
SOURCE_COLORS: dict[str, tuple[int, int, int]] = {
    SOURCE_FULL_FRAME: (80, 220, 80),
    SOURCE_SECONDARY: (60, 180, 255),
    SOURCE_ENHANCED: (255, 160, 60),
    SOURCE_TILE: (220, 100, 220),
}
DEFAULT_COLOR = (200, 200, 200)

# Repeating palette for cluster IDs.
CLUSTER_PALETTE: tuple[tuple[int, int, int], ...] = (
    (66, 135, 245),
    (52, 199, 89),
    (255, 149, 0),
    (175, 82, 222),
    (255, 59, 48),
    (90, 200, 250),
    (255, 214, 10),
    (48, 176, 199),
    (191, 90, 242),
    (172, 142, 104),
)


def _color_for_source(source_pass: str) -> tuple[int, int, int]:
    return SOURCE_COLORS.get(source_pass, DEFAULT_COLOR)


def _color_for_cluster(cluster_id: "int | None") -> tuple[int, int, int]:
    if cluster_id is None:
        return DEFAULT_COLOR
    return CLUSTER_PALETTE[cluster_id % len(CLUSTER_PALETTE)]


def draw_label(
    image: np.ndarray,
    text: str,
    origin: tuple[int, int],
    color: tuple[int, int, int],
    font_scale: float = 0.4,
) -> None:
    """Draw text on a filled background so it stays legible over any image."""
    if not text:
        return
    thickness = 1
    (text_w, text_h), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    x, y = origin
    # Flip the label below the box when it would be clipped at the top edge.
    y = max(y, text_h + baseline + 1)
    cv2.rectangle(image, (x, y - text_h - baseline), (x + text_w + 2, y), color, -1)
    cv2.putText(
        image,
        text,
        (x + 1, y - baseline),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        (0, 0, 0),
        thickness,
        cv2.LINE_AA,
    )


def draw_proposals(
    image: np.ndarray,
    proposals: Sequence[Proposal],
    title: str = "",
    color_by: str = "source",
    show_ids: bool = True,
    show_confidence: bool = True,
    thickness: int = 2,
) -> np.ndarray:
    """Render boxes annotated with id, confidence, cluster and source scale.

    Args:
        color_by: ``"source"`` colours by detector pass, ``"cluster"`` by
            cluster id, ``"merge_reason"`` groups by which rule fired.
    """
    canvas = image.copy()
    height, width = canvas.shape[:2]

    for proposal in proposals:
        if color_by == "cluster":
            color = _color_for_cluster(proposal.cluster_id)
        elif color_by == "merge_reason":
            color = _color_for_cluster(hash(proposal.merge_reason or "none") % len(CLUSTER_PALETTE))
        else:
            color = _color_for_source(proposal.source_pass)

        x1, y1, x2, y2 = proposal.clipped_bbox(width, height)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, thickness)

        parts: list[str] = []
        if show_ids:
            parts.append(f"#{proposal.proposal_id}")
        if show_confidence:
            parts.append(f"{proposal.confidence:.2f}")
        if proposal.cluster_id is not None:
            parts.append(f"c{proposal.cluster_id}")
        if proposal.source_scale:
            parts.append(f"s{proposal.source_scale}")
        if proposal.merge_reason:
            parts.append(proposal.merge_reason)
        draw_label(canvas, " ".join(parts), (x1, y1 - 2), color)

    if title:
        draw_label(canvas, f"{title} (n={len(proposals)})", (6, 20), (255, 255, 255), font_scale=0.6)
    return canvas


def draw_masks(
    image: np.ndarray,
    proposals: Sequence[Proposal],
    alpha: float = 0.45,
    title: str = "",
) -> np.ndarray:
    """Overlay segmentation masks, tinted per cluster.

    Masks are composited into a single colour layer and blended once, rather
    than blended one at a time, so overlapping masks do not compound into an
    opaque smear that hides everything underneath.
    """
    canvas = image.copy()
    overlay = np.zeros_like(canvas)
    drawn = 0

    for proposal in proposals:
        if proposal.mask is None:
            continue
        mask = proposal.mask.astype(bool, copy=False)
        if mask.shape[:2] != canvas.shape[:2]:
            logger.debug("skipping mask with shape %s for image %s", mask.shape, canvas.shape[:2])
            continue
        overlay[mask] = _color_for_cluster(proposal.cluster_id)
        drawn += 1

    if drawn:
        touched = overlay.any(axis=2)
        canvas[touched] = cv2.addWeighted(canvas, 1.0 - alpha, overlay, alpha, 0)[touched]

    if title:
        draw_label(canvas, f"{title} ({drawn} masks)", (6, 20), (255, 255, 255), font_scale=0.6)
    return canvas


def draw_merge_relationships(
    image: np.ndarray,
    proposals: Sequence[Proposal],
    merges: Sequence[Any],
    title: str = "merge graph",
) -> np.ndarray:
    """Draw a line between the centres of every merged pair, labelled by reason.

    Makes over-merging obvious: a long line across the frame means two distant
    proposals were joined, which is almost always a mistake.
    """
    canvas = image.copy()
    height, width = canvas.shape[:2]
    centers: dict[int, tuple[int, int]] = {}

    for proposal in proposals:
        x1, y1, x2, y2 = proposal.clipped_bbox(width, height)
        centers[proposal.proposal_id] = ((x1 + x2) // 2, (y1 + y2) // 2)
        cv2.circle(canvas, centers[proposal.proposal_id], 3, (255, 255, 255), -1)

    drawn = 0
    for record in merges:
        a = getattr(record, "proposal_a", None)
        b = getattr(record, "proposal_b", None)
        reason = getattr(record, "reason", "") or ""
        if a not in centers or b not in centers:
            continue
        color = _color_for_cluster(hash(reason) % len(CLUSTER_PALETTE))
        cv2.line(canvas, centers[a], centers[b], color, 1, cv2.LINE_AA)
        midpoint = ((centers[a][0] + centers[b][0]) // 2, (centers[a][1] + centers[b][1]) // 2)
        draw_label(canvas, reason, midpoint, color, font_scale=0.35)
        drawn += 1

    if title:
        draw_label(canvas, f"{title} ({drawn} merges)", (6, 20), (255, 255, 255), font_scale=0.6)
    return canvas


def side_by_side(panels: Sequence[np.ndarray], labels: "Sequence[str] | None" = None) -> np.ndarray:
    """Concatenate panels horizontally, padding to a common height.

    Padding rather than resizing so boxes stay pixel-comparable between panels
    — the whole point of a side-by-side is that a difference in the drawing is
    a real difference in the output, not a scaling artefact.
    """
    if not panels:
        raise ValueError("side_by_side requires at least one panel")

    target_height = max(p.shape[0] for p in panels)
    padded: list[np.ndarray] = []
    for index, panel in enumerate(panels):
        height, width = panel.shape[:2]
        if height < target_height:
            pad = np.zeros((target_height - height, width, 3), dtype=panel.dtype)
            panel = np.vstack([panel, pad])
        else:
            panel = panel.copy()
        if labels is not None and index < len(labels):
            draw_label(panel, labels[index], (6, target_height - 8), (255, 255, 0), font_scale=0.6)
        padded.append(panel)

    separator = np.full((target_height, 4, 3), 40, dtype=padded[0].dtype)
    stacked: list[np.ndarray] = []
    for index, panel in enumerate(padded):
        if index:
            stacked.append(separator)
        stacked.append(panel)
    return np.hstack(stacked)


def save_image(image: np.ndarray, path: str) -> str:
    """Write an image, creating parent directories as needed."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    if not cv2.imwrite(path, image):
        raise IOError(f"could not write image to {path}")
    return path


def render_pipeline_stages(
    image: np.ndarray,
    result: Any,
    output_dir: str,
    stem: str,
    save_masks: bool = True,
) -> dict[str, str]:
    """Write one render per pipeline stage for a single image.

    Args:
        image: The original BGR image.
        result: A :class:`vision.pipeline.PipelineResult`.
        output_dir: Destination directory, created if absent.
        stem: Filename prefix, normally the source image's basename.

    Returns:
        Mapping of stage name to written path.
    """
    os.makedirs(output_dir, exist_ok=True)
    written: dict[str, str] = {}

    detection = getattr(result, "detection", None)
    if detection is not None:
        raw = draw_proposals(image, detection.proposals, title="1. raw proposals", thickness=1)
        written["raw"] = save_image(raw, os.path.join(output_dir, f"{stem}_1_raw.jpg"))

    # Post-fusion, pre-dedup. Only available when the pipeline retained it.
    fused = getattr(result, "pre_dedup_proposals", None)
    if fused:
        panel = draw_proposals(image, fused, title="2. fused proposals", color_by="source")
        written["fused"] = save_image(panel, os.path.join(output_dir, f"{stem}_2_fused.jpg"))

    final = draw_proposals(image, result.proposals, title="3. final (deduplicated)", color_by="cluster")
    written["final"] = save_image(final, os.path.join(output_dir, f"{stem}_3_final.jpg"))

    if save_masks and any(p.mask is not None for p in result.proposals):
        masks = draw_masks(image, result.proposals, title="4. masks")
        written["masks"] = save_image(masks, os.path.join(output_dir, f"{stem}_4_masks.jpg"))

    dedup = getattr(result, "dedup", None)
    if dedup is not None and getattr(dedup, "merges", None):
        # Merge records reference pre-dedup proposal IDs, so draw against that
        # set when it was retained. Falling back to the final proposals would
        # silently render an empty graph, since merged-away IDs are gone.
        nodes = fused if fused else result.proposals
        graph = draw_merge_relationships(image, nodes, dedup.merges)
        written["merges"] = save_image(graph, os.path.join(output_dir, f"{stem}_5_merges.jpg"))

    return written


def render_comparison(
    image: np.ndarray,
    baseline_result: Any,
    enhanced_result: Any,
    output_dir: str,
    stem: str,
    baseline_label: str = "baseline (greedy IoU)",
    enhanced_label: str = "enhanced pipeline",
) -> str:
    """Write a single side-by-side baseline-vs-enhanced render."""
    os.makedirs(output_dir, exist_ok=True)
    left = draw_proposals(image, baseline_result.proposals, title="baseline", color_by="source")
    right = draw_proposals(image, enhanced_result.proposals, title="enhanced", color_by="cluster")
    combined = side_by_side(
        [left, right],
        [
            f"{baseline_label}: {len(baseline_result.proposals)} proposals",
            f"{enhanced_label}: {len(enhanced_result.proposals)} proposals",
        ],
    )
    return save_image(combined, os.path.join(output_dir, f"{stem}_comparison.jpg"))


__all__ = [
    "CLUSTER_PALETTE",
    "SOURCE_COLORS",
    "draw_label",
    "draw_masks",
    "draw_merge_relationships",
    "draw_proposals",
    "render_comparison",
    "render_pipeline_stages",
    "save_image",
    "side_by_side",
]
