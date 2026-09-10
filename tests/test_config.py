"""Tests for configuration loading, mode presets and environment overrides."""

from __future__ import annotations

import pytest

from vision.config import (
    ENV_PREFIX,
    EmbeddingCropMode,
    PipelineMode,
    VisionConfig,
    config_for_mode,
    load_config,
)


class TestModeParsing:
    def test_case_insensitive(self):
        assert PipelineMode.parse("balanced") is PipelineMode.BALANCED
        assert PipelineMode.parse("  ACCURATE  ") is PipelineMode.ACCURATE

    def test_passthrough(self):
        assert PipelineMode.parse(PipelineMode.FAST) is PipelineMode.FAST

    def test_unknown_mode_lists_the_valid_ones(self):
        with pytest.raises(ValueError, match="FAST"):
            PipelineMode.parse("TURBO")

    def test_crop_mode_parsing(self):
        assert EmbeddingCropMode.parse("MASKED") is EmbeddingCropMode.MASKED
        with pytest.raises(ValueError):
            EmbeddingCropMode.parse("sideways")


class TestPresets:
    def test_fast_is_minimal(self):
        config = config_for_mode(PipelineMode.FAST)
        assert config.scales == (640,)
        assert config.enable_embeddings is False
        assert config.enable_segmentation is False
        assert config.enable_tiling is False
        assert config.enable_preprocessing is False

    def test_balanced_adds_a_scale_and_appearance(self):
        config = config_for_mode(PipelineMode.BALANCED)
        assert config.scales == (640, 960)
        assert config.enable_embeddings is True
        assert config.enable_segmentation is True
        assert config.enable_tiling is False

    def test_accurate_is_maximal(self):
        config = config_for_mode(PipelineMode.ACCURATE)
        assert config.scales == (640, 960, 1280)
        assert config.enable_tiling is True
        assert config.embedding_crop_mode is EmbeddingCropMode.MASKED

    def test_scale_count_increases_with_mode(self):
        counts = [len(config_for_mode(m).scales) for m in
                  (PipelineMode.FAST, PipelineMode.BALANCED, PipelineMode.ACCURATE)]
        assert counts == sorted(counts)

    def test_explicit_overrides_beat_the_preset(self):
        config = config_for_mode(PipelineMode.FAST, enable_embeddings=True, max_proposals=42)
        assert config.enable_embeddings is True
        assert config.max_proposals == 42
        assert config.scales == (640,)  # preset value retained


class TestValidation:
    def test_empty_scales_rejected(self):
        with pytest.raises(ValueError, match="at least one"):
            VisionConfig(scales=())

    def test_negative_scale_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            VisionConfig(scales=(640, -1))

    def test_non_positive_max_proposals_rejected(self):
        with pytest.raises(ValueError, match="max_proposals"):
            VisionConfig(max_proposals=0)

    def test_out_of_range_threshold_rejected(self):
        with pytest.raises(ValueError, match="iou_threshold"):
            VisionConfig(iou_threshold=1.5)

    def test_bad_tile_overlap_rejected(self):
        with pytest.raises(ValueError, match="tile_overlap"):
            VisionConfig(tile_overlap=1.0)

    def test_config_is_frozen(self):
        config = VisionConfig()
        with pytest.raises(Exception):
            config.max_proposals = 5  # type: ignore[misc]


class TestEnvironmentOverrides:
    def test_mode_from_environment(self):
        config = load_config(env={f"{ENV_PREFIX}MODE": "ACCURATE"})
        assert config.mode is PipelineMode.ACCURATE

    def test_float_override(self):
        config = load_config(env={f"{ENV_PREFIX}YOLO_CONFIDENCE": "0.2"})
        assert config.yolo_confidence == pytest.approx(0.2)

    def test_int_override(self):
        config = load_config(env={f"{ENV_PREFIX}MAX_PROPOSALS": "77"})
        assert config.max_proposals == 77

    @pytest.mark.parametrize("raw,expected", [
        ("true", True), ("TRUE", True), ("1", True), ("yes", True), ("on", True),
        ("false", False), ("0", False), ("no", False), ("off", False),
    ])
    def test_bool_override(self, raw, expected):
        config = load_config(env={f"{ENV_PREFIX}ENABLE_TILING": raw})
        assert config.enable_tiling is expected

    @pytest.mark.parametrize("raw", ["640,960", "640 960", "640, 960"])
    def test_scales_accept_commas_or_spaces(self, raw):
        config = load_config(env={f"{ENV_PREFIX}SCALES": raw})
        assert config.scales == (640, 960)

    def test_enum_override(self):
        config = load_config(env={f"{ENV_PREFIX}EMBEDDING_CROP_MODE": "masked"})
        assert config.embedding_crop_mode is EmbeddingCropMode.MASKED

    def test_unknown_variable_is_ignored(self):
        # Must not raise: an unrecognized variable in a deployment environment
        # should not prevent the server from starting.
        config = load_config(env={f"{ENV_PREFIX}NOT_A_REAL_SETTING": "5"})
        assert isinstance(config, VisionConfig)

    def test_malformed_value_is_ignored_and_default_kept(self):
        default = VisionConfig().max_proposals
        config = load_config(env={f"{ENV_PREFIX}MAX_PROPOSALS": "not-a-number"})
        assert config.max_proposals == default

    def test_unprefixed_variables_are_ignored(self):
        config = load_config(env={"MAX_PROPOSALS": "5"})
        assert config.max_proposals != 5

    def test_explicit_argument_beats_environment(self):
        # Keeps tests and benchmarks deterministic regardless of the shell.
        config = load_config(
            env={f"{ENV_PREFIX}MAX_PROPOSALS": "10"},
            max_proposals=99,
        )
        assert config.max_proposals == 99

    def test_environment_beats_the_preset(self):
        config = load_config(
            mode=PipelineMode.FAST,
            env={f"{ENV_PREFIX}ENABLE_EMBEDDINGS": "true"},
        )
        assert config.enable_embeddings is True


class TestDerivedBehaviour:
    def test_uses_masks_requires_a_seg_checkpoint(self):
        seg = VisionConfig(model_path="yolo11x-seg.pt", enable_segmentation=True)
        det = VisionConfig(model_path="yolo11l.pt", enable_segmentation=True)
        assert seg.uses_masks is True
        assert det.uses_masks is False

    def test_uses_masks_false_when_segmentation_disabled(self):
        config = VisionConfig(model_path="yolo11x-seg.pt", enable_segmentation=False)
        assert config.uses_masks is False

    def test_should_tile_when_explicitly_enabled(self):
        config = VisionConfig(enable_tiling=True)
        assert config.should_tile(0.1, 0) is True

    def test_should_tile_on_large_images(self):
        config = VisionConfig(enable_tiling=False, tiling_megapixel_threshold=8.0)
        assert config.should_tile(12.0, 0) is True
        assert config.should_tile(2.0, 0) is False

    def test_should_tile_on_small_object_density(self):
        config = VisionConfig(enable_tiling=False, tiling_density_threshold=25)
        assert config.should_tile(1.0, 30) is True
        assert config.should_tile(1.0, 10) is False

    def test_fast_mode_never_auto_tiles(self):
        # FAST has no appearance model, so a tiled pass would only add latency.
        config = config_for_mode(PipelineMode.FAST)
        assert config.should_tile(50.0, 10_000) is False

    def test_with_overrides_returns_a_new_object(self):
        original = VisionConfig()
        derived = original.with_overrides(max_proposals=7)
        assert derived.max_proposals == 7
        assert original.max_proposals != 7

    def test_with_overrides_coerces_types(self):
        derived = VisionConfig().with_overrides(mode="ACCURATE", scales=[640, 1280])
        assert derived.mode is PipelineMode.ACCURATE
        assert derived.scales == (640, 1280)

    def test_summary_is_json_serializable(self):
        import json

        payload = config_for_mode(PipelineMode.ACCURATE).summary()
        json.dumps(payload)
        assert payload["mode"] == "ACCURATE"
        assert payload["scales"] == [640, 960, 1280]
