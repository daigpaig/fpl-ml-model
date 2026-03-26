import pandas as pd


def main():
    players = pd.read_csv("data/players_gw32.csv")
    odds = pd.read_csv("data/test_goal_odds.csv")

    players["name_key"] = players["player_name"].str.lower()
    odds["name_key"] = odds["player_name"].str.lower().str.split().str[-1]

    odds = odds.rename(columns={"player_name": "odds_player_name"})

    merged = players.merge(odds, on="name_key", how="inner")

    print(merged[[
        "player_name", "odds_player_name", "team_name", "opponent", "goal_prob"
    ]].head(20))

    print("\nMatched players:", len(merged))

    merged.to_csv("data/merged_gw32.csv", index=False)

    print("\nTotal FPL players:", len(odds))
    print("Matched players:", len(merged)) 

if __name__ == "__main__":
    main()