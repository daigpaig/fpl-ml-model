"""Walk-forward backtest over the holdout season(s).

    python eval/backtest.py

For every holdout GW, both models project xPts using only information from
strictly earlier GWs (the feature layer guarantees this; the stats model is
fitted once on the train seasons and never sees holdout data). Metric =
Spearman rank correlation between projected xPts and actual FPL points
within each GW, averaged across GWs.

Reported over two populations:
- all players with a fixture that GW (what a user of the tool sees), and
- only players who actually played (removes the easy wins from correctly
  ranking permanent bench-sitters last).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from scipy.stats import spearmanr

from src.data.paths import GW_HISTORY_PARQUET
from src.features.build import build_features
from src.models import odds_model
from src.models.common import load_splits
from src.models.stats_model import StatsModel


def actual_gw_points(gw_history: pd.DataFrame) -> pd.DataFrame:
    """Per (season, gw, element): actual FPL points and minutes."""
    return gw_history.groupby(
        ["season", "gw", "element"], as_index=False
    ).agg(actual_points=("total_points", "sum"), actual_minutes=("minutes", "sum"))


def within_gw_spearman(projection: pd.DataFrame, actual: pd.DataFrame) -> dict:
    merged = projection.merge(actual, on=["season", "gw", "element"], how="inner")
    played = merged[merged["actual_minutes"] > 0]
    return {
        "spearman_all": spearmanr(merged["xpts"], merged["actual_points"]).statistic,
        "spearman_played": spearmanr(
            played["xpts"], played["actual_points"]).statistic,
        "n_players": len(merged),
    }


def backtest() -> pd.DataFrame:
    features = build_features()
    actual = actual_gw_points(pd.read_parquet(GW_HISTORY_PARQUET))
    splits = load_splits()

    stats = StatsModel().fit(features, splits["train_seasons"])

    rows = []
    for season in splits["holdout_seasons"]:
        gws = sorted(features.loc[features["season"] == season, "gw"].unique())
        for gw in gws:
            projections = {
                "odds": odds_model.project(features, season, gw),
                "stats": stats.project(features, season, gw),
            }
            for model_name, proj in projections.items():
                rows.append({
                    "season": season, "gw": gw, "model": model_name,
                    **within_gw_spearman(proj, actual),
                })
    return pd.DataFrame(rows)


def main():
    results = backtest()

    print("\n=== Holdout backtest: mean within-GW Spearman (xPts vs actual points) ===")
    summary = results.groupby("model").agg(
        spearman_all=("spearman_all", "mean"),
        spearman_played=("spearman_played", "mean"),
        gws=("gw", "count"),
    )
    print(summary.to_string(float_format=lambda x: f"{x:.4f}"))

    out_path = Path(__file__).parent / "backtest_results.csv"
    results.to_csv(out_path, index=False)
    print(f"\nper-GW results -> {out_path}")


if __name__ == "__main__":
    main()
