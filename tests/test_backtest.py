"""Eval-layer tests: metric correctness and split hygiene."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))
from backtest import split_config, within_gw_spearman  # noqa: E402

from src.data.paths import SEASONS
from model.common import load_splits


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
        assert result["spearman_restricted"] == pytest.approx(1.0)
        assert result["n_players"] == 4

    def test_inverted_ranking(self):
        proj, actual = _frames([4, 3, 2, 1], [2, 5, 6, 12], [90] * 4)
        assert within_gw_spearman(proj, actual)["spearman_all"] == pytest.approx(-1.0)

    def test_restricted_filter_excludes_benchwarmers(self):
        # Ranking is perfect overall but inverted among those who played.
        proj, actual = _frames(
            [0, 0, 1, 2], [0, 0, 6, 3], [0, 0, 90, 90])
        result = within_gw_spearman(proj, actual)
        assert result["spearman_restricted"] == pytest.approx(-1.0)
        assert result["spearman_all"] > result["spearman_restricted"]


class TestSplits:
    def test_dev_split(self):
        dev = split_config("dev")
        assert dev["eval_seasons"] == ["2023-24"]
        # training strictly before the eval season
        assert max(dev["train_seasons"]) < "2023-24"
        assert "2023-24" not in dev["train_seasons"]
        assert "2024-25" not in dev["train_seasons"]

    def test_sealed_split_unchanged(self):
        sealed = split_config("sealed")
        assert sealed["eval_seasons"] == ["2024-25"]
        assert sealed["train_seasons"] == SEASONS[:-1]

    def test_no_split_trains_on_its_eval_seasons(self):
        for name in ("dev", "sealed"):
            cfg = split_config(name)
            assert set(cfg["train_seasons"]).isdisjoint(cfg["eval_seasons"])
            assert max(cfg["train_seasons"]) < min(cfg["eval_seasons"])

    def test_legacy_keys_match_sealed(self):
        # src/project.py's default StatsModel().fit() reads the legacy keys;
        # they must stay equal to the sealed era.
        splits = load_splits()
        assert splits["train_seasons"] == split_config("sealed")["train_seasons"]
        assert splits["holdout_seasons"] == split_config("sealed")["eval_seasons"]
