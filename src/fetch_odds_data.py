import requests
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ODDS_API_KEY")
SPORT = "soccer_epl"


def fetch_event_goal_scorer_odds(event_id):
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events/{event_id}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "player_goal_scorer_anytime",
        "oddsFormat": "decimal"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def extract_goal_odds(event_data):
    rows = []

    event_id = event_data["id"]
    home_team = event_data["home_team"]
    away_team = event_data["away_team"]

    for bookmaker in event_data.get("bookmakers", []):
        book_name = bookmaker["title"]

        for market in bookmaker.get("markets", []):
            if market["key"] != "player_goal_scorer_anytime":
                continue

            for outcome in market.get("outcomes", []):
                player_name = outcome.get("description")
                odds = outcome.get("price")

                if player_name is None or odds is None:
                    continue

                rows.append({
                    "event_id": event_id,
                    "home_team": home_team,
                    "away_team": away_team,
                    "bookmaker": book_name,
                    "player_name": player_name,
                    "goal_odds": odds,
                    "goal_prob_raw": 1 / odds
                })

    return pd.DataFrame(rows)


def main():
    event_id = "10d3a3a8df4f15a0754da8195a47c41f"  # WHU vs WOL test
    event_data = fetch_event_goal_scorer_odds(event_id)
    df = extract_goal_odds(event_data)

    print(df.head(20))

    os.makedirs("data", exist_ok=True)
    df.to_csv("data/test_goal_odds.csv", index=False)
    print("\nSaved to data/test_goal_odds.csv")


if __name__ == "__main__":
    main()