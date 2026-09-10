"""End-to-end pipeline tests with stubbed inference.

These check the wiring between stages — ordering, index alignment, timing
instrumentation and the FAST/BALANCED difference — rather than detection
quality, which needs real weights and is covered by the benchmark.
"""

from __future__ import annotations

import numpy as np
import pytest

from vision.config import PipelineMode, config_for_mode
from vision.pipeline import StageTimer, VisionPipeline


@pytest.fixture
def room_image(rng) -> np.ndarray:
    """A well-exposed synthetic image, so the quality gate stays quiet."""
    image = rng.integers(60, 200, (480, 640, 3), dtype=np.uint8)
    image[100:250, 120:300] = 210
    image[300:400, 400:560] = 40
    return image


def build_pipeline(mode, model, embedder=None, **overrides):
    config = config_for_mode(mode, model_path="stub.pt", **overrides)
    return VisionPipeline(config, model=model, embedder=embedder)


class TestStageTimer:
    def test_records_measured_stages(self):
        timer = StageTimer(enabled=True)
        with timer.measure("alpha"):
            pass
        with timer.measure("beta"):
            pass
        assert set(timer.timings) == {"alpha", "beta"}
        assert timer.total == pytest.approx(sum(timer.timings.values()))

    def test_repeated_stage_accumulates(self):
        timer = StageTimer(enabled=True)
        for _ in range(3):
            with timer.measure("alpha"):
                pass
        assert len(timer.timings) == 1

    def test_disabled_timer_records_nothing(self):
        timer = StageTimer(enabled=False)
        with timer.measure("alpha"):
            pass
        assert timer.timings == {}

    def test_timing_survives_an_exception(self):
        timer = StageTimer(enabled=True)
        with pytest.raises(RuntimeError):
            with timer.measure("alpha"):
                raise RuntimeError("boom")
        # The stage must still be recorded, or a failing request would report
        # no timings at all.
        assert "alpha" in timer.timings

    def test_to_dict_includes_a_total(self):
        timer = StageTimer(enabled=True)
        with timer.measure("alpha"):
            pass
        assert "total" in timer.to_dict()


class TestFastMode:
    def test_produces_deduplicated_proposals(self, fake_yolo, room_image):
        pipeline = build_pipeline(PipelineMode.FAST, fake_yolo)
        result = pipeline.process_image(room_image)
        assert result.final_count >= 1
        assert result.final_count <= result.raw_count
        assert result.mode is PipelineMode.FAST

    def test_skips_embeddings(self, fake_yolo, room_image, fake_embedder):
        pipeline = build_pipeline(PipelineMode.FAST, fake_yolo, embedder=fake_embedder)
        result = pipeline.process_image(room_image)
        assert result.embedding_count == 0
        # The encoder must not be touched at all in FAST mode.
        assert fake_embedder.call_count == 0
        assert "embedding" not in result.timings

    def test_crops_align_with_proposals(self, fake_yolo, room_image):
        pipeline = build_pipeline(PipelineMode.FAST, fake_yolo)
        result = pipeline.process_image(room_image)
        assert len(result.crops) == result.final_count
        assert all(c.size > 0 for c in result.crops)


class TestBalancedMode:
    def test_computes_embeddings(self, fake_yolo, room_image, fake_embedder):
        pipeline = build_pipeline(
            PipelineMode.BALANCED, fake_yolo, embedder=fake_embedder,
            enable_tiling=False, tiling_megapixel_threshold=float("inf"),
            tiling_density_threshold=10**9,
        )
        result = pipeline.process_image(room_image)
        assert result.embedding_count == result.capped_count
        assert fake_embedder.call_count >= 1
        assert "embedding" in result.timings
        assert "similarity" in result.timings

    def test_embeddings_are_attached_to_proposals(self, fake_yolo, room_image, fake_embedder):
        pipeline = build_pipeline(
            PipelineMode.BALANCED, fake_yolo, embedder=fake_embedder,
            enable_tiling=False, tiling_megapixel_threshold=float("inf"),
            tiling_density_threshold=10**9,
        )
        result = pipeline.process_image(room_image)
        assert any(p.has_embedding for p in result.proposals)

    def test_encoder_is_called_once_per_crop_not_per_pair(
        self, fake_yolo, room_image, fake_embedder
    ):
        """Cost must be linear in proposals, not quadratic.

        Embedding each pair independently would be O(N^2) forward passes; the
        whole design rests on doing one pass per crop and deriving similarity
        from a single matrix product.
        """
        pipeline = build_pipeline(
            PipelineMode.BALANCED, fake_yolo, embedder=fake_embedder,
            enable_tiling=False, tiling_megapixel_threshold=float("inf"),
            tiling_density_threshold=10**9,
        )
        result = pipeline.process_image(room_image)
        assert fake_embedder.crops_seen == result.capped_count


class TestStageOrdering:
    def test_counts_are_monotonically_non_increasing(self, fake_yolo, room_image, fake_embedder):
        pipeline = build_pipeline(
            PipelineMode.BALANCED, fake_yolo, embedder=fake_embedder,
            enable_tiling=False, tiling_megapixel_threshold=float("inf"),
            tiling_density_threshold=10**9,
        )
        result = pipeline.process_image(room_image)
        counts = result.stage_counts()
        assert counts["raw"] >= counts["after_prefusion"] >= counts["after_cap"] >= counts["final"]

    def test_cap_is_applied_before_embedding(self, yolo_factory, room_image, fake_embedder):
        """The proposal cap must precede the expensive per-crop stage."""
        boxes = [[i * 7, i * 5, i * 7 + 60, i * 5 + 60] for i in range(40)]
        model = yolo_factory(boxes, [0.5 + (i % 10) * 0.04 for i in range(40)])
        pipeline = build_pipeline(
            PipelineMode.BALANCED, model, embedder=fake_embedder,
            max_proposals=5, enable_secondary_pass=False, enable_tiling=False,
            tiling_megapixel_threshold=float("inf"), tiling_density_threshold=10**9,
        )
        result = pipeline.process_image(room_image)
        assert result.capped_count <= 5
        assert fake_embedder.crops_seen <= 5

    def test_reduction_ratio_is_consistent(self, fake_yolo, room_image):
        pipeline = build_pipeline(PipelineMode.FAST, fake_yolo)
        result = pipeline.process_image(room_image)
        expected = 1.0 - (result.final_count / result.raw_count)
        assert result.reduction_ratio == pytest.approx(expected)
        assert result.duplicates_removed == result.raw_count - result.final_count


class TestBaselinePath:
    def test_baseline_uses_a_single_scale(self, fake_yolo, room_image):
        pipeline = build_pipeline(PipelineMode.BALANCED, fake_yolo)
        pipeline.process_baseline(room_image)
        assert {c["imgsz"] for c in fake_yolo.calls} == {640}

    def test_baseline_skips_embeddings(self, fake_yolo, room_image, fake_embedder):
        pipeline = build_pipeline(PipelineMode.BALANCED, fake_yolo, embedder=fake_embedder)
        result = pipeline.process_baseline(room_image)
        assert result.embedding_count == 0
        assert fake_embedder.call_count == 0

    def test_baseline_has_no_dedup_record(self, fake_yolo, room_image):
        # Greedy suppression discards rather than clustering, so there is no
        # merge audit trail to report.
        pipeline = build_pipeline(PipelineMode.BALANCED, fake_yolo)
        assert pipeline.process_baseline(room_image).dedup is None

    def test_baseline_never_tiles(self, fake_yolo, room_image):
        pipeline = build_pipeline(PipelineMode.ACCURATE, fake_yolo)
        assert pipeline.process_baseline(room_image).tiled is False


class TestResultSerialization:
    def test_to_dict_is_json_serializable(self, fake_yolo, room_image, fake_embedder):
        import json

        pipeline = build_pipeline(
            PipelineMode.BALANCED, fake_yolo, embedder=fake_embedder,
            enable_tiling=False, tiling_megapixel_threshold=float("inf"),
            tiling_density_threshold=10**9,
        )
        payload = pipeline.process_image(room_image).to_dict()
        json.dumps(payload)
        assert "stage_counts" in payload
        assert "timings" in payload

    def test_to_dict_can_omit_proposals(self, fake_yolo, room_image):
        pipeline = build_pipeline(PipelineMode.FAST, fake_yolo)
        payload = pipeline.process_image(room_image).to_dict(include_proposals=False)
        assert "proposals" not in payload


class TestDebugRetention:
    def test_pre_dedup_proposals_retained_only_when_debugging(
        self, fake_yolo, room_image, fake_embedder
    ):
        # Full-frame masks are memory-heavy, so retention is gated.
        off = build_pipeline(
            PipelineMode.BALANCED, fake_yolo, embedder=fake_embedder,
            enable_tiling=False, tiling_megapixel_threshold=float("inf"),
            tiling_density_threshold=10**9,
        )
        assert off.process_image(room_image).pre_dedup_proposals == []

        on = build_pipeline(
            PipelineMode.BALANCED, fake_yolo, embedder=fake_embedder,
            debug_visualization=True, enable_tiling=False,
            tiling_megapixel_threshold=float("inf"), tiling_density_threshold=10**9,
        )
        assert on.process_image(room_image).pre_dedup_proposals


class TestInputValidation:
    def test_empty_image_raises(self, fake_yolo):
        pipeline = build_pipeline(PipelineMode.FAST, fake_yolo)
        with pytest.raises(ValueError):
            pipeline.process_image(np.zeros((0, 0, 3), dtype=np.uint8))

    def test_none_image_raises(self, fake_yolo):
        pipeline = build_pipeline(PipelineMode.FAST, fake_yolo)
        with pytest.raises(ValueError):
            pipeline.process_image(None)

    def test_no_detections_yields_no_proposals(self, yolo_factory, room_image):
        # All confidences below every threshold, so nothing survives.
        model = yolo_factory([[10, 10, 100, 100]], [0.0001])
        pipeline = build_pipeline(
            PipelineMode.FAST, model, yolo_confidence=0.5,
            yolo_confidence_secondary=0.4,
        )
        result = pipeline.process_image(room_image)
        assert result.final_count == 0
        assert result.crops == []
