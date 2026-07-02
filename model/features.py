"""Leak-free rolling features for both models.

Anti-lookahead rule (SPEC): every feature attached to a (season, gw) row is
computed from data strictly before that GW. Enforced structurally:

- Player features are computed on a per-GW aggregate table (so a second
  fixture in a double GW cannot see the first), then lagged with shift(1)
  BEFORE any rolling window is applied.
- Team form from understat is attached as-of the GW's cutoff date (the day of
  the GW's earliest kickoff) with allow_exact_matches=False, and the form
  values themselves are shift(1)-lagged per team.

tests/test_no_lookahead.py proves this by mutating all future data and
checking features are unchanged.

Cross-season player identity: vaastav `element` ids reset every season, so
players are keyed by (player_name, position) — see DECISIONS.md.
"""

import pandas as pd

from src.data.paths import (
    GW_HISTORY_PARQUET,
    SEASONS,
    UNDERSTAT_TEAM_MATCHES_PARQUET,
)

SEASON_ORDER = {s: i for i, s in enumerate(SEASONS)}

# Rolling windows (in GWs / matches). Small enough to track form, large
# enough not to be noise; see DECISIONS.md.
MINUTES_WINDOW = 5      # start/played rates
RATE_WINDOW = 10        # per-appearance goal/assist rates
SHARE_WINDOW = 20       # player share of team goals
TEAM_FORM_WINDOW = 10   # team xG/xGA form

PLAYER_FEATURES = [
    "played_rate_5",
    "start_rate_5",
    "minutes_mean_5",
    "goal_rate_10",
    "assist_rate_10",
    "goal_share_20",
    "assist_share_20",
]
TEAM_FEATURES = ["team_xg_10", "team_xga_10", "opp_xg_10", "opp_xga_10"]
ALL_FEATURES = PLAYER_FEATURES + TEAM_FEATURES


def add_gw_order(df: pd.DataFrame) -> pd.DataFrame:
    """Global GW ordering across seasons (season index * 100 + gw)."""
    df = df.copy()
    df["gw_order"] = df["season"].map(SEASON_ORDER) * 100 + df["gw"]
    return df


def _lagged_rolling(
    df: pd.DataFrame, group: str, col: str, window: int, agg: str
) -> pd.Series:
    """Rolling agg over the previous `window` rows, excluding the current row.

    `df` must be sorted by [group, time] with a clean RangeIndex.
    """
    shifted = df.groupby(group, sort=False)[col].shift(1)
    return (
        shifted.groupby(df[group], sort=False)
        .rolling(window, min_periods=1)
        .agg(agg)
        .reset_index(level=0, drop=True)
    )


def player_gw_features(gw_history: pd.DataFrame) -> pd.DataFrame:
    """Per (player_key, season, gw): lagged rolling minutes/goal/assist stats."""
    df = add_gw_order(gw_history)
    df["player_key"] = df["player_name"] + "|" + df["position"]

    per_gw = df.groupby(
        ["player_key", "team_name", "season", "gw", "gw_order"], as_index=False
    ).agg(
        minutes=("minutes", "sum"),
        goals=("goals_scored", "sum"),
        assists=("assists", "sum"),
        max_minutes=("minutes", "max"),
    )
    per_gw["played"] = (per_gw["minutes"] > 0).astype(float)
    per_gw["started60"] = (per_gw["max_minutes"] >= 60).astype(float)
    per_gw = per_gw.sort_values(["player_key", "gw_order"]).reset_index(drop=True)

    per_gw["played_rate_5"] = _lagged_rolling(
        per_gw, "player_key", "played", MINUTES_WINDOW, "mean")
    per_gw["start_rate_5"] = _lagged_rolling(
        per_gw, "player_key", "started60", MINUTES_WINDOW, "mean")
    per_gw["minutes_mean_5"] = _lagged_rolling(
        per_gw, "player_key", "minutes", MINUTES_WINDOW, "mean")

    goals_10 = _lagged_rolling(per_gw, "player_key", "goals", RATE_WINDOW, "sum")
    assists_10 = _lagged_rolling(per_gw, "player_key", "assists", RATE_WINDOW, "sum")
    apps_10 = _lagged_rolling(per_gw, "player_key", "played", RATE_WINDOW, "sum")
    per_gw["goal_rate_10"] = goals_10 / apps_10.clip(lower=1)
    per_gw["assist_rate_10"] = assists_10 / apps_10.clip(lower=1)

    per_gw["goals_20"] = _lagged_rolling(
        per_gw, "player_key", "goals", SHARE_WINDOW, "sum")
    per_gw["assists_20"] = _lagged_rolling(
        per_gw, "player_key", "assists", SHARE_WINDOW, "sum")

    # Team goals over the same lagged window -> player's share of team output.
    team_gw = df.groupby(
        ["team_name", "season", "gw", "gw_order"], as_index=False
    ).agg(team_goals=("goals_scored", "sum"))
    team_gw = team_gw.sort_values(["team_name", "gw_order"]).reset_index(drop=True)
    team_gw["team_goals_20"] = _lagged_rolling(
        team_gw, "team_name", "team_goals", SHARE_WINDOW, "sum")

    per_gw = per_gw.merge(
        team_gw[["team_name", "season", "gw", "team_goals_20"]],
        on=["team_name", "season", "gw"],
        how="left",
    )
    # +1 in the denominator: mild shrinkage, avoids 0/0 for teams w/o history.
    per_gw["goal_share_20"] = per_gw["goals_20"] / (per_gw["team_goals_20"] + 1.0)
    per_gw["assist_share_20"] = per_gw["assists_20"] / (per_gw["team_goals_20"] + 1.0)

    keep = ["player_key", "team_name", "season", "gw"] + PLAYER_FEATURES
    return per_gw[keep].fillna({c: 0.0 for c in PLAYER_FEATURES})


def team_form_table(understat_matches: pd.DataFrame) -> pd.DataFrame:
    """Per (team, match date): lagged rolling xG/xGA over prior matches."""
    m = understat_matches.sort_values(["team_name", "date"]).reset_index(drop=True)
    m["xg_10"] = _lagged_rolling(m, "team_name", "xG", TEAM_FORM_WINDOW, "mean")
    m["xga_10"] = _lagged_rolling(m, "team_name", "xGA", TEAM_FORM_WINDOW, "mean")
    return m[["team_name", "date", "xg_10", "xga_10"]].dropna()


def gw_cutoff_dates(gw_history: pd.DataFrame) -> pd.DataFrame:
    """Per (season, gw): the day of the earliest kickoff — the anti-lookahead
    cutoff for date-stamped sources."""
    kickoffs = pd.to_datetime(gw_history["kickoff_time"]).dt.tz_localize(None)
    cutoffs = (
        gw_history.assign(kickoff=kickoffs)
        .groupby(["season", "gw"], as_index=False)["kickoff"]
        .min()
    )
    cutoffs["cutoff_date"] = cutoffs["kickoff"].dt.normalize()
    return cutoffs[["season", "gw", "cutoff_date"]]


def team_gw_form(
    gw_history: pd.DataFrame, understat_matches: pd.DataFrame
) -> pd.DataFrame:
    """Per (season, gw, team): xG/xGA form strictly before the GW's cutoff."""
    cutoffs = gw_cutoff_dates(gw_history)
    teams = gw_history[["season", "gw", "team_name"]].drop_duplicates()
    team_gw = teams.merge(cutoffs, on=["season", "gw"])

    form = team_form_table(understat_matches)
    merged = pd.merge_asof(
        team_gw.sort_values("cutoff_date"),
        form.sort_values("date"),
        left_on="cutoff_date",
        right_on="date",
        by="team_name",
        allow_exact_matches=False,
    )
    return merged[["season", "gw", "team_name", "xg_10", "xga_10"]]


def build_features(
    gw_history: pd.DataFrame | None = None,
    understat_matches: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """One row per gw_history row, with all rolling features attached.

    Loads the processed parquets if frames aren't passed in (tests pass
    truncated/mutated frames to prove no lookahead).
    """
    if gw_history is None:
        gw_history = pd.read_parquet(GW_HISTORY_PARQUET)
    if understat_matches is None:
        understat_matches = pd.read_parquet(UNDERSTAT_TEAM_MATCHES_PARQUET)

    df = add_gw_order(gw_history)
    df["player_key"] = df["player_name"] + "|" + df["position"]

    # team_name in the join keys disambiguates distinct players who share a
    # (name, position) key within a season (SPEC: team + name, never name-only).
    player_feats = player_gw_features(gw_history)
    df = df.merge(
        player_feats, on=["player_key", "team_name", "season", "gw"], how="left"
    )

    form = team_gw_form(gw_history, understat_matches)
    df = df.merge(
        form.rename(columns={"xg_10": "team_xg_10", "xga_10": "team_xga_10"}),
        on=["season", "gw", "team_name"],
        how="left",
    )
    df = df.merge(
        form.rename(columns={
            "team_name": "opponent_team_name",
            "xg_10": "opp_xg_10",
            "xga_10": "opp_xga_10",
        }),
        on=["season", "gw", "opponent_team_name"],
        how="left",
    )

    # No history yet (new player / GW1 2016-17) -> neutral zeros; team form
    # NaN only at the very start of 2016-17 -> fill with league-typical 1.35.
    df = df.fillna({c: 0.0 for c in PLAYER_FEATURES})
    df = df.fillna({c: 1.35 for c in TEAM_FEATURES})
    return df
