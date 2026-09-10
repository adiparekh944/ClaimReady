"""Tests for tile planning, multi-scale scheduling and coordinate projection.

Inference is stubbed with ``FakeYOLO`` (see conftest) so no weights are
downloaded. What is verified is the scheduling and coordinate handling around
the model, which is where the real bugs live.
"""

from __future__ import annotations

import numpy as np
import pytest

from vision.config import PipelineMode, config_for_mode
from vision.detector import ProposalDetector, plan_tiles
from vision.proposals import (
    SOURCE_FULL_FRAME,
    SOURCE_SECONDARY,
    SOURCE_TILE,
)


class TestPlanTiles:
    @pytest.mark.parametrize("width,height", [(4000, 3000), (1920, 1080), (2500, 900), (800, 600)])
    def test_tiles_cover_the_whole_image(self, width, height):
        tiles = plan_tiles(width, height, 768, 0.25, 64)
        covered = np.zeros((height, width), dtype=bool)
        for x1, y1, x2, y2 in tiles:
            covered[y1:y2, x1:x2] = True
        assert covered.all(), "tiling left part of the image unexamined"

    @pytest.mark.parametrize("width,height", [(4000, 3000), (1920, 1080), (500, 500)])
    def test_tiles_stay_inside_the_image(self, width, height):
        for x1, y1, x2, y2 in plan_tiles(width, height, 768, 0.25, 64):
            assert 0 <= x1 < x2 <= width
            assert 0 <= y1 < y2 <= height

    def test_small_image_yields_one_tile(self):
        assert plan_tiles(400, 300, 768, 0.25, 24) == [(0, 0, 400, 300)]

    def test_tile_count_respects_the_cap(self):
        tiles = plan_tiles(8000, 6000, 512, 0.25, 12)
        assert len(tiles) <= 12

    def test_capped_tiling_still_covers_the_image(self):
        # Degrading to fewer, larger tiles must not silently drop regions,
        # which would lose recall in whichever part came last.
        width, height = 6000, 4000
        tiles = plan_tiles(width, height, 512, 0.25, 8)
        covered = np.zeros((height, width), dtype=bool)
        for x1, y1, x2, y2 in tiles:
            covered[y1:y2, x1:x2] = True
        assert covered.all()

    def test_overlap_produces_adjacent_tiles_that_intersect(self):
        tiles = plan_tiles(2000, 800, 768, 0.25, 64)
        xs = sorted({t[0] for t in tiles})
        assert len(xs) >= 2
        # Stride is smaller than the tile, so consecutive origins are closer
        # together than the tile width.
        assert xs[1] - xs[0] < 768

    def test_zero_overlap_is_allowed(self):
        assert plan_tiles(2000, 2000, 500, 0.0, 64)

    @pytest.mark.parametrize("kwargs", [
        {"tile_size": 0},
        {"overlap": 1.0},
        {"overlap": -0.1},
        {"max_tiles": 0},
    ])
    def test_invalid_parameters_raise(self, kwargs):
        params = {"width": 2000, "height": 2000, "tile_size": 512, "overlap": 0.25, "max_tiles": 24}
        params.update(kwargs)
        with pytest.raises(ValueError):
            plan_tiles(**params)


class TestMultiScaleScheduling:
    def test_fast_mode_runs_one_scale_plus_the_secondary_pass(self, fake_yolo):
        config = config_for_mode(PipelineMode.FAST, model_path="stub.pt")
        detector = ProposalDetector(config, model=fake_yolo)
        result = detector.detect(np.full((400, 600, 3), 120, dtype=np.uint8))

        assert [p.name for p in result.passes] == ["full@640", "secondary@640"]
        assert {c["imgsz"] for c in fake_yolo.calls} == {640}

    def test_balanced_mode_runs_two_scales(self, fake_yolo):
        config = config_for_mode(
            PipelineMode.BALANCED, model_path="stub.pt", enable_preprocessing=False
        )
        detector = ProposalDetector(config, model=fake_yolo)
        result = detector.detect(np.full((400, 600, 3), 120, dtype=np.uint8))

        names = [p.name for p in result.passes]
        assert "full@640" in names and "full@960" in names
        assert {640, 960} <= {c["imgsz"] for c in fake_yolo.calls}

    def test_accurate_mode_runs_three_scales_and_tiles(self, fake_yolo):
        config = config_for_mode(
            PipelineMode.ACCURATE, model_path="stub.pt", enable_preprocessing=False
        )
        detector = ProposalDetector(config, model=fake_yolo)
        result = detector.detect(np.full((1200, 1600, 3), 120, dtype=np.uint8))

        names = [p.name for p in result.passes]
        assert "full@640" in names and "full@960" in names and "full@1280" in names
        assert any(n.startswith("tiled@") for n in names)
        assert result.tiled is True

    def test_detection_is_class_agnostic(self, fake_yolo):
        config = config_for_mode(PipelineMode.FAST, model_path="stub.pt")
        ProposalDetector(config, model=fake_yolo).detect(
            np.full((400, 600, 3), 120, dtype=np.uint8)
        )
        # Every call must suppress by geometry only, ignoring predicted labels.
        assert all(call["agnostic_nms"] for call in fake_yolo.calls)

    def test_secondary_pass_uses_a_lower_confidence(self, fake_yolo):
        config = config_for_mode(PipelineMode.FAST, model_path="stub.pt")
        detector = ProposalDetector(config, model=fake_yolo)
        detector.detect(np.full((400, 600, 3), 120, dtype=np.uint8))

        confidences = [c["conf"] for c in fake_yolo.calls]
        assert min(confidences) == pytest.approx(config.yolo_confidence_secondary)

    def test_secondary_pass_can_be_disabled(self, fake_yolo):
        config = config_for_mode(
            PipelineMode.FAST, model_path="stub.pt", enable_secondary_pass=False
        )
        detector = ProposalDetector(config, model=fake_yolo)
        result = detector.detect(np.full((400, 600, 3), 120, dtype=np.uint8))
        assert [p.name for p in result.passes] == ["full@640"]

    def test_source_labels_are_recorded(self, fake_yolo):
        config = config_for_mode(PipelineMode.FAST, model_path="stub.pt")
        detector = ProposalDetector(config, model=fake_yolo)
        result = detector.detect(np.full((400, 600, 3), 120, dtype=np.uint8))

        sources = result.counts_by_source()
        assert SOURCE_FULL_FRAME in sources
        assert SOURCE_SECONDARY in sources

    def test_proposal_ids_are_unique(self, fake_yolo):
        config = config_for_mode(PipelineMode.FAST, model_path="stub.pt")
        result = ProposalDetector(config, model=fake_yolo).detect(
            np.full((400, 600, 3), 120, dtype=np.uint8)
        )
        ids = [p.proposal_id for p in result.proposals]
        assert len(ids) == len(set(ids))

    def test_empty_image_raises(self, fake_yolo):
        config = config_for_mode(PipelineMode.FAST, model_path="stub.pt")
        detector = ProposalDetector(config, model=fake_yolo)
        with pytest.raises(ValueError):
            detector.detect(np.zeros((0, 0, 3), dtype=np.uint8))


class TestTiledCoordinateProjection:
    def test_tile_detections_land_in_global_coordinates(self, yolo_factory):
        """A tile-local box must be shifted by its tile origin.

        This is the one place the detector must project coordinates itself, so
        a missing offset would place every tiled proposal in the top-left
        corner of the frame.
        """
        # The stub always reports a box at (10, 10, 60, 60) of whatever it is
        # given, so tiled results must appear at each tile's origin plus that.
        model = yolo_factory([[10, 10, 60, 60]], [0.9])
        config = config_for_mode(
            PipelineMode.FAST,
            model_path="stub.pt",
            enable_tiling=True,
            tile_size=400,
            tile_overlap=0.25,
            max_tiles=16,
            enable_secondary_pass=False,
            enable_preprocessing=False,
        )
        detector = ProposalDetector(config, model=model)
        result = detector.detect(np.full((900, 1200, 3), 120, dtype=np.uint8))

        tile_proposals = [p for p in result.proposals if p.source_pass == SOURCE_TILE]
        assert tile_proposals, "no tiled proposals produced"

        # Not every tiled box may sit at the origin, so check that at least one
        # was shifted away from it and that all stay in bounds.
        assert any(p.bbox[0] > 100 for p in tile_proposals)
        for proposal in tile_proposals:
            assert 0 <= proposal.bbox[0] <= 1200
            assert 0 <= proposal.bbox[1] <= 900
            assert proposal.bbox[2] <= 1200 + 1
            assert proposal.bbox[3] <= 900 + 1

    def test_tile_origin_is_recorded_in_metadata(self, yolo_factory):
        model = yolo_factory([[10, 10, 60, 60]], [0.9])
        config = config_for_mode(
            PipelineMode.FAST, model_path="stub.pt", enable_tiling=True,
            tile_size=400, enable_secondary_pass=False, enable_preprocessing=False,
        )
        result = ProposalDetector(config, model=model).detect(
            np.full((900, 1200, 3), 120, dtype=np.uint8)
        )
        tiled = [p for p in result.proposals if p.source_pass == SOURCE_TILE]
        assert all("tile" in p.metadata for p in tiled)


class TestCapsAndFilters:
    def test_per_pass_cap_is_enforced(self, yolo_factory):
        boxes = [[i, i, i + 40, i + 40] for i in range(0, 300, 3)]
        model = yolo_factory(boxes, [0.5] * len(boxes))
        config = config_for_mode(
            PipelineMode.FAST, model_path="stub.pt",
            max_proposals_per_pass=10, enable_secondary_pass=False,
        )
        result = ProposalDetector(config, model=model).detect(
            np.full((400, 400, 3), 120, dtype=np.uint8)
        )
        assert result.passes[0].proposal_count <= 10

    def test_tiny_boxes_are_dropped(self, yolo_factory):
        # A 2x2 box has area 4, below the default min_box_area of 64.
        model = yolo_factory([[10, 10, 12, 12], [20, 20, 120, 120]], [0.9, 0.9])
        config = config_for_mode(
            PipelineMode.FAST, model_path="stub.pt", enable_secondary_pass=False
        )
        result = ProposalDetector(config, model=model).detect(
            np.full((400, 400, 3), 120, dtype=np.uint8)
        )
        assert all(p.area >= config.min_box_area for p in result.proposals)

    def test_small_object_count_is_reported(self, fake_yolo):
        config = config_for_mode(PipelineMode.FAST, model_path="stub.pt")
        result = ProposalDetector(config, model=fake_yolo).detect(
            np.full((1000, 1000, 3), 120, dtype=np.uint8)
        )
        assert result.small_object_count >= 0
        assert result.small_object_count <= result.raw_count


class TestQualityGating:
    def test_well_exposed_image_gets_no_enhanced_pass(self, fake_yolo, rng):
        config = config_for_mode(
            PipelineMode.BALANCED, model_path="stub.pt", enable_tiling=False,
            tiling_megapixel_threshold=float("inf"), tiling_density_threshold=10**9,
        )
        good = rng.integers(0, 255, (400, 600, 3), dtype=np.uint8)
        result = ProposalDetector(config, model=fake_yolo).detect(good)
        assert not any(p.name.startswith("enhanced") for p in result.passes)

    def test_dark_image_gets_an_enhanced_pass(self, fake_yolo, rng):
        config = config_for_mode(
            PipelineMode.BALANCED, model_path="stub.pt", enable_tiling=False,
            tiling_megapixel_threshold=float("inf"), tiling_density_threshold=10**9,
        )
        dark = (rng.integers(0, 255, (400, 600, 3)) * 0.12).astype(np.uint8)
        result = ProposalDetector(config, model=fake_yolo).detect(dark)
        assert any(p.name.startswith("enhanced") for p in result.passes)
        assert "dark" in result.quality.defects
