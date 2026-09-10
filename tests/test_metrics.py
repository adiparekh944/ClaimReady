"""Tests for evaluation metrics.

Values are checked against hand-computed results, since a metric that is
subtly wrong produces plausible-looking numbers and would silently invalidate
every benchmark conclusion.
"""

from __future__ import annotations

import numpy as np
import pytest

from vision.metrics import (
    COCO_IOU_THRESHOLDS,
    LatencyStats,
    association_metrics,
    average_precision,
    duplicate_metrics,
    match_predictions,
    mean_average_precision,
    proposal_statistics,
)

GROUND_TRUTH = [(0, 0, 10, 10), (20, 20, 30, 30), (50, 50, 60, 60)]


class TestMatching:
    def test_perfect_predictions(self):
        _, metrics = match_predictions(GROUND_TRUTH, GROUND_TRUTH, 0.5)
        assert metrics.precision == 1.0
        assert metrics.recall == 1.0
        assert metrics.f1 == 1.0

    def test_one_miss_one_false_positive(self):
        predictions = [(0, 0, 10, 10), (100, 100, 110, 110)]
        assignment, metrics = match_predictions(predictions, GROUND_TRUTH, 0.5, [0.9, 0.8])
        assert assignment == [0, -1]
        assert metrics.true_positives == 1
        assert metrics.false_positives == 1
        assert metrics.false_negatives == 2
        assert metrics.precision == pytest.approx(0.5)
        assert metrics.recall == pytest.approx(1 / 3)

    def test_each_ground_truth_is_claimed_once(self):
        # Two predictions on one object: one true positive, one duplicate.
        predictions = [(0, 0, 10, 10), (1, 1, 11, 11)]
        assignment, metrics = match_predictions(predictions, [(0, 0, 10, 10)], 0.5, [0.9, 0.8])
        assert metrics.true_positives == 1
        assert metrics.false_positives == 1
        assert sorted(assignment) == [-1, 0]

    def test_higher_confidence_claims_the_match(self):
        # The better-scoring prediction must win, per the COCO protocol.
        predictions = [(3, 3, 13, 13), (0, 0, 10, 10)]
        assignment, _ = match_predictions(predictions, [(0, 0, 10, 10)], 0.5, [0.2, 0.99])
        assert assignment[1] == 0
        assert assignment[0] == -1

    def test_threshold_is_respected(self):
        predictions = [(5, 0, 15, 10)]  # IoU 1/3 with the first object
        _, lenient = match_predictions(predictions, GROUND_TRUTH, 0.3, [0.9])
        _, strict = match_predictions(predictions, GROUND_TRUTH, 0.5, [0.9])
        assert lenient.true_positives == 1
        assert strict.true_positives == 0

    def test_no_predictions(self):
        _, metrics = match_predictions([], GROUND_TRUTH, 0.5)
        assert metrics.false_negatives == 3
        assert metrics.precision == 0.0

    def test_no_ground_truth(self):
        _, metrics = match_predictions(GROUND_TRUTH, [], 0.5)
        assert metrics.false_positives == 3
        assert metrics.recall == 0.0

    def test_both_empty(self):
        _, metrics = match_predictions([], [], 0.5)
        assert metrics.f1 == 0.0

    def test_to_dict_is_json_serializable(self):
        import json

        _, metrics = match_predictions(GROUND_TRUTH, GROUND_TRUTH, 0.5)
        json.dumps(metrics.to_dict())


class TestAveragePrecision:
    def test_perfect_detection_scores_one(self):
        assert average_precision(GROUND_TRUTH, GROUND_TRUTH, [1.0, 1.0, 1.0], 0.5) == pytest.approx(1.0)

    def test_no_ground_truth_scores_zero(self):
        assert average_precision(GROUND_TRUTH, [], [1.0, 1.0, 1.0], 0.5) == 0.0

    def test_no_predictions_scores_zero(self):
        assert average_precision([], GROUND_TRUTH, [], 0.5) == 0.0

    def test_result_is_bounded(self):
        predictions = GROUND_TRUTH + [(200, 200, 210, 210)]
        value = average_precision(predictions, GROUND_TRUTH, [0.9, 0.8, 0.7, 0.6], 0.5)
        assert 0.0 <= value <= 1.0

    def test_false_positives_ranked_last_hurt_less(self):
        """Confidence ordering must matter, or AP degenerates to precision."""
        predictions = [(0, 0, 10, 10), (300, 300, 310, 310)]
        good_ranking = average_precision(predictions, [(0, 0, 10, 10)], [0.9, 0.1], 0.5)
        bad_ranking = average_precision(predictions, [(0, 0, 10, 10)], [0.1, 0.9], 0.5)
        assert good_ranking > bad_ranking

    def test_mismatched_scores_raise(self):
        with pytest.raises(ValueError):
            average_precision(GROUND_TRUTH, GROUND_TRUTH, [1.0], 0.5)


class TestMeanAveragePrecision:
    def test_reports_every_threshold(self):
        result = mean_average_precision(GROUND_TRUTH, GROUND_TRUTH, [1.0, 1.0, 1.0])
        for threshold in COCO_IOU_THRESHOLDS:
            assert f"ap@{threshold:.2f}" in result
        assert result["map@0.50"] == pytest.approx(1.0)
        assert result["map@0.50:0.95"] == pytest.approx(1.0)

    def test_coco_sweep_shape(self):
        assert len(COCO_IOU_THRESHOLDS) == 10
        assert COCO_IOU_THRESHOLDS[0] == 0.50
        assert COCO_IOU_THRESHOLDS[-1] == 0.95

    def test_loose_boxes_score_lower_at_strict_thresholds(self):
        # A 1px shift on a 10x10 box gives IoU 81/119 = 0.68: it clears the
        # 0.50-0.65 thresholds and fails everything at 0.70 and above, so the
        # averaged mAP must come out below mAP@0.50.
        predictions = [(1, 1, 11, 11), (21, 21, 31, 31), (51, 51, 61, 61)]
        from vision import geometry

        assert geometry.iou(predictions[0], GROUND_TRUTH[0]) == pytest.approx(81 / 119, abs=1e-4)

        result = mean_average_precision(predictions, GROUND_TRUTH, [0.9, 0.9, 0.9])
        assert result["map@0.50"] == pytest.approx(1.0)
        assert result["map@0.50:0.95"] < result["map@0.50"]


class TestDuplicateMetrics:
    def test_exact_clustering_is_perfect(self):
        result = duplicate_metrics([[0, 1], [2]], [[0, 1], [2]], num_items=3)
        assert result.precision == 1.0
        assert result.recall == 1.0
        assert result.f1 == 1.0

    def test_over_merging_costs_precision(self):
        # Claimed {0,1,2} as one item when only {0,1} truly are.
        result = duplicate_metrics([[0, 1, 2]], [[0, 1], [2]], num_items=3)
        assert result.recall == 1.0
        assert result.precision < 1.0
        assert result.false_positives == 2

    def test_under_merging_costs_recall(self):
        result = duplicate_metrics([[0], [1], [2]], [[0, 1], [2]], num_items=3)
        assert result.recall == 0.0
        assert result.false_negatives == 1

    def test_pair_universe_size(self):
        result = duplicate_metrics([], [], num_items=5)
        assert result.total_pairs == 10  # 5 choose 2

    def test_singletons_generate_no_pairs(self):
        result = duplicate_metrics([[0], [1]], [[0], [1]], num_items=2)
        assert result.true_positives == 0
        assert result.f1 == 0.0

    def test_negative_item_count_raises(self):
        with pytest.raises(ValueError):
            duplicate_metrics([], [], num_items=-1)

    def test_to_dict_is_json_serializable(self):
        import json

        json.dumps(duplicate_metrics([[0, 1]], [[0, 1]], 2).to_dict())


class TestAssociationMetrics:
    def test_without_labels_correctness_is_none(self):
        """Unlabelled runs must report null, not a guess."""
        result = association_metrics(10, 7, 3, 3)
        assert result["identity_inflation"] is None
        assert result["duplicate_entries"] is None
        assert result["true_object_count"] is None
        # Values are rounded to 4 dp for readable JSON output.
        assert result["track_id_to_identity_ratio"] == pytest.approx(10 / 7, abs=1e-4)

    def test_with_labels_computes_inflation(self):
        result = association_metrics(10, 7, 3, 3, true_object_count=6)
        assert result["identity_inflation"] == pytest.approx(7 / 6, abs=1e-4)
        assert result["tracker_only_inflation"] == pytest.approx(10 / 6, abs=1e-4)
        assert result["duplicate_entries"] == 1

    def test_zero_true_count_is_treated_as_unavailable(self):
        assert association_metrics(10, 7, 3, 3, true_object_count=0)["identity_inflation"] is None

    def test_no_identities_avoids_division_by_zero(self):
        assert association_metrics(0, 0, 0, 0)["track_id_to_identity_ratio"] is None


class TestLatencyStats:
    def test_mean_by_stage(self):
        stats = LatencyStats()
        stats.add({"detection": 0.1, "total": 0.2})
        stats.add({"detection": 0.3, "total": 0.4})
        means = stats.mean_by_stage()
        assert means["detection"] == pytest.approx(0.2)
        assert means["total"] == pytest.approx(0.3)

    def test_percentiles_appear_only_with_enough_samples(self):
        stats = LatencyStats()
        for i in range(5):
            stats.add({"total": 0.1 * i})
        few = stats.percentiles("total")
        assert "p50" in few
        assert "p90" not in few  # needs 10 samples

        for i in range(15):
            stats.add({"total": 0.1 * i})
        many = stats.percentiles("total")
        assert "p90" in many and "p95" in many

    def test_unknown_stage_returns_empty(self):
        stats = LatencyStats()
        stats.add({"total": 0.1})
        assert stats.percentiles("nonexistent") == {}

    def test_empty_stats(self):
        stats = LatencyStats()
        assert stats.count == 0
        assert stats.mean_by_stage() == {}

    def test_to_dict_is_json_serializable(self):
        import json

        stats = LatencyStats()
        stats.add({"detection": 0.1, "total": 0.2})
        json.dumps(stats.to_dict())


class TestProposalStatistics:
    def test_counts_and_reduction(self):
        result = proposal_statistics([100, 80], [20, 15])
        assert result["raw_total"] == 180
        assert result["final_total"] == 35
        assert result["duplicates_removed"] == 145
        assert result["reduction_ratio"] == pytest.approx(1 - 35 / 180, abs=1e-4)
        assert result["mean_raw_per_image"] == pytest.approx(90.0)

    def test_no_reduction(self):
        assert proposal_statistics([10, 10], [10, 10])["reduction_ratio"] == pytest.approx(0.0)

    def test_empty_input_reports_none_not_zero(self):
        # A reduction ratio of 0.0 would falsely imply "measured, no effect".
        assert proposal_statistics([], [])["reduction_ratio"] is None

    def test_all_zero_raw_avoids_division_by_zero(self):
        assert proposal_statistics([0, 0], [0, 0])["reduction_ratio"] is None

    def test_mismatched_lengths_raise(self):
        with pytest.raises(ValueError):
            proposal_statistics([1, 2], [1])

    def test_is_json_serializable(self):
        import json

        json.dumps(proposal_statistics([10], [5]))
