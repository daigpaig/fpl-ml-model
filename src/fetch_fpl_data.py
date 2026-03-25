import requests
import pandas as pd
import os

BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
FIXTURES_URL = "https://fantasy.premierleague.com/api/fixtures/"

GW = 32

def fetch_bootstrap_data():
    response = requests.get(BOOTSTRAP_URL)
    response.raise_for_status()
    return response.json()

def fetch_fixtures():
    response = requests.get(FIXTURES_URL)
    response.raise_for_status()
    return response.json()

def main():
    data = fetch_bootstrap_data()

    players = pd.DataFrame(data["elements"])
    teams = pd.DataFrame(data["teams"])[["id", "name", "short_name"]]
    positions = pd.DataFrame(data["element_types"])[["id", "singular_name_short"]]

    players = players[["id", "web_name", "team", "element_type", "now_cost"]].copy()

    players = players.merge(
        teams,
        left_on="team",
        right_on="id",
        how="left",
        suffixes=("", "_team")
    )

    players = players.merge(
        positions,
        left_on="element_type",
        right_on="id",
        how="left",
        suffixes=("", "_position")
    )

    players["now_cost"] = players["now_cost"] / 10

    players = players.rename(columns={
        "id": "player_id",
        "web_name": "player_name",
        "name": "team_name",
        "short_name": "team_short",
        "singular_name_short": "position",
        "now_cost": "price"
    })

    print(players[[
        "player_id", "player_name", "team_name", "team_short", "position", "price"
    ]].head(20))

    os.makedirs("data", exist_ok=True)
    players.to_csv("data/players.csv", index=False)

    print("\nSaved to data/players.csv")

    fixtures_data = fetch_fixtures()
    fixtures = pd.DataFrame(fixtures_data)

    teams = teams.rename(columns={"id": "team_id"})

    fixtures = fixtures.merge(
        teams,
        left_on="team_h",
        right_on="team_id",
        how="left"
    ).rename(columns={"name": "home_team"})

    fixtures = fixtures.merge(
        teams,
        left_on="team_a",
        right_on="team_id",
        how="left"
    ).rename(columns={"name": "away_team"})

    fixtures = fixtures[[
        "id", "event", "home_team", "away_team"
    ]].rename(columns={
        "id": "fixture_id",
        "event": "gameweek"
    })

    fixtures.to_csv("data/fixtures.csv", index=False)

    print("\nFixtures sample:")
    print(fixtures.head())
    
    GW = 32

    gw_fixtures = fixtures[fixtures["gameweek"] == GW].copy()

    print("\nGW32 Fixtures:")
    print(gw_fixtures)

    # home players
    home = gw_fixtures[["home_team", "away_team"]].copy()
    home["team_name"] = home["home_team"]
    home["opponent"] = home["away_team"]
    home["is_home"] = 1

    # away players
    away = gw_fixtures[["home_team", "away_team"]].copy()
    away["team_name"] = away["away_team"]
    away["opponent"] = away["home_team"]
    away["is_home"] = 0

    team_mapping = pd.concat([home, away])[["team_name", "opponent", "is_home"]]

    players_gw = players.merge(team_mapping, on="team_name", how="inner")

    players_gw.to_csv("data/players_gw32.csv", index=False)

    print("\nGW32 player sample:")
    print(players_gw.head())

if __name__ == "__main__":
    main()