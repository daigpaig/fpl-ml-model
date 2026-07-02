"""Naive baseline + comparison table.

    python eval/baselines.py        (= make baselines)

Baseline: predicted xPts = the player's mean FPL points over their previous
5 APPEARANCES (GWs with minutes > 0), using only GWs strictly before the
target GW. Players with no prior appearances get 0.

Deliberately self-contained: computes its own rolling numbers from
gw_history.parquet and does NOT import from model/, so autonomous-loop
experiments can never move the baseline.

This file is part of the frozen eval layer: the autonomous loop must never
modify it (enforced by tests/test_eval_integrity.py).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from src.data.paths import GW_HISTORY_PARQUET, SEASONS
from backtest import (  # noqa: E402  (eval/ is on sys.path when run as script)
    actual_gw_points,
    split_config,
    within_gw_spearman,
)

BASELINE_WINDOW = 5


def last5_projection(gw_history: pd.DataFrame) -> pd.DataFrame:
    """Per (season, gw, element): mean points over the previous 5 appearances.

    Anti-lookahead: appearances are aggregated per GW first (a double-GW's
    second fixture can't see its first), and the value attached to a GW uses
    only appearances from strictly earlier GWs. Cross-season identity =
    (player_name, position), as in the model feature layer.
    """
    season_order = {s: i for i, s in enumerate(SEASONS)}
    df = gw_history.copy()
    df["player_key"] = df["player_name"] + "|" + df["position"]
    df["gw_order"] = df["season"].map(season_order) * 100 + df["gw"]

    per_gw = df.groupby(
        ["player_key", "season", "gw", "gw_order", "element"], as_index=False
    ).agg(points=("total_points", "sum"), minutes=("minutes", "sum"))
    per_gw = per_gw.sort_values(["player_key", "gw_order"]).reset_index(drop=True)
    played = per_gw["minutes"] > 0

    # Appearance-only rows: rolling means over the last 5 appearances,
    # both excluding the current appearance (value AT an appearance GW)
    # and including it (value carried forward to later non-appearance GWs).
    appearances = per_gw[played]
    grouped = appearances.groupby("player_key", sort=False)["points"]
    incl = (
        grouped.rolling(BASELINE_WINDOW, min_periods=1).mean()
        .reset_index(level=0, drop=True)
    )
    excl = (
        grouped.shift(1)
        .groupby(appearances["player_key"], sort=False)
        .rolling(BASELINE_WINDOW, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )

    # At an appearance GW: mean of the 5 appearances strictly before it.
    # At a non-appearance GW: carry forward the mean of the last 5
    # appearances completed before it (ffill of the inclusive value; the
    # current row is NaN there, so ffill only ever pulls from earlier GWs).
    per_gw["incl_at_appearance"] = incl
    carried = per_gw.groupby("player_key", sort=False)["incl_at_appearance"].ffill()
    per_gw["xpts"] = np.where(played, excl.reindex(per_gw.index), carried)
    per_gw["xpts"] = per_gw["xpts"].fillna(0.0)

    return per_gw[["season", "gw", "element", "xpts"]]


def evaluate_baseline(gw_history: pd.DataFrame, split: str) -> dict:
    """Mean within-GW Spearman of the last-5 baseline on one split."""
    cfg = split_config(split)
    projection = last5_projection(gw_history)
    actual = actual_gw_points(gw_history)

    rows = []
    for season in cfg["eval_seasons"]:
        season_proj = projection[projection["season"] == season]
        for gw in sorted(season_proj["gw"].unique()):
            gw_proj = season_proj[season_proj["gw"] == gw]
            rows.append(within_gw_spearman(gw_proj, actual))
    results = pd.DataFrame(rows)
    return {
        "spearman_restricted": results["spearman_restricted"].mean(),
        "spearman_all": results["spearman_all"].mean(),
    }


def baseline_table() -> pd.DataFrame:
    """last-5 baseline vs stats vs odds on dev and sealed."""
    from backtest import backtest  # deferred: heavy imports

    gw_history = pd.read_parquet(GW_HISTORY_PARQUET)
    rows = []
    for split in ("dev", "sealed"):
        base = evaluate_baseline(gw_history, split)
        rows.append({"split": split, "model": "last5", **base})

        model_results, _ = backtest(split=split, model="both")
        for model_name, group in model_results.groupby("model"):
            rows.append({
                "split": split,
                "model": model_name,
                "spearman_restricted": group["spearman_restricted"].mean(),
                "spearman_all": group["spearman_all"].mean(),
            })
    table = pd.DataFrame(rows)
    order = {"last5": 0, "stats": 1, "odds": 2}
    return table.sort_values(
        ["split", "model"], key=lambda s: s.map(order).fillna(s)
    ).reset_index(drop=True)


def main():
    table = baseline_table()
    print("\n=== baselines — mean within-GW Spearman "
          "(restricted = minutes > 0 = HEADLINE) ===")
    pivot = table.pivot(index="model", columns="split",
                        values=["spearman_restricted", "spearman_all"])
    pivot = pivot.reindex(["last5", "stats", "odds"])
    print(pivot.to_string(float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    main()
