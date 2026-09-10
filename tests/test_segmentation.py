"""Tests for mask handling: IoU, occupancy, crops and coordinate projection."""

from __future__ import annotations

import numpy as np
import pytest

from vision import segmentation
from vision.detector import project_mask
from vision.proposals import Proposal


def square_mask(shape, y0, y1, x0, x1):
    mask = np.zeros(shape, dtype=np.uint8)
    mask[y0:y1, x0:x1] = 1
    return mask


class TestMaskIoU:
    def test_identical_masks(self):
        mask = square_mask((20, 20), 2, 12, 2, 12)
        assert segmentation.mask_iou(mask, mask) == pytest.approx(1.0)

    def test_disjoint_masks(self):
        a = square_mask((20, 20), 0, 5, 0, 5)
        b = square_mask((20, 20), 10, 15, 10, 15)
        assert segmentation.mask_iou(a, b) == 0.0

    def test_partial_overlap(self):
        a = square_mask((20, 20), 2, 12, 2, 12)  # 100 px
        b = square_mask((20, 20), 7, 17, 7, 17)  # 100 px
        # 5x5 = 25 overlap, union 175.
        assert segmentation.mask_iou(a, b) == pytest.approx(25 / 175)

    def test_missing_mask_reads_as_no_evidence(self):
        mask = square_mask((10, 10), 0, 5, 0, 5)
        assert segmentation.mask_iou(mask, None) == 0.0
        assert segmentation.mask_iou(None, None) == 0.0

    def test_shape_mismatch_raises(self):
        with pytest.raises(ValueError, match="shapes differ"):
            segmentation.mask_iou(np.ones((10, 10), np.uint8), np.ones((20, 20), np.uint8))

    def test_empty_masks_give_zero_not_nan(self):
        zeros = np.zeros((10, 10), dtype=np.uint8)
        assert segmentation.mask_iou(zeros, zeros) == 0.0


class TestMaskIoUDistinguishesOverlappingObjects:
    def test_high_box_iou_but_low_mask_iou(self):
        """A lamp in front of a bookshelf: boxes overlap, masks do not.

        This is the case box IoU cannot handle and mask IoU can, so it is the
        justification for computing masks at all.
        """
        from vision import geometry

        # Two boxes covering nearly the same region.
        box_a = (0, 0, 40, 40)
        box_b = (2, 2, 42, 42)
        assert geometry.iou(box_a, box_b) > 0.8

        # But their masks occupy different halves of that region.
        mask_a = square_mask((50, 50), 0, 40, 0, 18)
        mask_b = square_mask((50, 50), 2, 42, 24, 42)
        assert segmentation.mask_iou(mask_a, mask_b) == 0.0


class TestContainmentAndOccupancy:
    def test_mask_containment(self):
        inner = square_mask((20, 20), 5, 10, 5, 10)   # 25 px
        outer = square_mask((20, 20), 0, 20, 0, 20)
        assert segmentation.mask_containment(inner, outer) == pytest.approx(1.0)

    def test_mask_containment_is_asymmetric(self):
        inner = square_mask((20, 20), 5, 10, 5, 10)   # 25 px
        outer = square_mask((20, 20), 0, 20, 0, 20)   # 400 px
        assert segmentation.mask_containment(outer, inner) == pytest.approx(25 / 400)

    def test_bbox_occupancy_full(self):
        mask = square_mask((20, 20), 2, 12, 2, 12)
        assert segmentation.bbox_occupancy(mask, (2, 2, 12, 12)) == pytest.approx(1.0)

    def test_bbox_occupancy_half(self):
        mask = square_mask((20, 20), 2, 12, 2, 7)  # left half of the box
        assert segmentation.bbox_occupancy(mask, (2, 2, 12, 12)) == pytest.approx(0.5)

    def test_bbox_occupancy_outside_image(self):
        mask = square_mask((20, 20), 0, 5, 0, 5)
        assert segmentation.bbox_occupancy(mask, (100, 100, 110, 110)) == 0.0


class TestPairwiseMaskIoU:
    def test_matches_scalar_function(self):
        masks = [
            square_mask((20, 20), 2, 12, 2, 12),
            square_mask((20, 20), 7, 17, 7, 17),
            square_mask((20, 20), 0, 3, 15, 18),
        ]
        matrix = segmentation.pairwise_mask_iou(masks)
        for i, a in enumerate(masks):
            for j, b in enumerate(masks):
                if i == j:
                    assert matrix[i, j] == pytest.approx(1.0)
                else:
                    assert matrix[i, j] == pytest.approx(segmentation.mask_iou(a, b), abs=1e-9)

    def test_missing_masks_stay_zero(self):
        masks = [square_mask((20, 20), 0, 10, 0, 10), None]
        matrix = segmentation.pairwise_mask_iou(masks)
        assert matrix.shape == (2, 2)
        assert matrix[0, 1] == 0.0
        assert matrix[1, 1] == 0.0

    def test_matrix_is_symmetric(self):
        masks = [
            square_mask((16, 16), 0, 8, 0, 8),
            square_mask((16, 16), 4, 12, 4, 12),
        ]
        matrix = segmentation.pairwise_mask_iou(masks)
        assert np.allclose(matrix, matrix.T)

    def test_empty_input(self):
        assert segmentation.pairwise_mask_iou([]).shape == (0, 0)


class TestMaskProjection:
    def test_letterbox_padding_is_removed(self):
        """A letterboxed mask must map back without stretching the padding.

        Ultralytics returns masks on a padded canvas. A 300x200 image at
        imgsz=640 yields a 448x640 mask whose content occupies only the middle
        rows; a naive resize would stretch the blank padding into the image.
        """
        image_w, image_h = 300, 200
        scale = 640 / image_w
        content_h = int(round(image_h * scale))  # 427
        mask_h = 448
        pad = (mask_h - content_h) // 2

        network_mask = np.zeros((mask_h, 640), dtype=np.float32)
        # Mark the full content region so correct un-padding yields an all-ones
        # mask at original resolution.
        network_mask[pad : pad + content_h, :] = 1.0

        projected = project_mask(network_mask, image_w, image_h)
        assert projected.shape == (image_h, image_w)
        # Nearly every pixel should be set; a naive resize would leave the
        # padding rows blank and score far lower.
        assert projected.mean() > 0.98

    def test_already_correct_size_is_binarized_only(self):
        mask = np.zeros((50, 60), dtype=np.float32)
        mask[10:20, 10:20] = 0.9
        projected = project_mask(mask, 60, 50)
        assert projected.shape == (50, 60)
        assert projected.sum() == 100

    def test_square_input_needs_no_padding(self):
        mask = np.ones((64, 64), dtype=np.float32)
        assert project_mask(mask, 32, 32).shape == (32, 32)

    def test_rejects_non_2d(self):
        with pytest.raises(ValueError):
            project_mask(np.ones((2, 10, 10), dtype=np.float32), 10, 10)

    def test_rejects_invalid_target(self):
        with pytest.raises(ValueError):
            project_mask(np.ones((10, 10), dtype=np.float32), 0, 10)


class TestCrops:
    def test_bbox_crop_dimensions(self):
        image = np.full((100, 120, 3), 50, dtype=np.uint8)
        crop = segmentation.extract_bbox_crop(image, (10, 20, 40, 60))
        assert crop.shape == (40, 30, 3)

    def test_bbox_crop_with_padding_grows(self):
        image = np.full((100, 120, 3), 50, dtype=np.uint8)
        plain = segmentation.extract_bbox_crop(image, (30, 30, 50, 50))
        padded = segmentation.extract_bbox_crop(image, (30, 30, 50, 50), pad_frac=0.5)
        assert padded.shape[0] > plain.shape[0]

    def test_degenerate_box_returns_none(self):
        image = np.full((100, 120, 3), 50, dtype=np.uint8)
        assert segmentation.extract_bbox_crop(image, (50, 50, 50, 50)) is None

    def test_out_of_bounds_box_returns_none(self):
        image = np.full((100, 120, 3), 50, dtype=np.uint8)
        assert segmentation.extract_bbox_crop(image, (500, 500, 600, 600)) is None

    def test_masked_crop_zeroes_the_background(self):
        image = np.full((40, 40, 3), 200, dtype=np.uint8)
        mask = square_mask((40, 40), 10, 20, 10, 20)
        crop = segmentation.extract_masked_crop(image, (10, 10, 20, 20), mask)
        assert crop.shape == (10, 10, 3)
        # Fully covered by the mask, so nothing is zeroed.
        assert (crop == 200).all()

        wider = segmentation.extract_masked_crop(image, (5, 5, 25, 25), mask)
        # Now the box extends past the mask, so some pixels must be background.
        assert (wider == 0).any()
        assert (wider == 200).any()

    def test_masked_crop_falls_back_without_a_mask(self):
        image = np.full((40, 40, 3), 200, dtype=np.uint8)
        crop = segmentation.extract_masked_crop(image, (10, 10, 20, 20), None)
        assert (crop == 200).all()

    def test_all_zero_mask_falls_back_to_bbox_crop(self):
        # A blank crop carries less information than the bbox crop, so the
        # bbox crop is returned instead of a black square.
        image = np.full((40, 40, 3), 200, dtype=np.uint8)
        crop = segmentation.extract_masked_crop(
            image, (10, 10, 20, 20), np.zeros((40, 40), dtype=np.uint8)
        )
        assert (crop == 200).all()


class TestMaskStatistics:
    def test_low_occupancy_mask_is_distrusted(self):
        from vision.config import config_for_mode

        config = config_for_mode("BALANCED")
        thin = np.zeros((100, 100), dtype=np.uint8)
        thin[0:1, 0:2] = 1  # 2 px inside a 100-unit box -> 2% occupancy
        good = np.ones((100, 100), dtype=np.uint8)

        proposals = [
            Proposal(bbox=(0, 0, 10, 10), confidence=0.5, mask=thin, proposal_id=0),
            Proposal(bbox=(0, 0, 10, 10), confidence=0.5, mask=good, proposal_id=1),
            Proposal(bbox=(0, 0, 10, 10), confidence=0.5, mask=None, proposal_id=2),
        ]
        segmentation.attach_mask_statistics(proposals, config)

        assert proposals[0].metadata["mask_trusted"] is False
        assert proposals[1].metadata["mask_trusted"] is True
        assert proposals[2].metadata["mask_trusted"] is False

    def test_trusted_masks_filters_distrusted(self):
        from vision.config import config_for_mode

        config = config_for_mode("BALANCED")
        thin = np.zeros((100, 100), dtype=np.uint8)
        thin[0:1, 0:2] = 1
        proposals = [
            Proposal(bbox=(0, 0, 10, 10), confidence=0.5, mask=thin, proposal_id=0),
            Proposal(bbox=(0, 0, 10, 10), confidence=0.5, mask=np.ones((100, 100), np.uint8), proposal_id=1),
        ]
        segmentation.attach_mask_statistics(proposals, config)
        masks = segmentation.trusted_masks(proposals)
        assert masks[0] is None
        assert masks[1] is not None


class TestMergeMasks:
    def test_union_of_masks(self):
        a = square_mask((20, 20), 0, 10, 0, 10)
        b = square_mask((20, 20), 10, 20, 10, 20)
        merged = segmentation.merge_masks([a, b])
        assert merged.sum() == 200

    def test_ignores_missing_masks(self):
        a = square_mask((20, 20), 0, 10, 0, 10)
        assert segmentation.merge_masks([a, None]).sum() == 100

    def test_all_missing_returns_none(self):
        assert segmentation.merge_masks([None, None]) is None

    def test_shape_mismatch_raises(self):
        with pytest.raises(ValueError):
            segmentation.merge_masks([np.ones((10, 10), np.uint8), np.ones((20, 20), np.uint8)])
