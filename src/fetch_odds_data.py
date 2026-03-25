# import requests
# import pandas as pd
# import os
# from dotenv import load_dotenv

# load_dotenv()

# API_KEY = os.getenv("ODDS_API_KEY")

# SPORT = "soccer_epl"
# MARKETS = "player_goal_scorer_anytime"
# REGIONS = "us"

# URL = "https://api.the-odds-api.com/v4/sports/{SPORT}/odds/"

# def fetch_odds():
#     params = {
#         "apiKey": API_KEY,
#         "regions": REGIONS,
#         "markets": MARKETS,
#         "oddsFormat": "decimal"
#     }

#     response = requests.get(URL.format(sport=SPORT), params=params)
#     response.raise_for_status()
#     return response.json()

# def main():
#     data = fetch_odds()

#     print("Number of matches:", len(data))

#     # just inspect first match for now
#     import json
#     print(json.dumps(data[0], indent=2)[:2000])

# if __name__ == "__main__":
#     main()

import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ODDS_API_KEY")
SPORT = "soccer_epl"


def get_epl_events():
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"

    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }

    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()

    print("matches:", len(data))
    print(data[0]["id"])
    print(data[0]["home_team"], "vs", data[0]["away_team"])
    print(data)

def fetch_player_props():
    event_id = "10d3a3a8df4f15a0754da8195a47c41f"

    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events/{event_id}/odds/"

    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "player_goal_scorer_anytime",
        "oddsFormat": "decimal"
    }

    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()

    import json
    print(json.dumps(data, indent=2)[:3000])

if __name__ == "__main__":
    fetch_player_props()