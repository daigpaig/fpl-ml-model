# Research program for the autonomous loop

Current best dev restricted Spearman (stats model): **0.3090**
(frozen model, entry 0 in results.md).

Work the directions below in priority order. One experiment = one concrete,
minimal change from one direction. If a direction's obvious moves are
exhausted or retired (two failures), move down the list.

## 1. Minutes model refinements

The current start_prob is an unweighted trailing 5-GW rate of 60+-minute
appearances (start_rate_5 in model/features.py). Candidate experiments:
- recency weighting (e.g. exponential decay over the last 5-8 GWs)
- injury-return decay: distinguish "benched" from "absent" streaks and decay
  start_prob differently after long absences
- price-change signal: FPL price moves encode expected minutes; the price
  column is already in the feature frame
- team rotation rate: teams differ in how much they rotate; a team-level
  rolling rotation feature could sharpen individual start_prob

## 2. Rolling xG/xA feature windows

Goal/assist rates currently use fixed windows (10 GW rates, 20 GW shares;
team form 10 matches). Candidate experiments:
- alternative windows: 3 / 5 / 10 GW variants, or blending short + long
- exponential decay instead of hard windows
- opponent adjustment: scale player rates by opponent defensive form
- home/away splits for player rates and team form

## 3. Points-if-played modeling

Today appearance and event probabilities are mixed in one model. Candidate:
model P(points | played) separately, then multiply by start/play probability
at the end — cleaner separation of "will he play" from "what if he plays".

## 4. LightGBM per position

Replace the single pooled logistic regressions with LightGBM classifiers
per position (GKP/DEF/MID/FWD), keeping the exact same NAMED feature set.
Per-position dynamics differ (see per-position Spearman: GKP is far worse
than MID/FWD). Small trees, few features — interpretability survives.

## 5. Probability calibration

Logistic outputs may be miscalibrated at the extremes; try isotonic or Platt
calibration on a validation slice of the TRAIN seasons (never the dev
season). Calibration changes probabilities but usually not ranks, so this
matters most for goal_prob/assist_prob interacting in the xPts formula.

## Constraints (every experiment)

- Keep the shared output decomposition {start_prob, goal_prob, assist_prob,
  cs_prob, xPts} — the divergence layer depends on it.
- Keep features named and interpretable; no anonymous embeddings.
- The anti-lookahead test (tests/test_no_lookahead.py) must always pass.
- No deep learning; sklearn/lightgbm ceiling.
- No new data sources; only data already under data/processed/.
- Only files under model/ may change (protocol: CLAUDE.loop.md).
