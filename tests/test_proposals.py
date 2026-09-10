"""Tests for the Proposal record and union-find clustering."""

from __future__ import annotations

import numpy as np
import pytest

from vision.proposals import (
    Proposal,
    UnionFind,
    assign_ids,
    boxes_array,
    cap_proposals,
    cluster_from_pairs,
    filter_small,
)


class TestProposal:
    def test_inverted_coordinates_are_normalized(self):
        # Silently repairing this is safer than raising inside a request path.
        proposal = Proposal(bbox=(100, 80, 10, 20), confidence=0.5)
        assert proposal.bbox == (10.0, 20.0, 100.0, 80.0)

    def test_derived_geometry(self):
        proposal = Proposal(bbox=(10, 20, 30, 60), confidence=0.5)
        assert proposal.width == 20.0
        assert proposal.height == 40.0
        assert proposal.area == 800.0
        assert proposal.center == (20.0, 40.0)

    def test_no_mask_by_default(self):
        proposal = Proposal(bbox=(0, 0, 10, 10), confidence=0.5)
        assert not proposal.has_mask
        assert not proposal.has_embedding
        assert proposal.mask_area == 0.0
        assert proposal.mask_occupancy == 0.0

    def test_mask_occupancy(self):
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[0:10, 0:5] = 1  # 50 pixels inside a 100-unit box
        proposal = Proposal(bbox=(0, 0, 10, 10), confidence=0.5, mask=mask)
        assert proposal.mask_area == 50.0
        assert proposal.mask_occupancy == pytest.approx(0.5)

    def test_zero_area_box_has_zero_occupancy(self):
        mask = np.ones((10, 10), dtype=np.uint8)
        proposal = Proposal(bbox=(5, 5, 5, 5), confidence=0.5, mask=mask)
        assert proposal.mask_occupancy == 0.0

    def test_clipped_bbox_respects_bounds(self):
        proposal = Proposal(bbox=(-5, -5, 500, 500), confidence=0.5)
        assert proposal.clipped_bbox(100, 50) == (0, 0, 100, 50)

    def test_to_dict_omits_arrays_by_default(self):
        proposal = Proposal(
            bbox=(0, 0, 10, 10),
            confidence=0.5,
            embedding=np.array([1.0, 0.0], dtype=np.float32),
        )
        payload = proposal.to_dict()
        assert payload["has_embedding"] is True
        assert "embedding" not in payload
        assert proposal.to_dict(include_arrays=True)["embedding"] == [1.0, 0.0]

    def test_to_dict_is_json_serializable(self):
        import json

        proposal = Proposal(bbox=(0, 0, 10, 10), confidence=0.5, mask=np.ones((10, 10), np.uint8))
        json.dumps(proposal.to_dict())


class TestHelpers:
    def test_assign_ids_is_sequential(self):
        proposals = [Proposal(bbox=(0, 0, 1, 1), confidence=0.5) for _ in range(4)]
        assign_ids(proposals, start=10)
        assert [p.proposal_id for p in proposals] == [10, 11, 12, 13]

    def test_boxes_array_shape(self):
        proposals = [Proposal(bbox=(0, 0, 10, 10), confidence=0.5) for _ in range(3)]
        assert boxes_array(proposals).shape == (3, 4)

    def test_boxes_array_of_nothing(self):
        assert boxes_array([]).shape == (0, 4)

    def test_filter_small_drops_below_threshold(self):
        proposals = [
            Proposal(bbox=(0, 0, 2, 2), confidence=0.5),   # area 4
            Proposal(bbox=(0, 0, 20, 20), confidence=0.5),  # area 400
        ]
        assert len(filter_small(proposals, 64)) == 1

    def test_cap_keeps_highest_confidence(self):
        proposals = [Proposal(bbox=(0, 0, 10, 10), confidence=c) for c in (0.1, 0.9, 0.5, 0.7)]
        capped = cap_proposals(proposals, 2)
        assert [p.confidence for p in capped] == [0.9, 0.7]

    def test_cap_is_a_no_op_below_the_limit(self):
        proposals = [Proposal(bbox=(0, 0, 10, 10), confidence=0.5) for _ in range(3)]
        assert len(cap_proposals(proposals, 10)) == 3

    def test_cap_of_zero_or_less_disables_capping(self):
        proposals = [Proposal(bbox=(0, 0, 10, 10), confidence=0.5) for _ in range(3)]
        assert len(cap_proposals(proposals, 0)) == 3


class TestUnionFind:
    def test_starts_fully_disconnected(self):
        uf = UnionFind(5)
        assert uf.num_components == 5
        assert uf.groups() == [[0], [1], [2], [3], [4]]

    def test_union_joins_components(self):
        uf = UnionFind(5)
        assert uf.union(0, 1) is True
        assert uf.num_components == 4
        assert uf.connected(0, 1)

    def test_redundant_union_returns_false(self):
        uf = UnionFind(3)
        uf.union(0, 1)
        assert uf.union(1, 0) is False
        assert uf.num_components == 2

    def test_transitivity(self):
        uf = UnionFind(4)
        uf.union(0, 1)
        uf.union(1, 2)
        # 0 and 2 were never compared directly.
        assert uf.connected(0, 2)
        assert uf.groups() == [[0, 1, 2], [3]]

    def test_component_size(self):
        uf = UnionFind(4)
        uf.union(0, 1)
        uf.union(2, 3)
        uf.union(1, 3)
        assert uf.component_size(0) == 4

    def test_groups_are_deterministic_regardless_of_union_order(self):
        forward = UnionFind(6)
        for a, b in [(0, 1), (1, 2), (3, 4)]:
            forward.union(a, b)
        backward = UnionFind(6)
        for a, b in [(3, 4), (2, 1), (1, 0)]:
            backward.union(a, b)
        assert forward.groups() == backward.groups()

    def test_out_of_range_index_raises(self):
        uf = UnionFind(3)
        with pytest.raises(IndexError):
            uf.find(5)

    def test_negative_size_raises(self):
        with pytest.raises(ValueError):
            UnionFind(-1)

    def test_zero_size(self):
        uf = UnionFind(0)
        assert uf.groups() == []
        assert uf.num_components == 0

    def test_large_chain_does_not_recurse(self):
        # Path compression is iterative, so a long chain must not blow the
        # Python stack the way a recursive find() would.
        size = 5000
        uf = UnionFind(size)
        for i in range(size - 1):
            uf.union(i, i + 1)
        assert uf.num_components == 1
        assert uf.component_size(0) == size

    def test_cluster_from_pairs(self):
        assert cluster_from_pairs(5, [(0, 1), (3, 4)]) == [[0, 1], [2], [3, 4]]

    def test_cluster_from_no_pairs(self):
        assert cluster_from_pairs(3, []) == [[0], [1], [2]]
