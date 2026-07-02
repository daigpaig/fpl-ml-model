import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ODDS_API_KEY")
SPORT = "soccer_epl"


def fetch_event_odds(event_id, market):
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events/{event_id}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": market,
        "oddsFormat": "decimal"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def extract_goal_odds(event_data):
    rows = []

    home_team = event_data["home_team"]
    away_team = event_data["away_team"]

    for bookmaker in event_data.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market["key"] != "player_goal_scorer_anytime":
                continue

            for outcome in market.get("outcomes", []):
                player_name = outcome.get("description")
                goal_odds = outcome.get("price")

                if player_name is None or goal_odds is None:
                    continue

                rows.append({
                    "player_name_odds": player_name,
                    "home_team": home_team,
                    "away_team": away_team,
                    "bookmaker": bookmaker["title"],
                    "goal_odds": goal_odds
                })

    return pd.DataFrame(rows)


def collapse_goal_odds(goal_df):
    if goal_df.empty:
        return goal_df

    goal_df = (
        goal_df.groupby(
            ["player_name_odds", "home_team", "away_team"],
            as_index=False
        )
        .agg({"goal_odds": "mean"})
    )

    goal_df["goal_prob"] = 1 / goal_df["goal_odds"]
    return goal_df


def extract_clean_sheet_odds(event_data):
    rows = []

    home_team = event_data["home_team"]
    away_team = event_data["away_team"]

    found_team_totals = False

    for bookmaker in event_data.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market["key"] != "alternate_team_totals":
                continue

            found_team_totals = True

            for outcome in market.get("outcomes", []):
                if outcome.get("name") != "Under" or outcome.get("point") != 0.5:
                    continue

                team_that_scores_zero = outcome.get("description")
                clean_sheet_odds = outcome.get("price")

                if team_that_scores_zero is None or clean_sheet_odds is None:
                    continue

                if team_that_scores_zero == home_team:
                    clean_sheet_team = away_team
                    opponent = home_team
                elif team_that_scores_zero == away_team:
                    clean_sheet_team = home_team
                    opponent = away_team
                else:
                    continue

                rows.append({
                    "team_name": clean_sheet_team,
                    "opponent": opponent,
                    "bookmaker": bookmaker["title"],
                    "clean_sheet_odds": clean_sheet_odds,
                    "source": "alternate_team_totals"
                })

    if rows:
        return pd.DataFrame(rows)

    # fallback: BTTS No
    for bookmaker in event_data.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market["key"] != "btts":
                continue

            for outcome in market.get("outcomes", []):
                if outcome.get("name") != "No":
                    continue

                odds = outcome.get("price")
                if odds is None:
                    continue

                # crude fallback: assign same CS prob to both teams
                rows.append({
                    "team_name": home_team,
                    "opponent": away_team,
                    "bookmaker": bookmaker["title"],
                    "clean_sheet_odds": odds,
                    "source": "btts_fallback"
                })
                rows.append({
                    "team_name": away_team,
                    "opponent": home_team,
                    "bookmaker": bookmaker["title"],
                    "clean_sheet_odds": odds,
                    "source": "btts_fallback"
                })

    return pd.DataFrame(rows)


def collapse_clean_sheet_odds(cs_df):
    if cs_df.empty:
        return pd.DataFrame(columns=[
            "team_name", "opponent", "clean_sheet_odds",
            "clean_sheet_prob", "source"
        ])

    cs_df = (
        cs_df.groupby(["team_name", "opponent"], as_index=False)
        .agg({
            "clean_sheet_odds": "mean",
            "source": "first"
        })
    )

    cs_df["clean_sheet_prob"] = 1 / cs_df["clean_sheet_odds"]
    return cs_df


def build_name_key(series):
    return (
        series.str.lower()
        .str.strip()
        .str.replace(r"[^a-z\s]", "", regex=True)
        .str.split()
        .str[-1]
    )


def attach_team_info_to_goal_odds(goal_df, players_gw):
    if goal_df.empty:
        return goal_df

    players = players_gw.copy()

    players["name_key"] = build_name_key(players["player_name"])
    goal_df["name_key"] = build_name_key(goal_df["player_name_odds"])

    goal_df = goal_df.merge(
        players[["player_name", "team_name", "opponent", "position", "name_key"]],
        on="name_key",
        how="left"
    )

    goal_df = goal_df[[
        "player_name",
        "player_name_odds",
        "team_name",
        "opponent",
        "position",
        "goal_odds",
        "goal_prob"
    ]]

    return goal_df


def build_final_odds_table(event_id, players_gw_path):
    players_gw = pd.read_csv(players_gw_path)

    goal_event_data = fetch_event_odds(event_id, "player_goal_scorer_anytime")
    cs_event_data = fetch_event_odds(event_id, "team_totals")

    goal_raw = extract_goal_odds(goal_event_data)
    goal_final = collapse_goal_odds(goal_raw)
    goal_final = attach_team_info_to_goal_odds(goal_final, players_gw)

    cs_raw = extract_clean_sheet_odds(cs_event_data)
    cs_final = collapse_clean_sheet_odds(cs_raw)

    odds_final = goal_final.merge(
        cs_final[["team_name", "opponent", "clean_sheet_prob"]],
        on=["team_name", "opponent"],
        how="left"
    )

    return goal_raw, goal_final, cs_raw, cs_final, odds_final


def main():
    event_id = "10d3a3a8df4f15a0754da8195a47c41f"
    players_gw_path = "data/players_gw32.csv"

    goal_raw, goal_final, cs_raw, cs_final, odds_final = build_final_odds_table(
        event_id=event_id,
        players_gw_path=players_gw_path
    )

    os.makedirs("data", exist_ok=True)

    goal_raw.to_csv("data/test_goal_odds_raw.csv", index=False)
    goal_final.to_csv("data/test_goal_odds.csv", index=False)
    cs_raw.to_csv("data/test_clean_sheet_odds_raw.csv", index=False)
    cs_final.to_csv("data/test_clean_sheet_odds.csv", index=False)
    odds_final.to_csv("data/test_odds_final.csv", index=False)

    print("\nFinal merged odds table:")
    print(odds_final.head(20))

    print("\nSaved:")
    print("- data/test_goal_odds_raw.csv")
    print("- data/test_goal_odds.csv")
    print("- data/test_clean_sheet_odds_raw.csv")
    print("- data/test_clean_sheet_odds.csv")
    print("- data/test_odds_final.csv")


if __name__ == "__main__":
    main()