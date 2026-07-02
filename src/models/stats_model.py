"""Stats model: rolling FPL/understat features -> logistic regressions -> xPts.

Three interpretable logistic regressions, trained only on the train seasons
from eval/splits.json:

- goal:   P(player scores >= 1 in a fixture)   — player-fixture level
- assist: P(player assists >= 1 in a fixture)  — player-fixture level
- cs:     P(team concedes 0 in a fixture)      — team-fixture level
          (actual conceded goals come from the football-data final scores)

start_prob/play_prob come from the shared rolling-minutes model
(start_rate_5 / played_rate_5), same as the odds model. Logistic regression
over a handful of named rolling features keeps every divergence explainable
(SPEC: interpretability over marginal accuracy).
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from src.data.paths import MATCH_ODDS_PARQUET
from src.models.common import load_splits, to_gw_decomposition

PLAYER_MODEL_FEATURES = [
    "played_rate_5",
    "start_rate_5",
    "minutes_mean_5",
    "goal_rate_10",
    "assist_rate_10",
    "goal_share_20",
    "assist_share_20",
    "team_xg_10",
    "opp_xga_10",
    "is_home",
    "price",
    "is_gkp",
    "is_def",
    "is_mid",
]
CS_MODEL_FEATURES = ["team_xga_10", "opp_xg_10", "is_home"]


def _with_encodings(features: pd.DataFrame) -> pd.DataFrame:
    df = features.copy()
    df["is_home"] = df["was_home"].astype(float)
    for pos in ("gkp", "def", "mid"):
        df[f"is_{pos}"] = (df["position"] == pos.upper()).astype(float)
    return df


def team_fixture_frame(features: pd.DataFrame) -> pd.DataFrame:
    """One row per team-fixture with form features and conceded-goals target."""
    team_rows = _with_encodings(features)[
        ["season", "gw", "team_name", "opponent_team_name", "was_home",
         "is_home", "team_xga_10", "opp_xg_10"]
    ].drop_duplicates()

    scores = pd.read_parquet(MATCH_ODDS_PARQUET)
    home = scores.rename(columns={
        "home_team": "team_name", "away_team": "opponent_team_name",
        "away_goals": "conceded",
    }).assign(was_home=True)
    away = scores.rename(columns={
        "away_team": "team_name", "home_team": "opponent_team_name",
        "home_goals": "conceded",
    }).assign(was_home=False)
    conceded = pd.concat([home, away])[
        ["season", "team_name", "opponent_team_name", "was_home", "conceded"]
    ]

    merged = team_rows.merge(
        conceded,
        on=["season", "team_name", "opponent_team_name", "was_home"],
        how="left",
    )
    merged["clean_sheet"] = (merged["conceded"] == 0).astype(int)
    return merged


class StatsModel:
    def __init__(self):
        self.goal_clf: Pipeline | None = None
        self.assist_clf: Pipeline | None = None
        self.cs_clf: Pipeline | None = None

    @staticmethod
    def _new_clf() -> Pipeline:
        return make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=1000, C=1.0)
        )

    def fit(self, features: pd.DataFrame, train_seasons: list[str] | None = None):
        if train_seasons is None:
            train_seasons = load_splits()["train_seasons"]

        train = _with_encodings(
            features[features["season"].isin(train_seasons)]
        )
        X = train[PLAYER_MODEL_FEATURES]
        self.goal_clf = self._new_clf().fit(X, (train["goals_scored"] >= 1))
        self.assist_clf = self._new_clf().fit(X, (train["assists"] >= 1))

        teams = team_fixture_frame(features[features["season"].isin(train_seasons)])
        teams = teams.dropna(subset=["conceded"])
        self.cs_clf = self._new_clf().fit(
            teams[CS_MODEL_FEATURES], teams["clean_sheet"]
        )
        return self

    def project(self, features: pd.DataFrame, season: str, gw: int) -> pd.DataFrame:
        """Stats-model decomposition for every player with a fixture in the GW."""
        if self.goal_clf is None:
            raise RuntimeError("call fit() before project()")
        rows = features[
            (features["season"] == season) & (features["gw"] == gw)
        ].copy()
        if rows.empty:
            raise ValueError(f"no fixtures found for {season} GW{gw}")
        rows = _with_encodings(rows)

        X = rows[PLAYER_MODEL_FEATURES]
        rows["goal_prob"] = self.goal_clf.predict_proba(X)[:, 1]
        rows["assist_prob"] = self.assist_clf.predict_proba(X)[:, 1]
        rows["cs_prob"] = self.cs_clf.predict_proba(rows[CS_MODEL_FEATURES])[:, 1]
        rows["start_prob"] = rows["start_rate_5"]
        rows["play_prob"] = rows["played_rate_5"].clip(lower=rows["start_rate_5"])

        return to_gw_decomposition(rows)
