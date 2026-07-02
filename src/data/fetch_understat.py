"""Understat EPL data: season player aggregates + per-match team xG history.

understat.com serves league data from a JSON endpoint
(getLeagueData/{league}/{year}) — the old embedded-JSON-in-HTML pages are
now empty shells. One request per season, cached as raw JSON, parsed into
two processed tables:

- understat_players.parquet: one row per player per season (xG, xA, npxG, ...)
- understat_team_matches.parquet: one row per team per match, date-stamped,
  so later rolling features can be built without lookahead.
"""

import json

import pandas as pd

from .http_cache import fetch_cached
from .paths import (
    RAW_UNDERSTAT_DIR,
    SEASONS,
    UNDERSTAT_PLAYERS_PARQUET,
    UNDERSTAT_TEAM_MATCHES_PARQUET,
    ensure_dirs,
)
from .team_names import canonical_team_name

LEAGUE_DATA_URL = "https://understat.com/getLeagueData/EPL/{year}"

REQUEST_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


def season_start_year(season: str) -> int:
    """'2016-17' -> 2016 (understat keys seasons by their starting year)."""
    return int(season.split("-")[0])


def fetch_league_data(season: str, force: bool = False) -> dict:
    year = season_start_year(season)
    raw = fetch_cached(
        LEAGUE_DATA_URL.format(year=year),
        RAW_UNDERSTAT_DIR / f"epl_{season}.json",
        force=force,
        headers=REQUEST_HEADERS,
    )
    return json.loads(raw)


def parse_players(league_data: dict, season: str) -> pd.DataFrame:
    df = pd.DataFrame(league_data["players"])
    df["season"] = season
    numeric_cols = [
        "games", "time", "goals", "xG", "assists", "xA", "shots",
        "key_passes", "npg", "npxG", "xGChain", "xGBuildup",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # team_title is comma-joined for players who moved mid-season.
    df["team_title"] = df["team_title"].map(
        lambda names: ",".join(
            canonical_team_name(n, "understat") for n in str(names).split(",")
        )
    )
    return df[
        ["season", "id", "player_name", "team_title", "position"] + numeric_cols
    ].rename(columns={"id": "understat_id", "team_title": "team_name"})


def parse_team_matches(league_data: dict, season: str) -> pd.DataFrame:
    rows = []
    for team in league_data["teams"].values():
        for match in team["history"]:
            rows.append({
                "season": season,
                "team_name": canonical_team_name(team["title"], "understat"),
                "date": match["date"],
                "is_home": match["h_a"] == "h",
                "xG": match["xG"],
                "xGA": match["xGA"],
                "npxG": match["npxG"],
                "npxGA": match["npxGA"],
                "goals_scored": match["scored"],
                "goals_conceded": match["missed"],
                "result": match["result"],
                "points": match["pts"],
            })
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


def build_understat(force: bool = False):
    """Fetch all seasons (cached) and write both understat parquet files."""
    ensure_dirs()
    player_frames, match_frames = [], []
    for season in SEASONS:
        league_data = fetch_league_data(season, force=force)
        players = parse_players(league_data, season)
        matches = parse_team_matches(league_data, season)
        player_frames.append(players)
        match_frames.append(matches)
        print(f"  understat {season}: {len(players):>4} players, "
              f"{len(matches):>4} team-matches")

    players_all = pd.concat(player_frames, ignore_index=True)
    matches_all = pd.concat(match_frames, ignore_index=True)
    players_all.to_parquet(UNDERSTAT_PLAYERS_PARQUET, index=False)
    matches_all.to_parquet(UNDERSTAT_TEAM_MATCHES_PARQUET, index=False)
    print(f"  -> understat_players.parquet: {len(players_all)} rows")
    print(f"  -> understat_team_matches.parquet: {len(matches_all)} rows")
    return players_all, matches_all
