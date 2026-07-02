"""Proof of the SPEC anti-lookahead rule.

Features attached to a (season, gw) must be computed only from data strictly
before that GW. We build features twice — once on real data, once after
corrupting (a) every gw_history row from the target GW onward, including the
target GW's own outcomes, and (b) every understat match from the GW's cutoff
date onward — and assert the target GW's feature values are identical.
"""

import pandas as pd
import pytest

from src.data.paths import GW_HISTORY_PARQUET, UNDERSTAT_TEAM_MATCHES_PARQUET
from model.features import (
    ALL_FEATURES,
    add_gw_order,
    build_features,
    gw_cutoff_dates,
)

TARGET_SEASON = "2020-21"
TARGET_GW = 20
# Restrict to two seasons to keep the double build fast; cross-season carry
# from 2019-20 into 2020-21 is still exercised.
SEASONS_IN_TEST = ["2019-20", "2020-21"]


@pytest.fixture(scope="module")
def frames():
    if not GW_HISTORY_PARQUET.exists():
        pytest.skip("run `make fetch-historical` first")
    gw_history = pd.read_parquet(GW_HISTORY_PARQUET)
    understat = pd.read_parquet(UNDERSTAT_TEAM_MATCHES_PARQUET)
    gw_history = gw_history[gw_history["season"].isin(SEASONS_IN_TEST)].copy()
    understat = understat[understat["season"].isin(SEASONS_IN_TEST)].copy()
    return gw_history, understat


def target_gw_features(gw_history, understat):
    feats = build_features(gw_history, understat)
    target = feats[
        (feats["season"] == TARGET_SEASON) & (feats["gw"] == TARGET_GW)
    ]
    return (
        target[["element", "player_name"] + ALL_FEATURES]
        .sort_values("element")
        .reset_index(drop=True)
    )


def corrupt_future(gw_history, understat):
    """Garbage in everything from the target GW onward (inclusive)."""
    gw_history = gw_history.copy()
    understat = understat.copy()

    ordered = add_gw_order(gw_history)
    target_order = ordered.loc[
        (ordered["season"] == TARGET_SEASON) & (ordered["gw"] == TARGET_GW),
        "gw_order",
    ].iloc[0]
    future = ordered["gw_order"] >= target_order
    for col in ["minutes", "goals_scored", "assists", "clean_sheets",
                "goals_conceded", "total_points", "saves", "bonus"]:
        gw_history.loc[future.values, col] = 999

    cutoff = gw_cutoff_dates(gw_history).set_index(["season", "gw"]).loc[
        (TARGET_SEASON, TARGET_GW), "cutoff_date"
    ]
    future_matches = understat["date"] >= cutoff
    for col in ["xG", "xGA", "npxG", "npxGA", "goals_scored", "goals_conceded"]:
        understat.loc[future_matches, col] = 999.0

    return gw_history, understat


def test_features_ignore_future_and_current_gw_outcomes(frames):
    gw_history, understat = frames
    clean = target_gw_features(gw_history, understat)

    corrupted_gw, corrupted_us = corrupt_future(gw_history, understat)
    corrupted = target_gw_features(corrupted_gw, corrupted_us)

    pd.testing.assert_frame_equal(clean, corrupted)
    # Guard against vacuous pass: the corruption must actually change
    # features for LATER gameweeks.
    later = build_features(corrupted_gw, corrupted_us)
    later = later[(later["season"] == TARGET_SEASON) & (later["gw"] == TARGET_GW + 2)]
    assert (later["goal_rate_10"] > 10).any()
