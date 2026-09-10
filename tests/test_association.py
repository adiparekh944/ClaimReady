"""Tests for inventory identity association and appearance re-identification.

The behaviour that matters most is the pair of opposing failure modes:

- an object that leaves the frame and returns must be **one** item, and
- two identical objects visible simultaneously must be **two** items.

Both are tested explicitly, because a re-identification threshold can be wrong
in either direction and the counts alone look plausible in both cases.
"""

from __future__ import annotations

import numpy as np
import pytest

from vision.association import (
    ASSIGN_NEW,
    ASSIGN_REID,
    ASSIGN_TRACKER,
    InventoryItem,
    InventoryMemoryBank,
    score_crop_quality,
)


def unit_vector(index: int, dim: int = 16) -> np.ndarray:
    vector = np.zeros(dim, dtype=np.float32)
    vector[index] = 1.0
    return vector


def textured_crop(size: int = 60, value: int = 120) -> np.ndarray:
    crop = np.full((size, size, 3), value, dtype=np.uint8)
    crop[size // 3 : 2 * size // 3, size // 3 : 2 * size // 3] = 250
    return crop


@pytest.fixture
def bank(balanced_config):
    return InventoryMemoryBank(balanced_config)


FRAME_SHAPE = (480, 640)


class TestTrackerAssociation:
    def test_first_detection_creates_an_item(self, bank):
        item, reason = bank.assign(1, (10, 10, 50, 50), 0.8, 0, embedding=unit_vector(0),
                                   frame_shape=FRAME_SHAPE, live_track_ids={1})
        assert reason == ASSIGN_NEW
        assert item.item_id == 0
        assert item.track_ids == [1]

    def test_same_tracker_id_reuses_the_item(self, bank):
        first, _ = bank.assign(1, (10, 10, 50, 50), 0.8, 0, embedding=unit_vector(0),
                               frame_shape=FRAME_SHAPE, live_track_ids={1})
        second, reason = bank.assign(1, (11, 11, 51, 51), 0.8, 1, embedding=unit_vector(0),
                                     frame_shape=FRAME_SHAPE, live_track_ids={1})
        assert reason == ASSIGN_TRACKER
        assert second is first
        assert first.frames_seen == 2

    def test_confirmation_requires_enough_frames(self, bank):
        threshold = bank.config.min_frames_to_confirm
        for frame in range(threshold):
            item, _ = bank.assign(1, (10, 10, 50, 50), 0.8, frame, embedding=unit_vector(0),
                                  frame_shape=FRAME_SHAPE, live_track_ids={1})
            expected = frame + 1 >= threshold
            assert item.confirmed is expected

    def test_unconfirmed_items_are_excluded_from_the_inventory(self, bank):
        bank.assign(1, (10, 10, 50, 50), 0.8, 0, embedding=unit_vector(0),
                    frame_shape=FRAME_SHAPE, live_track_ids={1})
        assert bank.confirmed_items() == []


class TestReIdentification:
    def _establish(self, bank, embedding, track_id=1):
        for frame in range(bank.config.min_frames_to_confirm):
            bank.assign(track_id, (100, 100, 200, 200), 0.8, frame, crop=textured_crop(),
                        embedding=embedding, label="couch", frame_shape=FRAME_SHAPE,
                        live_track_ids={track_id})

    def test_object_returning_with_a_new_tracker_id_is_recognized(self, bank):
        """The pan-away-and-return case that produced duplicate entries."""
        sofa = unit_vector(0)
        self._establish(bank, sofa)

        # Object leaves the frame for long enough that the tracker gives up.
        for frame in range(3, 40):
            bank.mark_missing(set(), frame)

        item, reason = bank.assign(9, (110, 105, 215, 205), 0.75, 40, crop=textured_crop(),
                                   embedding=sofa, label="couch", frame_shape=FRAME_SHAPE,
                                   live_track_ids={9})
        assert reason == ASSIGN_REID
        assert item.item_id == 0
        assert item.track_ids == [1, 9]
        assert item.id_switches_absorbed == 1
        assert len(bank.items) == 1

    def test_a_different_object_gets_its_own_identity(self, bank):
        self._establish(bank, unit_vector(0))
        for frame in range(3, 40):
            bank.mark_missing(set(), frame)

        item, reason = bank.assign(9, (400, 50, 470, 200), 0.7, 40, crop=textured_crop(),
                                   embedding=unit_vector(5), label="lamp",
                                   frame_shape=FRAME_SHAPE, live_track_ids={9})
        assert reason == ASSIGN_NEW
        assert item.item_id == 1
        assert len(bank.items) == 2

    def test_identical_objects_in_the_same_frame_stay_separate(self, bank):
        """Two matching chairs visible at once cannot be one object.

        This is a physical-impossibility constraint, not a threshold, and it is
        what makes appearance matching safe to use at all.
        """
        sofa = unit_vector(0)
        self._establish(bank, sofa, track_id=1)

        item, reason = bank.assign(2, (400, 300, 500, 400), 0.8, 3, crop=textured_crop(),
                                   embedding=sofa, label="couch", frame_shape=FRAME_SHAPE,
                                   live_track_ids={1, 2})
        assert reason == ASSIGN_NEW
        assert len(bank.items) == 2

    def test_disabling_reid_reverts_to_tracker_semantics(self, balanced_config):
        bank = InventoryMemoryBank(balanced_config.with_overrides(enable_reid=False))
        sofa = unit_vector(0)
        for frame in range(3):
            bank.assign(1, (100, 100, 200, 200), 0.8, frame, embedding=sofa,
                        frame_shape=FRAME_SHAPE, live_track_ids={1})
        for frame in range(3, 40):
            bank.mark_missing(set(), frame)
        _, reason = bank.assign(9, (100, 100, 200, 200), 0.8, 40, embedding=sofa,
                                frame_shape=FRAME_SHAPE, live_track_ids={9})
        assert reason == ASSIGN_NEW
        assert len(bank.items) == 2

    def test_no_embedding_means_no_reid(self, bank):
        self._establish(bank, unit_vector(0))
        for frame in range(3, 40):
            bank.mark_missing(set(), frame)
        _, reason = bank.assign(9, (100, 100, 200, 200), 0.8, 40, embedding=None,
                                frame_shape=FRAME_SHAPE, live_track_ids={9})
        assert reason == ASSIGN_NEW

    def test_below_threshold_similarity_does_not_merge(self, bank):
        self._establish(bank, unit_vector(0))
        for frame in range(3, 40):
            bank.mark_missing(set(), frame)

        # Roughly 0.7 cosine against the stored descriptor.
        blend = np.zeros(16, dtype=np.float32)
        blend[0] = 0.7
        blend[1] = 0.714
        _, reason = bank.assign(9, (100, 100, 200, 200), 0.8, 40, embedding=blend,
                                frame_shape=FRAME_SHAPE, live_track_ids={9})
        assert reason == ASSIGN_NEW

    def test_similarity_samples_are_recorded_even_without_a_match(self, bank):
        """A threshold that never fires must still be observable.

        Otherwise "0 re-id events" is indistinguishable from a broken feature.
        """
        self._establish(bank, unit_vector(0))
        for frame in range(3, 40):
            bank.mark_missing(set(), frame)
        bank.assign(9, (100, 100, 200, 200), 0.8, 40, embedding=unit_vector(7),
                    frame_shape=FRAME_SHAPE, live_track_ids={9})

        distribution = bank.reid_similarity_distribution()
        assert distribution["samples"] >= 1
        assert "would_match_at_threshold" in distribution
        assert bank.stats["reid_attempts_with_candidates"] >= 1

    def test_distribution_reports_absence_clearly(self, bank):
        assert bank.reid_similarity_distribution()["samples"] == 0
        assert "note" in bank.reid_similarity_distribution()


class TestDescriptorUpdates:
    def test_descriptor_is_unit_length(self):
        item = InventoryItem(item_id=0)
        item.update_descriptor(np.array([3.0, 4.0], dtype=np.float32))
        assert np.linalg.norm(item.descriptor) == pytest.approx(1.0)

    def test_running_mean_stays_unit_length(self):
        item = InventoryItem(item_id=0)
        for value in ([1.0, 0.0], [0.9, 0.1], [0.8, 0.2], [0.95, 0.05]):
            item.update_descriptor(np.array(value, dtype=np.float32))
        assert np.linalg.norm(item.descriptor) == pytest.approx(1.0, abs=1e-6)
        assert item.embedding_count == 4

    def test_descriptor_moves_toward_repeated_observations(self):
        item = InventoryItem(item_id=0)
        item.update_descriptor(np.array([1.0, 0.0], dtype=np.float32))
        for _ in range(10):
            item.update_descriptor(np.array([0.0, 1.0], dtype=np.float32))
        # After ten observations of the second view it should dominate.
        assert item.descriptor[1] > item.descriptor[0]

    def test_zero_and_none_embeddings_are_ignored(self):
        item = InventoryItem(item_id=0)
        item.update_descriptor(None)
        item.update_descriptor(np.zeros(4, dtype=np.float32))
        assert item.descriptor is None


class TestLabelVoting:
    def test_majority_label_wins(self):
        item = InventoryItem(item_id=0)
        for label in ("chair", "chair", "couch", "chair"):
            item.observe_label(label)
        assert item.dominant_label == "chair"

    def test_empty_labels_are_not_counted(self):
        item = InventoryItem(item_id=0, label="fallback")
        item.observe_label("")
        assert item.dominant_label == "fallback"


class TestCropQuality:
    def test_centered_beats_edge(self, balanced_config):
        crop = textured_crop()
        centered = score_crop_quality(crop, (270, 190, 370, 290), 0.8, FRAME_SHAPE, balanced_config)
        edge = score_crop_quality(crop, (0, 0, 100, 100), 0.8, FRAME_SHAPE, balanced_config)
        assert centered.score > edge.score

    def test_higher_confidence_beats_lower(self, balanced_config):
        crop = textured_crop()
        box = (270, 190, 370, 290)
        high = score_crop_quality(crop, box, 0.95, FRAME_SHAPE, balanced_config)
        low = score_crop_quality(crop, box, 0.30, FRAME_SHAPE, balanced_config)
        assert high.score > low.score

    def test_sharper_crop_beats_blurred(self, balanced_config):
        import cv2

        sharp = textured_crop()
        blurred = cv2.GaussianBlur(sharp, (21, 21), 0)
        box = (270, 190, 370, 290)
        assert (
            score_crop_quality(sharp, box, 0.8, FRAME_SHAPE, balanced_config).score
            > score_crop_quality(blurred, box, 0.8, FRAME_SHAPE, balanced_config).score
        )

    def test_larger_box_beats_tiny(self, balanced_config):
        crop = textured_crop()
        big = score_crop_quality(crop, (220, 140, 420, 340), 0.8, FRAME_SHAPE, balanced_config)
        tiny = score_crop_quality(crop, (310, 230, 330, 250), 0.8, FRAME_SHAPE, balanced_config)
        assert big.score > tiny.score

    def test_missing_crop_scores_zero_sharpness(self, balanced_config):
        quality = score_crop_quality(None, (0, 0, 10, 10), 0.5, FRAME_SHAPE, balanced_config)
        assert quality.sharpness == 0.0

    def test_score_is_bounded(self, balanced_config):
        crop = textured_crop()
        quality = score_crop_quality(crop, (0, 0, 640, 480), 1.0, FRAME_SHAPE, balanced_config)
        assert 0.0 <= quality.score <= 1.0

    def test_best_crop_selection_keeps_the_highest_score(self, balanced_config):
        item = InventoryItem(item_id=0)
        weak = score_crop_quality(textured_crop(), (0, 0, 20, 20), 0.2, FRAME_SHAPE, balanced_config)
        strong = score_crop_quality(textured_crop(), (270, 190, 370, 290), 0.9, FRAME_SHAPE, balanced_config)

        assert item.consider_crop(textured_crop(), weak, frame_number=1) is True
        assert item.consider_crop(textured_crop(), strong, frame_number=5) is True
        assert item.best_frame == 5
        # A subsequent worse frame must not replace it.
        assert item.consider_crop(textured_crop(), weak, frame_number=9) is False
        assert item.best_frame == 5


class TestAgingAndSummary:
    def test_stale_items_release_their_tracker_binding(self, bank):
        for frame in range(3):
            bank.assign(1, (10, 10, 50, 50), 0.8, frame, embedding=unit_vector(0),
                        frame_shape=FRAME_SHAPE, live_track_ids={1})
        stale = []
        for frame in range(3, 3 + bank.config.max_missing_frames + 2):
            stale.extend(bank.mark_missing(set(), frame))
        assert 0 in stale
        # The item itself survives so it can still be re-identified later.
        assert 0 in bank.items

    def test_summary_counts(self, bank):
        for frame in range(3):
            bank.assign(1, (10, 10, 50, 50), 0.8, frame, embedding=unit_vector(0),
                        frame_shape=FRAME_SHAPE, live_track_ids={1})
        summary = bank.summary()
        assert summary["generated_track_ids"] == 1
        assert summary["inventory_identities"] == 1
        assert summary["confirmed_identities"] == 1
        assert summary["detections"] == 3

    def test_summary_is_json_serializable(self, bank):
        import json

        bank.assign(1, (10, 10, 50, 50), 0.8, 0, embedding=unit_vector(0),
                    frame_shape=FRAME_SHAPE, live_track_ids={1})
        json.dumps(bank.summary())

    def test_item_to_dict_is_json_serializable(self, bank):
        import json

        item, _ = bank.assign(1, (10, 10, 50, 50), 0.8, 0, crop=textured_crop(),
                              embedding=unit_vector(0), frame_shape=FRAME_SHAPE,
                              live_track_ids={1})
        json.dumps(item.to_dict())
