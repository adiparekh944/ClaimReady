"""Tests for embedding normalization and similarity.

The encoder itself is not exercised here — that would mean downloading CLIP
weights. What is tested is the surrounding maths, which is where a mistake
would silently corrupt every merge decision: if rows are not unit length, the
Gram matrix stops being cosine similarity and every configured threshold means
something different.
"""

from __future__ import annotations

import numpy as np
import pytest

from vision.embeddings import (
    cosine_similarity,
    cosine_similarity_matrix,
    l2_normalize,
    resolve_device,
)


class TestL2Normalize:
    def test_rows_become_unit_length(self):
        matrix = l2_normalize(np.array([[3.0, 4.0], [5.0, 12.0]]))
        assert np.allclose(np.linalg.norm(matrix, axis=1), 1.0)

    def test_known_value(self):
        matrix = l2_normalize(np.array([[3.0, 4.0]]))
        assert matrix[0] == pytest.approx([0.6, 0.8])

    def test_zero_row_stays_zero_instead_of_nan(self):
        # A crop that failed to embed must produce "no evidence", not NaN,
        # which would poison every comparison involving it.
        matrix = l2_normalize(np.array([[0.0, 0.0], [1.0, 0.0]]))
        assert np.all(np.isfinite(matrix))
        assert matrix[0] == pytest.approx([0.0, 0.0])

    def test_direction_is_preserved(self):
        matrix = l2_normalize(np.array([[2.0, 0.0, 0.0]]))
        assert matrix[0] == pytest.approx([1.0, 0.0, 0.0])

    def test_empty_input(self):
        assert l2_normalize(np.zeros((0, 4))).shape == (0, 4)

    def test_scaling_a_vector_does_not_change_its_normalization(self):
        a = l2_normalize(np.array([[1.0, 2.0, 3.0]]))
        b = l2_normalize(np.array([[10.0, 20.0, 30.0]]))
        assert np.allclose(a, b)


class TestCosineSimilarityMatrix:
    def test_diagonal_is_one(self):
        matrix = l2_normalize(np.array([[1.0, 0.0], [0.6, 0.8], [0.0, 1.0]]))
        similarity = cosine_similarity_matrix(matrix)
        assert np.allclose(np.diag(similarity), 1.0, atol=1e-6)

    def test_orthogonal_vectors_score_zero(self):
        matrix = l2_normalize(np.array([[1.0, 0.0], [0.0, 1.0]]))
        assert cosine_similarity_matrix(matrix)[0, 1] == pytest.approx(0.0, abs=1e-6)

    def test_matrix_is_symmetric(self):
        matrix = l2_normalize(np.random.default_rng(0).normal(size=(6, 12)))
        similarity = cosine_similarity_matrix(matrix)
        assert np.allclose(similarity, similarity.T, atol=1e-6)

    def test_values_stay_within_bounds(self):
        # Clipping matters: float32 rounding otherwise yields self-similarities
        # slightly above 1.0, which breaks strict threshold comparisons.
        matrix = l2_normalize(np.random.default_rng(1).normal(size=(20, 32)))
        similarity = cosine_similarity_matrix(matrix)
        assert similarity.min() >= -1.0
        assert similarity.max() <= 1.0

    def test_agrees_with_the_pairwise_function(self):
        matrix = l2_normalize(np.random.default_rng(2).normal(size=(5, 8)))
        similarity = cosine_similarity_matrix(matrix)
        for i in range(5):
            for j in range(5):
                assert similarity[i, j] == pytest.approx(
                    cosine_similarity(matrix[i], matrix[j]), abs=1e-5
                )

    def test_zero_row_scores_zero_against_everything(self):
        matrix = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=np.float32)
        similarity = cosine_similarity_matrix(matrix)
        assert similarity[1, 0] == 0.0
        assert similarity[1, 1] == 0.0

    def test_none_and_empty_return_none(self):
        assert cosine_similarity_matrix(None) is None
        assert cosine_similarity_matrix(np.zeros((0, 4))) is None

    def test_rejects_wrong_dimensionality(self):
        with pytest.raises(ValueError):
            cosine_similarity_matrix(np.zeros((2, 2, 2)))


class TestCosineSimilarity:
    def test_identical_vectors(self):
        assert cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)

    def test_opposite_vectors(self):
        assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_normalizes_unnormalized_input(self):
        assert cosine_similarity([3.0, 0.0], [7.0, 0.0]) == pytest.approx(1.0)

    def test_zero_vector_gives_zero(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0

    def test_shape_mismatch_raises(self):
        with pytest.raises(ValueError):
            cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])


class TestDeviceResolution:
    def test_explicit_device_is_respected(self):
        assert resolve_device("cpu") == "cpu"
        assert resolve_device("cuda:1") == "cuda:1"

    def test_auto_returns_a_known_backend(self):
        assert resolve_device("auto") in {"cpu", "cuda", "mps"}
