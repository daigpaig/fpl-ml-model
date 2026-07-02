"""Phase 2 model tests: vig stripping, implied lambdas, and the shared
decomposition contract both models must honour."""

import numpy as np
import pandas as pd
import pytest
from scipy.stats import poisson

from src.data.paths import GW_HISTORY_PARQUET
from model import odds_model
from model.common import DECOMPOSITION_COLUMNS, to_gw_decomposition
from model.stats_model import StatsModel

SAMPLE_SEASON, SAMPLE_GW = "2024-25", 20


class TestVigStripping:
    def test_probs_sum_to_one_and_keep_order(self):
        probs = odds_model.strip_vig(np.array([1.95, 3.6, 4.2]))
        assert probs.sum() == pytest.approx(1.0)
        assert probs[0] > probs[1] > probs[2]

    def test_overround_removed_proportionally(self):
        # equal odds with vig -> exactly equal probabilities
        probs = odds_model.strip_vig(np.array([2.9, 2.9, 2.9]))
        assert np.allclose(probs, 1 / 3)


class TestImpliedLambdas:
    def test_recovers_known_poisson_lambdas(self):
        lam_h, lam_a = 1.8, 1.0
        goals = np.arange(odds_model.MAX_GOALS + 1)
        joint = np.outer(poisson.pmf(goals, lam_h), poisson.pmf(goals, lam_a))
        p_home = np.tril(joint, -1).sum()
        p_draw = np.trace(joint)
        p_away = np.triu(joint, 1).sum()
        p_over = joint[np.add.outer(goals, goals) >= 3].sum()

        fit_h, fit_a = odds_model.implied_lambdas(
            1 / p_home, 1 / p_draw, 1 / p_away, 1 / p_over, 1 / (1 - p_over)
        )
        assert fit_h == pytest.approx(lam_h, abs=0.05)
        assert fit_a == pytest.approx(lam_a, abs=0.05)

    def test_home_favourite_gets_higher_lambda(self):
        lam_h, lam_a = odds_model.implied_lambdas(1.4, 5.0, 7.5, 1.6, 2.3)
        assert lam_h > lam_a


class TestGwDecomposition:
    def test_double_gw_combination(self):
        fixtures = pd.DataFrame({
            "season": ["2024-25"] * 2, "gw": [24] * 2, "element": [7] * 2,
            "player_name": ["A"] * 2, "team_name": ["T"] * 2,
            "position": ["MID"] * 2,
            "start_prob": [0.8, 0.8], "play_prob": [0.9, 0.9],
            "goal_prob": [0.5, 0.2], "assist_prob": [0.3, 0.1],
            "cs_prob": [0.4, 0.25],
        })
        out = to_gw_decomposition(fixtures)
        assert len(out) == 1
        row = out.iloc[0]
        assert row["goal_prob"] == pytest.approx(1 - 0.5 * 0.8)
        assert row["assist_prob"] == pytest.approx(1 - 0.7 * 0.9)
        single = to_gw_decomposition(fixtures.iloc[[0]])
        assert row["xpts"] > single.iloc[0]["xpts"]  # DGW adds points


@pytest.fixture(scope="module")
def sample_projections():
    if not GW_HISTORY_PARQUET.exists():
        pytest.skip("run `make fetch-historical` first")
    from model.features import build_features
    features = build_features()
    odds_proj = odds_model.project(features, SAMPLE_SEASON, SAMPLE_GW)
    stats_proj = StatsModel().fit(features).project(
        features, SAMPLE_SEASON, SAMPLE_GW)
    return odds_proj, stats_proj


class TestSharedDecomposition:
    def test_same_columns_both_models(self, sample_projections):
        odds_proj, stats_proj = sample_projections
        assert list(odds_proj.columns) == DECOMPOSITION_COLUMNS
        assert list(stats_proj.columns) == DECOMPOSITION_COLUMNS

    def test_same_players_both_models(self, sample_projections):
        odds_proj, stats_proj = sample_projections
        assert set(odds_proj["element"]) == set(stats_proj["element"])
        assert odds_proj["element"].is_unique
        assert stats_proj["element"].is_unique

    def test_probabilities_and_xpts_valid(self, sample_projections):
        for proj in sample_projections:
            for col in ["start_prob", "goal_prob", "assist_prob", "cs_prob"]:
                assert proj[col].between(0, 1).all(), col
            assert (proj["xpts"] >= 0).all()
            assert proj["xpts"].max() < 15  # sanity ceiling for a single GW
            assert proj[DECOMPOSITION_COLUMNS].notna().all().all()

    def test_projections_are_discriminative(self, sample_projections):
        for proj in sample_projections:
            assert proj["xpts"].nunique() > 100
