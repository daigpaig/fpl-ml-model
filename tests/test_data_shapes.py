"""Data-shape tests for the Phase 1 processed tables.

These read the parquet files produced by `make fetch-historical`; they are
skipped (not failed) if the data hasn't been fetched yet.
"""

import pandas as pd
import pytest

from src.data.fetch_vaastav import CANONICAL_COLUMNS, normalize_player_name
from src.data.paths import (
    FPL_FIXTURES_PARQUET,
    FPL_PLAYERS_PARQUET,
    GW_HISTORY_PARQUET,
    SEASONS,
    UNDERSTAT_PLAYERS_PARQUET,
    UNDERSTAT_TEAM_MATCHES_PARQUET,
)

VALID_POSITIONS = {"GKP", "DEF", "MID", "FWD"}


def _load(path):
    if not path.exists():
        pytest.skip(f"{path.name} missing - run `make fetch-historical` first")
    return pd.read_parquet(path)


@pytest.fixture(scope="module")
def gw_history():
    return _load(GW_HISTORY_PARQUET)


class TestGwHistory:
    def test_canonical_columns(self, gw_history):
        assert list(gw_history.columns) == CANONICAL_COLUMNS

    def test_all_seasons_present(self, gw_history):
        assert sorted(gw_history["season"].unique()) == SEASONS

    def test_no_nan_in_key_columns(self, gw_history):
        key_cols = [
            "season", "gw", "element", "player_name", "position",
            "team_name", "opponent_team_name", "minutes", "total_points",
        ]
        nan_counts = gw_history[key_cols].isna().sum()
        assert nan_counts.sum() == 0, f"NaNs found:\n{nan_counts[nan_counts > 0]}"

    def test_positions_valid(self, gw_history):
        assert set(gw_history["position"].unique()) <= VALID_POSITIONS

    def test_gw_counts_per_season(self, gw_history):
        gw_stats = gw_history.groupby("season")["gw"].agg(["min", "max", "nunique"])
        assert (gw_stats["min"] == 1).all()
        for season, row in gw_stats.iterrows():
            # 2019-20: COVID restart renumbered GWs 30-38 as 39-47.
            expected_max = 47 if season == "2019-20" else 38
            assert row["max"] == expected_max, f"{season}: max GW {row['max']}"
            # 2022-23 GW7 was postponed entirely (37 distinct GWs).
            assert row["nunique"] >= 37, f"{season}: only {row['nunique']} GWs"

    def test_value_ranges(self, gw_history):
        assert gw_history["minutes"].between(0, 120).all()
        assert (gw_history["price"] > 0).all()
        assert gw_history["was_home"].isin([True, False]).all()

    def test_row_counts_plausible(self, gw_history):
        per_season = gw_history.groupby("season").size()
        # ~500-800 players x 38 GWs => 20k-31k player-GW rows per season
        assert per_season.between(18_000, 32_000).all(), per_season

    def test_player_unique_within_gw(self, gw_history):
        # An element appears at most twice in a GW (double gameweeks).
        counts = gw_history.groupby(["season", "gw", "element"]).size()
        assert counts.max() <= 3


class TestNameNormalization:
    def test_underscore_format(self):
        assert normalize_player_name("Aaron_Cresswell") == "Aaron Cresswell"

    def test_underscore_with_id(self):
        assert normalize_player_name("Aaron_Cresswell_402") == "Aaron Cresswell"

    def test_plain_format_passthrough(self):
        assert normalize_player_name("Aaron Cresswell") == "Aaron Cresswell"


class TestUnderstat:
    def test_players_shape(self):
        players = _load(UNDERSTAT_PLAYERS_PARQUET)
        assert sorted(players["season"].unique()) == SEASONS
        per_season = players.groupby("season").size()
        assert per_season.between(450, 700).all(), per_season
        assert players["player_name"].notna().all()
        assert players["xG"].notna().all()
        assert (players["xG"] >= 0).all()

    def test_team_matches_shape(self):
        matches = _load(UNDERSTAT_TEAM_MATCHES_PARQUET)
        # 380 matches x 2 teams = 760 team-match rows per season
        per_season = matches.groupby("season").size()
        assert (per_season == 760).all(), per_season
        assert pd.api.types.is_datetime64_any_dtype(matches["date"])
        assert matches[["team_name", "xG", "xGA", "date"]].notna().all().all()


class TestFplSnapshot:
    def test_players_shape(self):
        players = _load(FPL_PLAYERS_PARQUET)
        assert len(players) > 400
        assert players["player_id"].notna().all()
        assert players["player_id"].is_unique
        assert set(players["position"].unique()) <= VALID_POSITIONS
        assert (players["price"] > 0).all()

    def test_fixtures_shape(self):
        fixtures = _load(FPL_FIXTURES_PARQUET)
        assert len(fixtures) == 380
        assert fixtures["home_team"].notna().all()
        assert fixtures["away_team"].notna().all()
