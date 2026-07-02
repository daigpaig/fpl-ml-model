"""Current-season snapshot from the official FPL API.

bootstrap-static and fixtures are fetched once each and cached as raw JSON;
processed players/fixtures parquet files are rebuilt from the cache.
"""

import json

import pandas as pd

from .http_cache import fetch_cached
from .paths import (
    FPL_FIXTURES_PARQUET,
    FPL_PLAYERS_PARQUET,
    RAW_FPL_API_DIR,
    ensure_dirs,
)

BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
FIXTURES_URL = "https://fantasy.premierleague.com/api/fixtures/"

ELEMENT_TYPE_TO_POSITION = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}


def fetch_bootstrap(force: bool = False) -> dict:
    raw = fetch_cached(BOOTSTRAP_URL, RAW_FPL_API_DIR / "bootstrap.json", force=force)
    return json.loads(raw)


def fetch_fixtures(force: bool = False) -> list:
    raw = fetch_cached(FIXTURES_URL, RAW_FPL_API_DIR / "fixtures.json", force=force)
    return json.loads(raw)


def build_players_table(bootstrap: dict) -> pd.DataFrame:
    players = pd.DataFrame(bootstrap["elements"])
    teams = pd.DataFrame(bootstrap["teams"])[["id", "name", "short_name"]]

    players["position"] = players["element_type"].map(ELEMENT_TYPE_TO_POSITION)
    players = players[players["position"].notna()].copy()  # drop managers
    players["price"] = players["now_cost"] / 10.0
    players["player_name"] = (
        players["first_name"].str.strip() + " " + players["second_name"].str.strip()
    )

    players = players.merge(
        teams.rename(
            columns={"id": "team", "name": "team_name", "short_name": "team_short"}
        ),
        on="team",
        how="left",
    )

    return players[
        ["id", "player_name", "web_name", "team_name", "team_short",
         "position", "price", "status", "chance_of_playing_next_round"]
    ].rename(columns={"id": "player_id"})


def build_fixtures_table(fixtures: list, bootstrap: dict) -> pd.DataFrame:
    df = pd.DataFrame(fixtures)
    teams = pd.DataFrame(bootstrap["teams"])[["id", "name"]]
    team_id_to_name = dict(zip(teams["id"], teams["name"]))

    df["home_team"] = df["team_h"].map(team_id_to_name)
    df["away_team"] = df["team_a"].map(team_id_to_name)
    return df[
        ["id", "event", "kickoff_time", "home_team", "away_team", "finished"]
    ].rename(columns={"id": "fixture_id", "event": "gw"})


def build_fpl_snapshot(force: bool = False):
    """Fetch (cached) and write fpl_players.parquet + fpl_fixtures.parquet."""
    ensure_dirs()
    bootstrap = fetch_bootstrap(force=force)
    fixtures = fetch_fixtures(force=force)

    players = build_players_table(bootstrap)
    fixtures_df = build_fixtures_table(fixtures, bootstrap)

    players.to_parquet(FPL_PLAYERS_PARQUET, index=False)
    fixtures_df.to_parquet(FPL_FIXTURES_PARQUET, index=False)
    print(f"  fpl_api: {len(players)} players, {len(fixtures_df)} fixtures")
    return players, fixtures_df
