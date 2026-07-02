"""Shared output decomposition and xPts arithmetic for both models.

Both models emit fixture-level component probabilities with identical
meanings, then this module turns them into the per-player per-GW
decomposition {start_prob, goal_prob, assist_prob, cs_prob, xPts} that the
future divergence layer diffs component-wise:

- start_prob : P(player plays 60+ minutes)
- play_prob  : P(player plays at all) — internal, used for appearance points
- goal_prob  : P(player scores >= 1 goal in the fixture)
- assist_prob: P(player provides >= 1 assist in the fixture)
- cs_prob    : P(player's TEAM keeps a clean sheet) — unconditional on the
               player featuring, so market and stats views stay comparable

xPts (interpretable approximation of FPL scoring):
    start_prob*2 + (play_prob - start_prob)*1        appearance
  + goal_prob * goal_points(position)
  + assist_prob * 3
  + cs_prob * start_prob * cs_points(position)       CS needs 60+ minutes
Bonus, cards, saves and goals-conceded penalties are out of scope (logged
in DECISIONS.md).
"""

import json

import pandas as pd

from src.data.paths import PROJECT_ROOT

GOAL_POINTS = {"GKP": 6, "DEF": 6, "MID": 5, "FWD": 4}
CS_POINTS = {"GKP": 4, "DEF": 4, "MID": 1, "FWD": 0}
ASSIST_POINTS = 3

SPLITS_JSON = PROJECT_ROOT / "eval" / "splits.json"

IDENTITY_COLUMNS = [
    "season", "gw", "element", "player_name", "team_name", "position",
]
COMPONENT_COLUMNS = ["start_prob", "goal_prob", "assist_prob", "cs_prob"]
DECOMPOSITION_COLUMNS = IDENTITY_COLUMNS + COMPONENT_COLUMNS + ["xpts"]


def load_splits() -> dict:
    return json.loads(SPLITS_JSON.read_text())


def fixture_xpts(df: pd.DataFrame) -> pd.Series:
    """Expected FPL points for one fixture row (needs component + play_prob
    + position columns)."""
    appearance = df["start_prob"] * 2 + (df["play_prob"] - df["start_prob"]) * 1
    goals = df["goal_prob"] * df["position"].map(GOAL_POINTS)
    assists = df["assist_prob"] * ASSIST_POINTS
    clean_sheets = df["cs_prob"] * df["start_prob"] * df["position"].map(CS_POINTS)
    return appearance + goals + assists + clean_sheets


def to_gw_decomposition(fixture_rows: pd.DataFrame) -> pd.DataFrame:
    """Fixture-level component rows -> one decomposition row per player-GW.

    Double gameweeks: xPts adds across fixtures; event probabilities combine
    as P(at least one across fixtures) = 1 - prod(1 - p).
    """
    df = fixture_rows.copy()
    df["xpts"] = fixture_xpts(df)

    def at_least_once(p: pd.Series) -> float:
        return 1.0 - (1.0 - p).prod()

    out = df.groupby(IDENTITY_COLUMNS, as_index=False).agg(
        start_prob=("start_prob", "mean"),
        goal_prob=("goal_prob", at_least_once),
        assist_prob=("assist_prob", at_least_once),
        cs_prob=("cs_prob", at_least_once),
        xpts=("xpts", "sum"),
    )
    return out[DECOMPOSITION_COLUMNS].sort_values(
        "xpts", ascending=False
    ).reset_index(drop=True)
