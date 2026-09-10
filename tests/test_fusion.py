"""Tests for the box fusion operators and the coarse IoU pre-fusion pass."""

from __future__ import annotations

import numpy as np
import pytest

from vision import fusion
from vision.proposals import Proposal, assign_ids


def make_proposals(specs):
    """Build proposals from ``(bbox, confidence)`` pairs with sequential IDs."""
    return assign_ids([Proposal(bbox=bbox, confidence=conf) for bbox, conf in specs])


class TestWeightedBoxFusion:
    def test_single_box_is_returned_unchanged(self):
        bbox, conf = fusion.weighted_box_fusion([[1, 2, 3, 4]], [0.7])
        assert bbox == (1.0, 2.0, 3.0, 4.0)
        assert conf == pytest.approx(0.7)

    def test_equal_weights_give_the_midpoint(self):
        bbox, _ = fusion.weighted_box_fusion([[0, 0, 10, 10], [10, 10, 20, 20]], [0.5, 0.5])
        assert bbox == pytest.approx((5.0, 5.0, 15.0, 15.0))

    def test_result_is_pulled_toward_the_confident_box(self):
        bbox, _ = fusion.weighted_box_fusion([[0, 0, 10, 10], [10, 10, 20, 20]], [0.9, 0.1])
        # 0.9 weight on the first box puts the result one tenth of the way over.
        assert bbox == pytest.approx((1.0, 1.0, 11.0, 11.0))

    def test_confidence_is_the_mean_not_the_max(self):
        # WBF convention: agreement between passes is what the score reflects.
        _, conf = fusion.weighted_box_fusion([[0, 0, 10, 10], [1, 1, 11, 11]], [0.9, 0.1])
        assert conf == pytest.approx(0.5)

    def test_never_exceeds_the_enclosing_union(self):
        # This is the key property that distinguishes WBF from union merging:
        # averaging cannot inflate a box beyond its members.
        boxes = [[0, 0, 10, 10], [4, 4, 14, 14], [2, 6, 12, 16]]
        bbox, _ = fusion.weighted_box_fusion(boxes, [0.5, 0.5, 0.5])
        array = np.asarray(boxes, dtype=float)
        assert bbox[0] >= array[:, 0].min() and bbox[1] >= array[:, 1].min()
        assert bbox[2] <= array[:, 2].max() and bbox[3] <= array[:, 3].max()

    def test_all_zero_scores_fall_back_to_unweighted_mean(self):
        bbox, conf = fusion.weighted_box_fusion([[0, 0, 10, 10], [10, 10, 20, 20]], [0.0, 0.0])
        assert bbox == pytest.approx((5.0, 5.0, 15.0, 15.0))
        assert conf == 0.0

    def test_rejects_empty_input(self):
        with pytest.raises(ValueError):
            fusion.weighted_box_fusion([], [])

    def test_rejects_mismatched_lengths(self):
        with pytest.raises(ValueError, match="scores"):
            fusion.weighted_box_fusion([[0, 0, 1, 1], [0, 0, 2, 2]], [0.5])


class TestUnionFusion:
    def test_union_is_the_outer_envelope(self):
        bbox, conf = fusion.union_fusion([[0, 0, 10, 10], [20, 20, 30, 30]], [0.3, 0.7])
        assert bbox == (0.0, 0.0, 30.0, 30.0)

    def test_confidence_is_the_max(self):
        # A fragmented object is as likely as its most convincing piece.
        _, conf = fusion.union_fusion([[0, 0, 10, 10], [9, 0, 19, 10]], [0.3, 0.7])
        assert conf == pytest.approx(0.7)

    def test_rejects_empty_input(self):
        with pytest.raises(ValueError):
            fusion.union_fusion([], [])


class TestSelectByConfidence:
    def test_picks_the_most_confident(self):
        members = make_proposals([((0, 0, 10, 10), 0.4), ((0, 0, 40, 40), 0.9)])
        bbox, conf, chosen = fusion.select_by_confidence(members)
        assert conf == pytest.approx(0.9)
        assert bbox == (0.0, 0.0, 40.0, 40.0)
        assert chosen is members[1]

    def test_ties_prefer_the_larger_box(self):
        # A generous crop is recoverable downstream; a too-tight one is not.
        members = make_proposals([((0, 0, 10, 10), 0.5), ((0, 0, 40, 40), 0.5)])
        bbox, _, _ = fusion.select_by_confidence(members)
        assert bbox == (0.0, 0.0, 40.0, 40.0)


class TestChooseOperator:
    def test_union_dominates(self):
        reasons = {fusion.MERGE_FRAGMENT_UNION, fusion.MERGE_CONTAINMENT, fusion.MERGE_WBF}
        assert fusion.choose_operator(reasons) == "union"

    def test_pure_containment_selects(self):
        assert fusion.choose_operator({fusion.MERGE_CONTAINMENT}) == "select"
        assert fusion.choose_operator({fusion.MERGE_CONTAINMENT_CLIP}) == "select"

    def test_mixed_containment_and_overlap_averages(self):
        assert fusion.choose_operator({fusion.MERGE_CONTAINMENT, fusion.MERGE_IOU}) == "wbf"

    def test_default_is_wbf(self):
        assert fusion.choose_operator(set()) == "wbf"


class TestFuseCluster:
    def test_single_member_is_marked_canonical(self):
        members = make_proposals([((0, 0, 10, 10), 0.8)])
        result = fusion.fuse_cluster(members)
        assert result is members[0]
        assert result.is_canonical

    def test_anchor_payload_is_preserved(self):
        mask = np.ones((10, 10), dtype=np.uint8)
        embedding = np.array([1.0, 0.0], dtype=np.float32)
        high = Proposal(bbox=(0, 0, 10, 10), confidence=0.9, proposal_id=0,
                        mask=mask, embedding=embedding, source_scale=960)
        low = Proposal(bbox=(1, 1, 11, 11), confidence=0.2, proposal_id=1)
        result = fusion.fuse_cluster([high, low], [fusion.MERGE_WBF])
        # The highest-confidence member anchors, so its mask/embedding survive.
        assert result.proposal_id == 0
        assert result.mask is mask
        assert result.embedding is embedding
        assert result.source_scale == 960
        assert result.merged_from == [1]
        assert result.metadata["cluster_size"] == 2

    def test_fragment_cluster_unions(self):
        members = make_proposals([((0, 0, 10, 20), 0.6), ((8, 0, 18, 20), 0.5)])
        result = fusion.fuse_cluster(members, [fusion.MERGE_FRAGMENT_UNION])
        assert result.bbox == (0.0, 0.0, 18.0, 20.0)
        assert result.merge_reason == fusion.MERGE_FRAGMENT_UNION
        assert result.metadata["fusion_operator"] == "union"

    def test_rejects_empty_cluster(self):
        with pytest.raises(ValueError):
            fusion.fuse_cluster([])


class TestFuseByIoU:
    def test_empty_input(self):
        assert fusion.fuse_by_iou([], 0.5) == []

    def test_single_proposal_gets_a_cluster_id(self):
        proposals = make_proposals([((0, 0, 10, 10), 0.5)])
        result = fusion.fuse_by_iou(proposals, 0.5)
        assert len(result) == 1
        assert result[0].cluster_id == 0

    def test_high_overlap_collapses(self):
        proposals = make_proposals([((0, 0, 100, 100), 0.9), ((3, 3, 103, 103), 0.5)])
        result = fusion.fuse_by_iou(proposals, 0.55)
        assert len(result) == 1
        assert result[0].merge_reason == fusion.MERGE_WBF

    def test_low_overlap_is_left_alone(self):
        proposals = make_proposals([((0, 0, 100, 100), 0.9), ((90, 90, 190, 190), 0.5)])
        assert len(fusion.fuse_by_iou(proposals, 0.55)) == 2

    def test_transitive_chain_forms_one_cluster(self):
        # A-B and B-C both exceed the threshold while A-C does not. Union-find
        # must still place all three together.
        proposals = make_proposals([
            ((0, 0, 100, 100), 0.9),
            ((15, 0, 115, 100), 0.8),
            ((30, 0, 130, 100), 0.7),
        ])
        result = fusion.fuse_by_iou(proposals, 0.5)
        assert len(result) == 1
        assert result[0].metadata["cluster_size"] == 3

    def test_output_is_sorted_by_confidence(self):
        proposals = make_proposals([
            ((0, 0, 10, 10), 0.2),
            ((500, 500, 510, 510), 0.9),
            ((900, 900, 910, 910), 0.5),
        ])
        result = fusion.fuse_by_iou(proposals, 0.55)
        confidences = [p.confidence for p in result]
        assert confidences == sorted(confidences, reverse=True)

    def test_result_is_order_independent(self):
        specs = [
            ((0, 0, 100, 100), 0.9),
            ((5, 5, 105, 105), 0.7),
            ((400, 400, 500, 500), 0.6),
        ]
        forward = fusion.fuse_by_iou(make_proposals(specs), 0.5)
        backward = fusion.fuse_by_iou(make_proposals(list(reversed(specs))), 0.5)
        assert len(forward) == len(backward)


class TestGreedyBaseline:
    def test_suppresses_overlapping_boxes(self):
        proposals = make_proposals([((0, 0, 100, 100), 0.9), ((5, 5, 105, 105), 0.5)])
        result = fusion.greedy_iou_suppression(proposals, 0.5)
        assert len(result) == 1
        # Greedy keeps the highest-confidence box *unchanged* rather than
        # fusing, which is the behaviour the ablation measures against.
        assert result[0].bbox == (0.0, 0.0, 100.0, 100.0)
        assert result[0].confidence == pytest.approx(0.9)
        assert result[0].merge_reason == fusion.MERGE_IOU

    def test_keeps_distinct_boxes(self):
        proposals = make_proposals([((0, 0, 10, 10), 0.9), ((500, 500, 510, 510), 0.5)])
        assert len(fusion.greedy_iou_suppression(proposals, 0.5)) == 2

    def test_empty_input(self):
        assert fusion.greedy_iou_suppression([], 0.5) == []
