"""Historical per-GW FPL data from the vaastav/Fantasy-Premier-League repo.

Downloads merged_gw.csv + players_raw.csv per season (raw cache), then
normalizes every season onto one canonical schema in gw_history.parquet.

Season-to-season schema differences handled here:
- position/team columns only exist in merged_gw from 2020-21; earlier seasons
  get them via players_raw.csv (element_type/team id) + master_team_list.csv.
- name formats vary: "First_Last" (2016-18), "First_Last_123" (2018-20),
  "First Last" (2020-21+). Normalized to "First Last".
- 2016-18 files are latin-1 encoded; later ones utf-8.
- 2024-25 introduced assistant-manager rows (position "AM"); dropped.
- xP exists from 2020-21, expected_goals/expected_assists from 2022-23;
  earlier seasons carry NaN in those columns.
"""

import io
import re

import numpy as np
import pandas as pd

from .http_cache import fetch_cached
from .paths import GW_HISTORY_PARQUET, RAW_VAASTAV_DIR, SEASONS, ensure_dirs

BASE_URL = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"

ELEMENT_TYPE_TO_POSITION = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}

# merged_gw position labels (2020-21+) -> canonical labels
POSITION_ALIASES = {"GK": "GKP", "GKP": "GKP", "DEF": "DEF", "MID": "MID", "FWD": "FWD"}

CANONICAL_COLUMNS = [
    "season",
    "gw",
    "element",
    "player_name",
    "position",
    "team_name",
    "opponent_team_name",
    "was_home",
    "kickoff_time",
    "minutes",
    "goals_scored",
    "assists",
    "clean_sheets",
    "goals_conceded",
    "saves",
    "bonus",
    "total_points",
    "price",
    "xp",
    "expected_goals",
    "expected_assists",
]


def _read_cached_csv(url: str, cache_path) -> pd.DataFrame:
    raw = fetch_cached(url, cache_path)
    try:
        return pd.read_csv(io.BytesIO(raw), encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(io.BytesIO(raw), encoding="latin-1")


def fetch_master_team_list(force: bool = False) -> pd.DataFrame:
    return _read_cached_csv(
        f"{BASE_URL}/master_team_list.csv",
        RAW_VAASTAV_DIR / "master_team_list.csv",
    )


def fetch_season_merged_gw(season: str, force: bool = False) -> pd.DataFrame:
    return _read_cached_csv(
        f"{BASE_URL}/{season}/gws/merged_gw.csv",
        RAW_VAASTAV_DIR / season / "merged_gw.csv",
    )


def fetch_season_players_raw(season: str, force: bool = False) -> pd.DataFrame:
    return _read_cached_csv(
        f"{BASE_URL}/{season}/players_raw.csv",
        RAW_VAASTAV_DIR / season / "players_raw.csv",
    )


def fetch_season_teams(season: str, force: bool = False) -> pd.DataFrame:
    return _read_cached_csv(
        f"{BASE_URL}/{season}/teams.csv",
        RAW_VAASTAV_DIR / season / "teams.csv",
    )


def season_team_map(season: str, team_list: pd.DataFrame, force: bool = False) -> dict:
    """FPL team id -> team name for one season.

    master_team_list.csv is the primary source but is not maintained for
    recent seasons (currently stops at 2023-24); fall back to the season's
    own teams.csv.
    """
    season_teams = team_list[team_list["season"] == season]
    if len(season_teams) > 0:
        return dict(zip(season_teams["team"], season_teams["team_name"]))
    teams = fetch_season_teams(season, force=force)
    return dict(zip(teams["id"], teams["name"]))


def normalize_player_name(name: str) -> str:
    """'Aaron_Cresswell_402' / 'Aaron_Cresswell' -> 'Aaron Cresswell'."""
    name = re.sub(r"_\d+$", "", str(name))
    return name.replace("_", " ").strip()


def normalize_season_gws(
    season: str,
    merged_gw: pd.DataFrame,
    players_raw: pd.DataFrame,
    team_id_to_name: dict,
) -> pd.DataFrame:
    """One season of merged_gw rows -> canonical schema."""
    df = merged_gw.copy()
    df["season"] = season
    df["gw"] = df["GW"].astype(int)
    df["player_name"] = df["name"].map(normalize_player_name)

    if "position" in df.columns:
        df["position"] = df["position"].map(POSITION_ALIASES)
    else:
        element_to_type = dict(zip(players_raw["id"], players_raw["element_type"]))
        df["position"] = (
            df["element"].map(element_to_type).map(ELEMENT_TYPE_TO_POSITION)
        )

    if "team" in df.columns:
        df["team_name"] = df["team"]
    else:
        element_to_team = dict(zip(players_raw["id"], players_raw["team"]))
        df["team_name"] = df["element"].map(element_to_team).map(team_id_to_name)

    df["opponent_team_name"] = df["opponent_team"].map(team_id_to_name)

    # Drop assistant-manager rows (2024-25+): they have no player position.
    df = df[df["position"].notna()].copy()

    df["was_home"] = df["was_home"].astype(bool)
    df["price"] = df["value"] / 10.0

    for optional_col, out_col in [
        ("xP", "xp"),
        ("expected_goals", "expected_goals"),
        ("expected_assists", "expected_assists"),
    ]:
        if optional_col in df.columns:
            df[out_col] = pd.to_numeric(df[optional_col], errors="coerce")
        else:
            df[out_col] = np.nan

    return df[CANONICAL_COLUMNS]


def build_gw_history(force: bool = False) -> pd.DataFrame:
    """Fetch all seasons (cached) and write gw_history.parquet."""
    ensure_dirs()
    team_list = fetch_master_team_list(force=force)

    frames = []
    for season in SEASONS:
        merged_gw = fetch_season_merged_gw(season, force=force)
        players_raw = fetch_season_players_raw(season, force=force)
        team_id_to_name = season_team_map(season, team_list, force=force)
        normalized = normalize_season_gws(season, merged_gw, players_raw, team_id_to_name)
        frames.append(normalized)
        print(f"  vaastav {season}: {len(normalized):>6} player-GW rows")

    history = pd.concat(frames, ignore_index=True)
    history.to_parquet(GW_HISTORY_PARQUET, index=False)
    print(f"  -> {GW_HISTORY_PARQUET.relative_to(GW_HISTORY_PARQUET.parents[2])}: "
          f"{len(history)} rows total")
    return history
