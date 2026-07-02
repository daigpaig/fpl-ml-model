"""Betting-market model: historical match odds -> implied probabilities -> xPts.

Pipeline per fixture:
1. Vig-strip the 1X2 and over/under-2.5 market-average odds by proportional
   normalization (SPEC decision).
2. Fit an independent-Poisson score model (lambda_home, lambda_away) that
   best reproduces the vig-free market probabilities — this converts match
   odds into implied team goal expectations.
3. cs_prob = P(opponent scores 0) = exp(-lambda_opponent).
4. Allocate team goal expectation to players by their trailing share of team
   goals/assists (leak-free features): lambda_player = lambda_team * share,
   goal_prob = 1 - exp(-lambda_player). Historical player-prop odds are not
   freely available, so team-level markets + prior share is the market model
   (DECISIONS.md).
5. start_prob/play_prob come from the shared rolling-minutes model
   (start_rate_5 / played_rate_5) — the market does not price starts.
"""

from functools import lru_cache

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

from src.data.paths import MATCH_ODDS_PARQUET
from model.common import to_gw_decomposition

MAX_GOALS = 10


def strip_vig(odds: np.ndarray) -> np.ndarray:
    """Decimal odds for mutually exclusive outcomes -> probabilities summing
    to 1 (proportional normalization)."""
    implied = 1.0 / np.asarray(odds, dtype=float)
    return implied / implied.sum()


@lru_cache(maxsize=8192)
def implied_lambdas(
    home_odds: float, draw_odds: float, away_odds: float,
    over25_odds: float, under25_odds: float,
) -> tuple[float, float]:
    """Fit (lambda_home, lambda_away) to the vig-free 1X2 + O/U 2.5 probs."""
    p_home, p_draw, p_away = strip_vig(np.array([home_odds, draw_odds, away_odds]))
    p_over, _ = strip_vig(np.array([over25_odds, under25_odds]))

    goals = np.arange(MAX_GOALS + 1)
    total = np.add.outer(goals, goals)

    def loss(log_lambdas):
        lam_h, lam_a = np.exp(log_lambdas)
        joint = np.outer(poisson.pmf(goals, lam_h), poisson.pmf(goals, lam_a))
        m_home = np.tril(joint, -1).sum()
        m_away = np.triu(joint, 1).sum()
        m_draw = np.trace(joint)
        m_over = joint[total >= 3].sum()
        return (
            (m_home - p_home) ** 2
            + (m_draw - p_draw) ** 2
            + (m_away - p_away) ** 2
            + (m_over - p_over) ** 2
        )

    result = minimize(loss, x0=np.log([1.4, 1.1]), method="Nelder-Mead")
    lam_h, lam_a = np.exp(result.x)
    return float(lam_h), float(lam_a)


def fixture_lambdas(match_odds: pd.DataFrame, season: str) -> pd.DataFrame:
    """Per (home_team, away_team) of a season: implied goal expectations."""
    rows = match_odds[match_odds["season"] == season]
    records = []
    for row in rows.itertuples():
        lam_h, lam_a = implied_lambdas(
            row.home_odds, row.draw_odds, row.away_odds,
            row.over25_odds, row.under25_odds,
        )
        records.append({
            "home_team": row.home_team,
            "away_team": row.away_team,
            "lambda_home": lam_h,
            "lambda_away": lam_a,
        })
    return pd.DataFrame(records)


def project(features: pd.DataFrame, season: str, gw: int) -> pd.DataFrame:
    """Market-model decomposition for every player with a fixture in the GW."""
    rows = features[(features["season"] == season) & (features["gw"] == gw)].copy()
    if rows.empty:
        raise ValueError(f"no fixtures found for {season} GW{gw}")

    match_odds = pd.read_parquet(MATCH_ODDS_PARQUET)
    lambdas = fixture_lambdas(match_odds, season)

    rows["home_team"] = np.where(
        rows["was_home"], rows["team_name"], rows["opponent_team_name"])
    rows["away_team"] = np.where(
        rows["was_home"], rows["opponent_team_name"], rows["team_name"])
    rows = rows.merge(lambdas, on=["home_team", "away_team"], how="left")
    if rows["lambda_home"].isna().any():
        missing = rows[rows["lambda_home"].isna()][
            ["home_team", "away_team"]].drop_duplicates()
        raise ValueError(f"no odds for fixtures:\n{missing}")

    team_lambda = np.where(rows["was_home"], rows["lambda_home"], rows["lambda_away"])
    opp_lambda = np.where(rows["was_home"], rows["lambda_away"], rows["lambda_home"])

    rows["goal_prob"] = 1.0 - np.exp(-team_lambda * rows["goal_share_20"])
    rows["assist_prob"] = 1.0 - np.exp(-team_lambda * rows["assist_share_20"])
    rows["cs_prob"] = np.exp(-opp_lambda)
    rows["start_prob"] = rows["start_rate_5"]
    rows["play_prob"] = rows["played_rate_5"].clip(lower=rows["start_rate_5"])

    return to_gw_decomposition(rows)
