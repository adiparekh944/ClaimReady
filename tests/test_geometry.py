"""Tests for box geometry primitives.

These are the foundation everything else builds on, so they are tested against
hand-computed values rather than against each other.
"""

from __future__ import annotations

import numpy as np
import pytest

from vision import geometry


class TestIoU:
    def test_identical_boxes(self):
        box = (0, 0, 10, 10)
        assert geometry.iou(box, box) == pytest.approx(1.0)

    def test_disjoint_boxes(self):
        assert geometry.iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0

    def test_touching_edges_do_not_overlap(self):
        # Sharing an edge is zero area under a continuous-coordinate
        # convention. The original code's `+1` width offset made this 0.09.
        assert geometry.iou((0, 0, 10, 10), (10, 0, 20, 10)) == 0.0

    def test_half_overlap(self):
        # Two 10x10 boxes offset by 5 in x: intersection 5*10=50,
        # union 100+100-50=150, so IoU = 1/3.
        assert geometry.iou((0, 0, 10, 10), (5, 0, 15, 10)) == pytest.approx(1 / 3, abs=1e-6)

    def test_nested_box(self):
        # 4x4 inside 10x10: intersection 16, union 100, IoU 0.16.
        assert geometry.iou((0, 0, 10, 10), (2, 2, 6, 6)) == pytest.approx(0.16, abs=1e-6)

    def test_degenerate_box_has_zero_iou(self):
        assert geometry.iou((5, 5, 5, 5), (0, 0, 10, 10)) == 0.0

    def test_symmetry(self):
        a, b = (3, 4, 20, 25), (10, 8, 30, 40)
        assert geometry.iou(a, b) == pytest.approx(geometry.iou(b, a))


class TestAreaAndContainment:
    def test_box_area(self):
        assert geometry.box_area((0, 0, 10, 20)) == 200.0

    def test_inverted_box_clamps_to_zero(self):
        assert geometry.box_area((10, 10, 0, 0)) == 0.0

    def test_full_containment(self):
        assert geometry.containment((2, 2, 4, 4), (0, 0, 10, 10)) == pytest.approx(1.0, abs=1e-6)

    def test_containment_is_asymmetric(self):
        small, large = (2, 2, 4, 4), (0, 0, 10, 10)
        assert geometry.containment(small, large) == pytest.approx(1.0, abs=1e-6)
        # 4 of the large box's 100 units lie inside the small one.
        assert geometry.containment(large, small) == pytest.approx(0.04, abs=1e-6)

    def test_partial_containment(self):
        # Half of the 4x4 box lies inside the 10x10 box.
        assert geometry.containment((8, 2, 12, 6), (0, 0, 10, 10)) == pytest.approx(0.5, abs=1e-6)

    def test_intersection_over_smaller_beats_iou_for_nesting(self):
        small, large = (2, 2, 4, 4), (0, 0, 10, 10)
        # This is the whole reason the metric exists: IoU is misleadingly low
        # for a fully contained small object.
        assert geometry.iou(small, large) == pytest.approx(0.04, abs=1e-6)
        assert geometry.intersection_over_smaller(small, large) == pytest.approx(1.0, abs=1e-6)


class TestCenterAndSize:
    def test_box_center(self):
        assert geometry.box_center((0, 0, 10, 20)) == (5.0, 10.0)

    def test_center_distance(self):
        assert geometry.center_distance((0, 0, 2, 2), (3, 4, 5, 6)) == pytest.approx(5.0)

    def test_normalized_center_distance_is_scale_free(self):
        # Doubling both boxes and their separation must not change the value.
        small = geometry.normalized_center_distance((0, 0, 10, 10), (5, 0, 15, 10))
        large = geometry.normalized_center_distance((0, 0, 20, 20), (10, 0, 30, 20))
        assert small == pytest.approx(large)

    def test_concentric_boxes_have_zero_center_distance(self):
        assert geometry.normalized_center_distance((0, 0, 10, 10), (2, 2, 8, 8)) == 0.0

    def test_size_ratio(self):
        assert geometry.size_ratio((0, 0, 10, 10), (0, 0, 5, 5)) == pytest.approx(0.25)

    def test_size_ratio_is_one_for_equal_areas(self):
        assert geometry.size_ratio((0, 0, 10, 10), (50, 50, 60, 60)) == pytest.approx(1.0)


class TestUnionAndTransforms:
    def test_union_box(self):
        assert geometry.union_box([(0, 0, 5, 5), (10, 10, 20, 20)]) == (0.0, 0.0, 20.0, 20.0)

    def test_union_of_single_box_is_itself(self):
        assert geometry.union_box([(3, 4, 5, 6)]) == (3.0, 4.0, 5.0, 6.0)

    def test_union_requires_input(self):
        with pytest.raises(ValueError):
            geometry.union_box([])

    def test_clip_box_to_bounds(self):
        assert geometry.clip_box((-10, -10, 500, 500), 100, 80) == (0, 0, 100, 80)

    def test_clip_box_never_returns_empty(self):
        x1, y1, x2, y2 = geometry.clip_box((99.6, 79.6, 99.7, 79.7), 100, 80)
        assert x2 > x1 and y2 > y1

    def test_scale_box_round_trip(self):
        original = (10.0, 20.0, 30.0, 40.0)
        scaled = geometry.scale_box(original, 2.0, 4.0)
        assert scaled == (20.0, 80.0, 60.0, 160.0)
        assert geometry.scale_box(scaled, 0.5, 0.25) == original

    def test_translate_box_round_trip(self):
        original = (10.0, 20.0, 30.0, 40.0)
        moved = geometry.translate_box(original, 100, -5)
        assert moved == (110.0, 15.0, 130.0, 35.0)
        assert geometry.translate_box(moved, -100, 5) == original


class TestVectorizedMatchesScalar:
    """The matrix helpers must agree exactly with the scalar functions.

    Deduplication reads the matrices while the documented rule is written in
    terms of the scalar definitions, so any divergence would be a silent
    behaviour change.
    """

    BOXES = [
        (0, 0, 10, 10),
        (5, 5, 15, 15),
        (2, 2, 4, 4),
        (100, 100, 180, 140),
    ]

    def test_pairwise_iou(self):
        matrix = geometry.pairwise_iou(self.BOXES, self.BOXES)
        assert matrix.shape == (4, 4)
        for i, a in enumerate(self.BOXES):
            for j, b in enumerate(self.BOXES):
                assert matrix[i, j] == pytest.approx(geometry.iou(a, b), abs=1e-9)

    def test_pairwise_containment(self):
        matrix = geometry.pairwise_containment(self.BOXES)
        for i, a in enumerate(self.BOXES):
            for j, b in enumerate(self.BOXES):
                assert matrix[i, j] == pytest.approx(geometry.containment(a, b), abs=1e-9)

    def test_pairwise_center_distance(self):
        matrix = geometry.pairwise_normalized_center_distance(self.BOXES)
        for i, a in enumerate(self.BOXES):
            for j, b in enumerate(self.BOXES):
                assert matrix[i, j] == pytest.approx(
                    geometry.normalized_center_distance(a, b), abs=1e-9
                )

    def test_pairwise_size_ratio(self):
        matrix = geometry.pairwise_size_ratio(self.BOXES)
        for i, a in enumerate(self.BOXES):
            for j, b in enumerate(self.BOXES):
                assert matrix[i, j] == pytest.approx(geometry.size_ratio(a, b), abs=1e-9)

    def test_empty_input_gives_empty_matrix(self):
        assert geometry.pairwise_iou([], []).shape == (0, 0)
        assert geometry.pairwise_containment([]).shape == (0, 0)

    def test_pairwise_iou_diagonal_is_one(self):
        matrix = geometry.pairwise_iou(self.BOXES, self.BOXES)
        assert np.allclose(np.diag(matrix), 1.0, atol=1e-6)
