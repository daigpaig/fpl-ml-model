"""Phase 3 eval-layer tests: metric correctness and split hygiene."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))
from backtest import within_gw_spearman  # noqa: E402

from src.data.paths import SEASONS
from src.models.common import load_splits


def _frames(xpts, actual_points, actual_minutes):
    n = len(xpts)
    base = {"season": ["2024-25"] * n, "gw": [1] * n, "element": range(n)}
    projection = pd.DataFrame({**base, "xpts": xpts})
    actual = pd.DataFrame({
        **base, "actual_points": actual_points, "actual_minutes": actual_minutes,
    })
    return projection, actual


class TestWithinGwSpearman:
    def test_perfect_ranking(self):
        proj, actual = _frames([1, 2, 3, 4], [2, 5, 6, 12], [90] * 4)
        result = within_gw_spearman(proj, actual)
        assert result["spearman_all"] == pytest.approx(1.0)
        assert result["spearman_played"] == pytest.approx(1.0)
        assert result["n_players"] == 4

    def test_inverted_ranking(self):
        proj, actual = _frames([4, 3, 2, 1], [2, 5, 6, 12], [90] * 4)
        assert within_gw_spearman(proj, actual)["spearman_all"] == pytest.approx(-1.0)

    def test_played_filter_excludes_benchwarmers(self):
        # Ranking is perfect overall but random among those who played.
        proj, actual = _frames(
            [0, 0, 1, 2], [0, 0, 6, 3], [0, 0, 90, 90])
        result = within_gw_spearman(proj, actual)
        assert result["spearman_played"] == pytest.approx(-1.0)
        assert result["spearman_all"] > result["spearman_played"]


class TestSplits:
    def test_train_and_holdout_disjoint_and_known(self):
        splits = load_splits()
        train = set(splits["train_seasons"])
        holdout = set(splits["holdout_seasons"])
        assert train.isdisjoint(holdout)
        assert train | holdout == set(SEASONS)
        assert holdout == {"2024-25"}
        # holdout comes strictly after all train seasons
        assert max(train) < min(holdout)
