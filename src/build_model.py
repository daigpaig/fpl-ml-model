import pandas as pd

players = pd.read_csv("data/merged_gw32.csv")

GOAL_POINTS = {
    "GKP": 10,
    "DEF": 6,
    "MID": 5,
    "FWD": 4
}

CLEAN_SHEET_POINTS = {
    "GKP": 4,
    "DEF": 4,
    "MID": 1,
    "FWD": 0
}

# MVP assumptions
players["appearance_points"] = 2
players["clean_sheet_prob"] = 0.30   # placeholder for now

players["goal_points"] = players.apply(
    lambda row: GOAL_POINTS[row["position"]] * row["goal_prob"],
    axis=1
)

players["clean_sheet_points"] = players.apply(
    lambda row: CLEAN_SHEET_POINTS[row["position"]] * row["clean_sheet_prob"],
    axis=1
)

players["expected_points"] = (
    players["appearance_points"]
    + players["goal_points"]
    + players["clean_sheet_points"]
)

players = players.sort_values("expected_points", ascending=False)

print(players[[
    "player_name", "team_name", "position", "opponent",
    "goal_prob", "expected_points"
]].head(20))

players.to_csv("data/player_projections_gw32.csv", index=False)