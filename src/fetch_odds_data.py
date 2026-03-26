import requests
import pandas as pd
import os
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

    for bookmaker in event_data.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market["key"] != "player_goal_scorer_anytime":
                continue

            for outcome in market.get("outcomes", []):
                player_name = outcome.get("description")
                odds = outcome.get("price")

                if player_name is None or odds is None:
                    continue

                rows.append({
                    "player_name": player_name,
                    "home_team": event_data["home_team"],
                    "away_team": event_data["away_team"],
                    "bookmaker": bookmaker["title"],
                    "goal_odds": odds
                })

    return pd.DataFrame(rows)


def collapse_goal_odds(goal_df):
    if goal_df.empty:
        return goal_df

    goal_df = (
        goal_df.groupby(["player_name", "home_team", "away_team"], as_index=False)
        .agg({"goal_odds": "mean"})
    )

    goal_df["goal_prob"] = 1 / goal_df["goal_odds"]
    return goal_df


def extract_clean_sheets(event_data):
    rows = []

    home_team = event_data["home_team"]
    away_team = event_data["away_team"]

    for bookmaker in event_data.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market["key"] != "team_totals":
                continue

            for outcome in market.get("outcomes", []):
                if outcome.get("name") == "Under" and outcome.get("point") == 0.5:
                    team_that_scores_zero = outcome.get("description")
                    odds = outcome.get("price")

                    if team_that_scores_zero is None or odds is None:
                        continue

                    # if home team scores 0, away team gets clean sheet
                    if team_that_scores_zero == home_team:
                        clean_sheet_team = away_team
                    elif team_that_scores_zero == away_team:
                        clean_sheet_team = home_team
                    else:
                        continue

                    rows.append({
                        "team_name": clean_sheet_team,
                        "bookmaker": bookmaker["title"],
                        "clean_sheet_odds": odds
                    })

    return pd.DataFrame(rows)


def collapse_clean_sheet_odds(cs_df):
    if cs_df.empty:
        return cs_df

    cs_df = (
        cs_df.groupby(["team_name"], as_index=False)
        .agg({"clean_sheet_odds": "mean"})
    )

    cs_df["clean_sheet_prob"] = 1 / cs_df["clean_sheet_odds"]
    return cs_df


def main():
    event_id = "10d3a3a8df4f15a0754da8195a47c41f"

    goal_event_data = fetch_event_odds(event_id, "player_goal_scorer_anytime")
    cs_event_data = fetch_event_odds(event_id, "team_totals")

    goal_raw = extract_goal_odds(goal_event_data)
    goal_final = collapse_goal_odds(goal_raw)

    cs_raw = extract_clean_sheets(cs_event_data)
    cs_final = collapse_clean_sheet_odds(cs_raw)

    os.makedirs("data", exist_ok=True)

    goal_raw.to_csv("data/test_goal_odds_raw.csv", index=False)
    goal_final.to_csv("data/test_goal_odds.csv", index=False)
    cs_raw.to_csv("data/test_clean_sheet_odds_raw.csv", index=False)
    cs_final.to_csv("data/test_clean_sheet_odds.csv", index=False)

    print("\nGoal odds:")
    print(goal_final.head(10))

    print("\nClean sheet odds:")
    print(cs_final.head(10))


if __name__ == "__main__":
    main()