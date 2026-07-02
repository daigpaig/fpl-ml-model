"""Produce projections for any historical GW from both models.

    python -m src.project --season 2024-25 --gw 20            # both models
    python -m src.project --season 2024-25 --gw 20 --model odds
    python -m src.project --season 2024-25 --gw 20 --out proj.csv

Prints the top of each model's table; --out writes the full merged
decomposition (one row per player-GW-model) to CSV.
"""

import argparse

import pandas as pd

from model.features import build_features
from model import odds_model
from model.stats_model import StatsModel


def run(season: str, gw: int, model: str) -> pd.DataFrame:
    features = build_features()

    frames = []
    if model in ("odds", "both"):
        odds_proj = odds_model.project(features, season, gw)
        odds_proj["model"] = "odds"
        frames.append(odds_proj)
    if model in ("stats", "both"):
        stats = StatsModel().fit(features)
        stats_proj = stats.project(features, season, gw)
        stats_proj["model"] = "stats"
        frames.append(stats_proj)
    return pd.concat(frames, ignore_index=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", required=True, help="e.g. 2024-25")
    parser.add_argument("--gw", type=int, required=True)
    parser.add_argument("--model", choices=["odds", "stats", "both"],
                        default="both")
    parser.add_argument("--out", help="write full projections CSV here")
    parser.add_argument("--top", type=int, default=15,
                        help="rows to print per model")
    args = parser.parse_args()

    projections = run(args.season, args.gw, args.model)

    pd.set_option("display.width", 140)
    for model_name, table in projections.groupby("model"):
        print(f"\n=== {model_name} model — {args.season} GW{args.gw} "
              f"(top {args.top} by xPts) ===")
        print(
            table.drop(columns=["model", "season", "gw", "element"])
            .head(args.top)
            .to_string(index=False, float_format=lambda x: f"{x:.3f}")
        )

    if args.out:
        projections.to_csv(args.out, index=False)
        print(f"\nwrote {len(projections)} rows -> {args.out}")


if __name__ == "__main__":
    main()
