"""Walk-forward backtest.

    python eval/backtest.py [--split sealed|dev] [--model both|stats|odds]
                            [--by-position]

Splits (defined in eval/splits.json):
- sealed (default): the 2024-25 holdout, training on 2016-17..2023-24.
  Reserved for final evaluation — the autonomous loop must never run it.
- dev: walk-forward over all GWs of 2023-24, training on seasons strictly
  before 2023-24. The loop's ratchet split.

For every eval GW, models project xPts using only information from strictly
earlier GWs (the feature layer guarantees this; the stats model is fitted
once on the split's train seasons and never sees eval-season data). Metric =
Spearman rank correlation between projected xPts and actual FPL points
within each GW, averaged across GWs.

HEADLINE METRIC: the RESTRICTED population (players with minutes > 0).
The all-players number is inflated by correctly ranking permanent
bench-sitters last, so improvements are judged on restricted only.

This file is part of the frozen eval layer: the autonomous loop must never
modify it (enforced by tests/test_eval_integrity.py).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from scipy.stats import spearmanr

from src.data.paths import GW_HISTORY_PARQUET, PROJECT_ROOT
from model.features import build_features
from model import odds_model
from model.common import load_splits
from model.stats_model import StatsModel

# Per-GW output CSVs go here, NOT under eval/ (eval/ and data/ are read-only
# under `make lockdown`).
RUNS_DIR = PROJECT_ROOT / "runs"

MODEL_CHOICES = ["both", "stats", "odds"]
SPLIT_CHOICES = ["sealed", "dev"]


def split_config(split: str) -> dict:
    return load_splits()["splits"][split]


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
        "spearman_restricted": spearmanr(
            played["xpts"], played["actual_points"]).statistic,
        "n_players": len(merged),
    }


def within_gw_spearman_by_position(
    projection: pd.DataFrame, actual: pd.DataFrame
) -> list[dict]:
    """All + restricted Spearman per position within one GW."""
    merged = projection.merge(actual, on=["season", "gw", "element"], how="inner")
    rows = []
    for position, group in merged.groupby("position"):
        played = group[group["actual_minutes"] > 0]
        rows.append({
            "position": position,
            "spearman_all": spearmanr(
                group["xpts"], group["actual_points"]).statistic,
            "spearman_restricted": spearmanr(
                played["xpts"], played["actual_points"]).statistic,
        })
    return rows


def projections_for_gw(
    features: pd.DataFrame,
    season: str,
    gw: int,
    model: str,
    stats: StatsModel | None,
) -> dict[str, pd.DataFrame]:
    out = {}
    if model in ("odds", "both"):
        out["odds"] = odds_model.project(features, season, gw)
    if model in ("stats", "both"):
        out["stats"] = stats.project(features, season, gw)
    return out


def backtest(
    split: str = "sealed",
    model: str = "both",
    by_position: bool = False,
    features: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Returns (per-GW results, per-GW-per-position results or None)."""
    cfg = split_config(split)
    if features is None:
        features = build_features()
    actual = actual_gw_points(pd.read_parquet(GW_HISTORY_PARQUET))

    stats = None
    if model in ("stats", "both"):
        stats = StatsModel().fit(features, cfg["train_seasons"])

    rows, position_rows = [], []
    for season in cfg["eval_seasons"]:
        gws = sorted(features.loc[features["season"] == season, "gw"].unique())
        for gw in gws:
            for model_name, proj in projections_for_gw(
                features, season, gw, model, stats
            ).items():
                rows.append({
                    "season": season, "gw": gw, "model": model_name,
                    **within_gw_spearman(proj, actual),
                })
                if by_position:
                    for pos_row in within_gw_spearman_by_position(proj, actual):
                        position_rows.append({
                            "season": season, "gw": gw, "model": model_name,
                            **pos_row,
                        })
    return (
        pd.DataFrame(rows),
        pd.DataFrame(position_rows) if by_position else None,
    )


def print_summary(results: pd.DataFrame, split: str,
                  position_results: pd.DataFrame | None = None):
    cfg = split_config(split)
    print(f"\n=== backtest — split: {split} "
          f"(eval {', '.join(cfg['eval_seasons'])}; "
          f"train <= {max(cfg['train_seasons'])}) ===")
    print("metric: mean within-GW Spearman, xPts vs actual FPL points\n")

    summary = results.groupby("model").agg(
        restricted=("spearman_restricted", "mean"),
        all_players=("spearman_all", "mean"),
        gws=("gw", "count"),
    )
    print("HEADLINE = restricted population (players with minutes > 0):")
    for model_name, row in summary.iterrows():
        print(f"  {model_name:<6} restricted={row['restricted']:.4f} (HEADLINE)   "
              f"all-players={row['all_players']:.4f}   "
              f"[{int(row['gws'])} GWs]")

    if position_results is not None:
        print("\nper-position breakdown (mean within-GW Spearman):")
        pivot = position_results.groupby(["model", "position"]).agg(
            restricted=("spearman_restricted", "mean"),
            all_players=("spearman_all", "mean"),
        )
        print(pivot.to_string(float_format=lambda x: f"{x:.4f}"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=SPLIT_CHOICES, default="sealed")
    parser.add_argument("--model", choices=MODEL_CHOICES, default="both")
    parser.add_argument("--by-position", action="store_true",
                        help="also print per-position Spearman")
    args = parser.parse_args()

    results, position_results = backtest(
        split=args.split, model=args.model, by_position=args.by_position)
    print_summary(results, args.split, position_results)

    RUNS_DIR.mkdir(exist_ok=True)
    out_path = RUNS_DIR / f"backtest_{args.split}.csv"
    results.to_csv(out_path, index=False)
    print(f"\nper-GW results -> {out_path}")


if __name__ == "__main__":
    main()
