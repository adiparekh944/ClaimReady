"""Tests for the deduplication decision rule.

Each of the five clauses is tested in isolation, and — more importantly — so
are the cases that must **not** merge. Over-merging silently deletes an
inventory item and its value, so the negative tests are the ones that protect
the product.
"""

from __future__ import annotations

import numpy as np
import pytest

from vision import geometry
from vision.config import config_for_mode
from vision.deduplication import MERGE_IOU_CLIP, Deduplicator
from vision.fusion import (
    MERGE_CONTAINMENT_CLIP,
    MERGE_FRAGMENT_UNION,
    MERGE_IOU,
    MERGE_MASK_OVERLAP,
)
from vision.proposals import Proposal, assign_ids


def build(specs, masks=None):
    proposals = []
    for index, (bbox, conf) in enumerate(specs):
        mask = masks[index] if masks else None
        proposals.append(Proposal(bbox=bbox, confidence=conf, mask=mask))
    return assign_ids(proposals)


def similarity_matrix(count, pairs=None, default=0.0):
    matrix = np.full((count, count), default, dtype=np.float32)
    np.fill_diagonal(matrix, 1.0)
    for (i, j), value in (pairs or {}).items():
        matrix[i, j] = matrix[j, i] = value
    return matrix


@pytest.fixture
def dedup(balanced_config):
    return Deduplicator(balanced_config)


class TestTrivialCases:
    def test_empty_input(self, dedup):
        result = dedup.deduplicate([])
        assert result.output_count == 0
        assert result.duplicates_removed == 0

    def test_single_proposal_is_canonical(self, dedup):
        proposals = build([((0, 0, 10, 10), 0.5)])
        result = dedup.deduplicate(proposals)
        assert result.output_count == 1
        assert result.proposals[0].is_canonical
        assert result.proposals[0].cluster_id == 0

    def test_distant_proposals_stay_separate(self, dedup):
        proposals = build([((0, 0, 10, 10), 0.9), ((500, 500, 510, 510), 0.8)])
        assert dedup.deduplicate(proposals).output_count == 2


class TestClauseOneHighIoU:
    def test_high_iou_merges_without_appearance(self, dedup):
        proposals = build([((0, 0, 100, 100), 0.9), ((5, 5, 105, 105), 0.6)])
        assert geometry.iou(proposals[0].bbox, proposals[1].bbox) >= 0.6
        result = dedup.deduplicate(proposals, None)
        assert result.output_count == 1
        assert result.reason_counts() == {MERGE_IOU: 1}

    def test_high_iou_merges_even_when_appearance_disagrees(self, dedup):
        # Geometry this strong is decisive on its own; the boxes describe the
        # same region so they cannot be two separate items.
        proposals = build([((0, 0, 100, 100), 0.9), ((5, 5, 105, 105), 0.6)])
        result = dedup.deduplicate(proposals, similarity_matrix(2, {(0, 1): 0.1}))
        assert result.output_count == 1


class TestClauseTwoMaskOverlap:
    def test_mask_agreement_merges(self, dedup):
        mask = np.zeros((200, 200), dtype=np.uint8)
        mask[10:110, 10:110] = 1
        shifted = np.zeros((200, 200), dtype=np.uint8)
        shifted[14:114, 14:114] = 1

        # Boxes chosen so box IoU alone would not trigger clause 1.
        proposals = build(
            [((0, 0, 120, 120), 0.9), ((30, 30, 130, 130), 0.6)],
            masks=[mask, shifted],
        )
        from vision import segmentation

        segmentation.attach_mask_statistics(proposals, dedup.config)
        result = dedup.deduplicate(proposals, None)
        assert result.output_count == 1
        assert MERGE_MASK_OVERLAP in result.reason_counts()

    def test_distrusted_masks_are_ignored(self, dedup):
        # A mask covering almost none of its own box is a failed segmentation,
        # so it must not be treated as evidence.
        from vision import segmentation

        thin = np.zeros((200, 200), dtype=np.uint8)
        thin[0:1, 0:2] = 1
        proposals = build(
            [((0, 0, 120, 120), 0.9), ((300, 300, 420, 420), 0.6)],
            masks=[thin, thin.copy()],
        )
        segmentation.attach_mask_statistics(proposals, dedup.config)
        assert all(not p.metadata["mask_trusted"] for p in proposals)
        assert dedup.deduplicate(proposals, None).output_count == 2


class TestClauseThreeModerateIoUPlusAppearance:
    SPECS = [((0, 0, 100, 100), 0.9), ((35, 0, 135, 100), 0.5)]

    def test_moderate_iou_with_similar_appearance_merges(self, dedup):
        proposals = build(self.SPECS)
        pair_iou = geometry.iou(proposals[0].bbox, proposals[1].bbox)
        assert 0.30 <= pair_iou < 0.60  # in the moderate band
        result = dedup.deduplicate(proposals, similarity_matrix(2, {(0, 1): 0.96}))
        assert result.output_count == 1
        assert result.reason_counts() == {MERGE_IOU_CLIP: 1}

    def test_moderate_iou_with_different_appearance_stays_separate(self, dedup):
        proposals = build(self.SPECS)
        result = dedup.deduplicate(proposals, similarity_matrix(2, {(0, 1): 0.50}))
        assert result.output_count == 2

    def test_without_embeddings_moderate_iou_does_not_merge(self, dedup):
        # FAST mode has no appearance model, so this clause is unreachable and
        # the behaviour degrades to geometry-only rather than merging blindly.
        proposals = build(self.SPECS)
        assert dedup.deduplicate(proposals, None).output_count == 2

    def test_size_guard_blocks_absorbing_a_much_smaller_box(self, dedup):
        # Two similar-looking cushions, one near and one far. They overlap and
        # look alike, but the size disparity says they are different objects.
        proposals = build([((0, 0, 200, 200), 0.9), ((10, 10, 60, 60), 0.8)])
        result = dedup.deduplicate(proposals, similarity_matrix(2, {(0, 1): 0.99}))
        # Merges via containment (fully nested + identical), not via clause 3.
        assert MERGE_IOU_CLIP not in result.reason_counts()


class TestClauseFourContainment:
    NESTED = [((0, 0, 400, 400), 0.8), ((50, 50, 110, 110), 0.7)]

    def test_nested_and_identical_merges(self, dedup):
        proposals = build(self.NESTED)
        assert geometry.containment(proposals[1].bbox, proposals[0].bbox) > 0.9
        result = dedup.deduplicate(proposals, similarity_matrix(2, {(0, 1): 0.99}))
        assert result.output_count == 1
        assert result.reason_counts() == {MERGE_CONTAINMENT_CLIP: 1}

    def test_object_on_a_surface_is_not_merged(self, dedup):
        """A phone on a desk is contained in the desk but is a separate item.

        This is the single most important negative case: nearly everything in a
        room is contained in some larger object's box, so containment without
        appearance agreement must never merge.
        """
        proposals = build(self.NESTED)
        result = dedup.deduplicate(proposals, similarity_matrix(2, {(0, 1): 0.60}))
        assert result.output_count == 2

    def test_containment_needs_the_strict_threshold(self, dedup):
        # Above the ordinary similarity threshold but below the strict one.
        config = dedup.config
        between = (config.embedding_similarity_threshold + config.embedding_strict_threshold) / 2
        proposals = build(self.NESTED)
        result = dedup.deduplicate(proposals, similarity_matrix(2, {(0, 1): between}))
        assert result.output_count == 2

    def test_without_embeddings_nesting_never_merges(self, dedup):
        proposals = build(self.NESTED)
        assert dedup.deduplicate(proposals, None).output_count == 2


class TestClauseFiveFragments:
    FRAGMENTS = [((0, 0, 100, 200), 0.6), ((75, 0, 175, 200), 0.6)]

    def test_overlapping_fragments_with_similar_appearance_union(self, dedup):
        proposals = build(self.FRAGMENTS)
        pair_iou = geometry.iou(proposals[0].bbox, proposals[1].bbox)
        assert 0.10 <= pair_iou < 0.30
        result = dedup.deduplicate(proposals, similarity_matrix(2, {(0, 1): 0.95}))
        assert result.output_count == 1
        assert result.reason_counts() == {MERGE_FRAGMENT_UNION: 1}
        # Union, so the result must enclose both fragments.
        assert result.proposals[0].bbox == (0.0, 0.0, 175.0, 200.0)

    def test_fragments_with_different_appearance_stay_separate(self, dedup):
        proposals = build(self.FRAGMENTS)
        assert dedup.deduplicate(proposals, similarity_matrix(2, {(0, 1): 0.6})).output_count == 2

    def test_disabling_fragment_union_stops_the_clause(self, balanced_config):
        dedup = Deduplicator(balanced_config.with_overrides(enable_fragment_union=False))
        proposals = build(self.FRAGMENTS)
        result = dedup.deduplicate(proposals, similarity_matrix(2, {(0, 1): 0.95}))
        assert result.output_count == 2


class TestOverMergeProtection:
    def test_row_of_identical_non_overlapping_objects(self, dedup):
        """Three identical chairs side by side must remain three items.

        They are visually indistinguishable, so appearance alone would merge
        them. What prevents it is that distinct adjacent objects do not
        overlap, so no clause is ever reached.
        """
        proposals = build([
            ((0, 0, 100, 150), 0.7),
            ((110, 0, 210, 150), 0.7),
            ((220, 0, 320, 150), 0.7),
        ])
        matrix = similarity_matrix(3, {(0, 1): 0.99, (1, 2): 0.99, (0, 2): 0.99})
        result = dedup.deduplicate(proposals, matrix)
        assert result.output_count == 3

    def test_appearance_alone_never_merges(self, dedup):
        # Identical embeddings, no geometric relationship whatsoever.
        proposals = build([((0, 0, 50, 50), 0.8), ((900, 900, 950, 950), 0.8)])
        matrix = similarity_matrix(2, {(0, 1): 1.0})
        assert dedup.deduplicate(proposals, matrix).output_count == 2


class TestClusteringProperties:
    def test_transitive_merging(self, dedup):
        proposals = build([
            ((0, 0, 100, 100), 0.9),
            ((12, 0, 112, 100), 0.8),
            ((24, 0, 124, 100), 0.7),
        ])
        result = dedup.deduplicate(proposals, None)
        assert result.output_count == 1

    def test_output_sorted_by_confidence(self, dedup):
        proposals = build([
            ((0, 0, 10, 10), 0.2),
            ((500, 500, 510, 510), 0.9),
            ((900, 900, 910, 910), 0.5),
        ])
        result = dedup.deduplicate(proposals, None)
        confidences = [p.confidence for p in result.proposals]
        assert confidences == sorted(confidences, reverse=True)

    def test_cluster_ids_are_assigned(self, dedup):
        proposals = build([((0, 0, 10, 10), 0.9), ((500, 500, 510, 510), 0.8)])
        result = dedup.deduplicate(proposals, None)
        assert sorted(p.cluster_id for p in result.proposals) == [0, 1]

    def test_merge_records_capture_the_signals(self, dedup):
        proposals = build([((0, 0, 100, 100), 0.9), ((5, 5, 105, 105), 0.6)])
        result = dedup.deduplicate(proposals, similarity_matrix(2, {(0, 1): 0.97}))
        assert len(result.merges) == 1
        record = result.merges[0].to_dict()
        assert record["reason"] == MERGE_IOU
        assert record["iou"] > 0.6
        assert record["similarity"] == pytest.approx(0.97, abs=1e-3)

    def test_result_is_json_serializable(self, dedup):
        import json

        proposals = build([((0, 0, 100, 100), 0.9), ((5, 5, 105, 105), 0.6)])
        json.dumps(dedup.deduplicate(proposals, None).to_dict())

    def test_wrong_similarity_shape_raises(self, dedup):
        proposals = build([((0, 0, 10, 10), 0.9), ((50, 50, 60, 60), 0.8)])
        with pytest.raises(ValueError, match="similarity must be"):
            dedup.deduplicate(proposals, np.eye(5, dtype=np.float32))

    def test_similarity_ignored_when_embeddings_disabled(self, balanced_config):
        dedup = Deduplicator(balanced_config.with_overrides(enable_embeddings=False))
        proposals = build([((0, 0, 400, 400), 0.8), ((50, 50, 110, 110), 0.7)])
        # Would merge via containment+clip if the matrix were honoured.
        result = dedup.deduplicate(proposals, similarity_matrix(2, {(0, 1): 0.99}))
        assert result.output_count == 2
