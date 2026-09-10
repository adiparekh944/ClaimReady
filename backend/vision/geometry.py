"""Box geometry primitives shared by fusion, deduplication, tracking and metrics.

The original codebase defined ``_iou`` / ``iou`` / ``iou_boxes`` /
``calculate_iou`` in four different files with subtly different conventions
(some added 1 to widths, some did not). Everything now routes through this
module so the definitions cannot drift again.

Convention: a box is ``(x1, y1, x2, y2)`` in absolute pixel coordinates with
``x2 >= x1`` and ``y2 >= y1``. Widths are computed as ``x2 - x1`` with no ``+1``
offset, treating coordinates as continuous rather than inclusive pixel indices.
This matches how Ultralytics reports ``xyxy`` and how COCO defines box area.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

Box = Sequence[float]

EPS = 1e-9


def _as_array(boxes: "np.ndarray | Sequence[Box]") -> np.ndarray:
    arr = np.asarray(boxes, dtype=np.float64)
    if arr.size == 0:
        # An empty list must stay empty. Reshaping it to (1, -1) like a single
        # box would yield a (1, 0) array and make the pairwise helpers report a
        # 1x1 matrix for no input.
        return np.zeros((0, 4), dtype=np.float64)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr[:, :4]


def box_area(box: Box) -> float:
    """Area of a single box, clamped at zero for degenerate boxes."""
    x1, y1, x2, y2 = box[:4]
    return max(0.0, float(x2) - float(x1)) * max(0.0, float(y2) - float(y1))


def box_areas(boxes: "np.ndarray | Sequence[Box]") -> np.ndarray:
    """Vectorized areas for an ``(N, 4+)`` array."""
    arr = _as_array(boxes)
    widths = np.clip(arr[:, 2] - arr[:, 0], 0.0, None)
    heights = np.clip(arr[:, 3] - arr[:, 1], 0.0, None)
    return widths * heights


def intersection_area(a: Box, b: Box) -> float:
    """Area of overlap between two boxes."""
    ax1, ay1, ax2, ay2 = a[:4]
    bx1, by1, bx2, by2 = b[:4]
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    return max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)


def iou(a: Box, b: Box) -> float:
    """Intersection over union."""
    inter = intersection_area(a, b)
    if inter <= 0.0:
        return 0.0
    union = box_area(a) + box_area(b) - inter
    return float(inter / (union + EPS))


def intersection_over_smaller(a: Box, b: Box) -> float:
    """Intersection divided by the area of the *smaller* box.

    IoU is a poor similarity measure when one box is much larger than the
    other: a small object fully inside a large one scores low IoU despite being
    completely covered. This normalization exposes that case, which matters here
    because a low-confidence pass often emits both a whole-shelf box and boxes
    for the individual items on it.
    """
    inter = intersection_area(a, b)
    if inter <= 0.0:
        return 0.0
    smaller = min(box_area(a), box_area(b))
    return float(inter / (smaller + EPS))


def containment(inner: Box, outer: Box) -> float:
    """Fraction of ``inner`` that lies inside ``outer``.

    Asymmetric on purpose: ``containment(small, big)`` approaches 1.0 while
    ``containment(big, small)`` stays small. Callers use the direction to decide
    which proposal is the parent.
    """
    inner_area = box_area(inner)
    if inner_area <= 0.0:
        return 0.0
    return float(intersection_area(inner, outer) / (inner_area + EPS))


def box_center(box: Box) -> tuple[float, float]:
    x1, y1, x2, y2 = box[:4]
    return ((float(x1) + float(x2)) / 2.0, (float(y1) + float(y2)) / 2.0)


def center_distance(a: Box, b: Box) -> float:
    """Euclidean distance between box centers, in pixels."""
    ax, ay = box_center(a)
    bx, by = box_center(b)
    return float(np.hypot(ax - bx, ay - by))


def normalized_center_distance(a: Box, b: Box) -> float:
    """Center distance divided by the mean diagonal of the two boxes.

    Scale-free, so one threshold works for both a mug and a sofa. Values near 0
    mean concentric; values above ~0.5 mean the boxes are clearly offset.
    """
    ax1, ay1, ax2, ay2 = a[:4]
    bx1, by1, bx2, by2 = b[:4]
    diag_a = np.hypot(ax2 - ax1, ay2 - ay1)
    diag_b = np.hypot(bx2 - bx1, by2 - by1)
    scale = (diag_a + diag_b) / 2.0
    if scale <= 0.0:
        return float("inf")
    return float(center_distance(a, b) / scale)


def size_ratio(a: Box, b: Box) -> float:
    """Smaller area over larger area, in ``[0, 1]``.

    Guards against merging a tiny detection into a huge one purely because they
    overlap. A ratio near 1 means comparable size.
    """
    area_a, area_b = box_area(a), box_area(b)
    if area_a <= 0.0 or area_b <= 0.0:
        return 0.0
    return float(min(area_a, area_b) / max(area_a, area_b))


def union_box(boxes: Sequence[Box]) -> tuple[float, float, float, float]:
    """Smallest box enclosing all inputs."""
    if not boxes:
        raise ValueError("union_box requires at least one box")
    arr = _as_array(boxes)
    return (
        float(arr[:, 0].min()),
        float(arr[:, 1].min()),
        float(arr[:, 2].max()),
        float(arr[:, 3].max()),
    )


def clip_box(box: Box, width: int, height: int) -> tuple[int, int, int, int]:
    """Clamp a box to image bounds and round to integer pixels."""
    x1, y1, x2, y2 = box[:4]
    cx1 = int(max(0, min(round(x1), width - 1)))
    cy1 = int(max(0, min(round(y1), height - 1)))
    cx2 = int(max(0, min(round(x2), width)))
    cy2 = int(max(0, min(round(y2), height)))
    if cx2 <= cx1:
        cx2 = min(width, cx1 + 1)
    if cy2 <= cy1:
        cy2 = min(height, cy1 + 1)
    return cx1, cy1, cx2, cy2


def scale_box(box: Box, scale_x: float, scale_y: float) -> tuple[float, float, float, float]:
    """Multiply coordinates by per-axis factors.

    Used to project detections made on a resized or tiled image back into
    original-image coordinates.
    """
    x1, y1, x2, y2 = box[:4]
    return (float(x1) * scale_x, float(y1) * scale_y, float(x2) * scale_x, float(y2) * scale_y)


def translate_box(box: Box, dx: float, dy: float) -> tuple[float, float, float, float]:
    """Shift a box by an offset, e.g. a tile origin."""
    x1, y1, x2, y2 = box[:4]
    return (float(x1) + dx, float(y1) + dy, float(x2) + dx, float(y2) + dy)


def pairwise_iou(boxes_a: "np.ndarray | Sequence[Box]", boxes_b: "np.ndarray | Sequence[Box]") -> np.ndarray:
    """Full ``(N, M)`` IoU matrix.

    Vectorized because deduplication needs every pair and a Python double loop
    dominates runtime once N reaches a few hundred proposals.
    """
    a = _as_array(boxes_a)
    b = _as_array(boxes_b)
    if a.size == 0 or b.size == 0:
        return np.zeros((a.shape[0], b.shape[0]), dtype=np.float64)

    ix1 = np.maximum(a[:, None, 0], b[None, :, 0])
    iy1 = np.maximum(a[:, None, 1], b[None, :, 1])
    ix2 = np.minimum(a[:, None, 2], b[None, :, 2])
    iy2 = np.minimum(a[:, None, 3], b[None, :, 3])

    inter = np.clip(ix2 - ix1, 0.0, None) * np.clip(iy2 - iy1, 0.0, None)
    area_a = box_areas(a)[:, None]
    area_b = box_areas(b)[None, :]
    return inter / (area_a + area_b - inter + EPS)


def pairwise_containment(boxes: "np.ndarray | Sequence[Box]") -> np.ndarray:
    """``(N, N)`` matrix where entry ``[i, j]`` is the fraction of box ``i``
    contained in box ``j``."""
    arr = _as_array(boxes)
    n = arr.shape[0]
    if n == 0:
        return np.zeros((0, 0), dtype=np.float64)

    ix1 = np.maximum(arr[:, None, 0], arr[None, :, 0])
    iy1 = np.maximum(arr[:, None, 1], arr[None, :, 1])
    ix2 = np.minimum(arr[:, None, 2], arr[None, :, 2])
    iy2 = np.minimum(arr[:, None, 3], arr[None, :, 3])

    inter = np.clip(ix2 - ix1, 0.0, None) * np.clip(iy2 - iy1, 0.0, None)
    areas = box_areas(arr)[:, None]
    return inter / (areas + EPS)


def pairwise_normalized_center_distance(boxes: "np.ndarray | Sequence[Box]") -> np.ndarray:
    """``(N, N)`` scale-free center-distance matrix."""
    arr = _as_array(boxes)
    n = arr.shape[0]
    if n == 0:
        return np.zeros((0, 0), dtype=np.float64)

    cx = (arr[:, 0] + arr[:, 2]) / 2.0
    cy = (arr[:, 1] + arr[:, 3]) / 2.0
    dist = np.hypot(cx[:, None] - cx[None, :], cy[:, None] - cy[None, :])

    diag = np.hypot(arr[:, 2] - arr[:, 0], arr[:, 3] - arr[:, 1])
    scale = (diag[:, None] + diag[None, :]) / 2.0
    return dist / (scale + EPS)


def pairwise_size_ratio(boxes: "np.ndarray | Sequence[Box]") -> np.ndarray:
    """``(N, N)`` matrix of smaller-over-larger area ratios."""
    areas = box_areas(boxes)
    if areas.size == 0:
        return np.zeros((0, 0), dtype=np.float64)
    a = areas[:, None]
    b = areas[None, :]
    return np.minimum(a, b) / (np.maximum(a, b) + EPS)


__all__ = [
    "Box",
    "box_area",
    "box_areas",
    "box_center",
    "center_distance",
    "clip_box",
    "containment",
    "intersection_area",
    "intersection_over_smaller",
    "iou",
    "normalized_center_distance",
    "pairwise_containment",
    "pairwise_iou",
    "pairwise_normalized_center_distance",
    "pairwise_size_ratio",
    "scale_box",
    "size_ratio",
    "translate_box",
    "union_box",
]
