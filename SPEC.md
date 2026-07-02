# FPL Projection Tool — Build Spec

## Project context

A Fantasy Premier League points-projection tool built on two independent models:
a betting-market model (odds → implied probabilities → xPts) and a stats model
(Opta-derived/Understat data → xPts). Long-term, a third layer explains
_divergences_ between the two — the thesis is that the human's job in FPL is
reconciling what the market knows that the stats don't (injuries, tactical
changes, manager news). Eventually this becomes a tool anyone can use for
transfer/chip decisions, with a public track record of projections vs outcomes.

## Why this shapes your decisions

- Both models MUST share the same output decomposition (start_prob, goal_prob,
  assist_prob, cs_prob, xPts) — the divergence layer diffs them component-wise.
- Prefer interpretable features over marginal accuracy — divergences must be
  explainable to a human.
- This build is layers 1–2 plus evaluation. The divergence layer comes later,
  but don't paint it into a corner.

## Architecture (three layers, build in this order)

1. Data layer: fetchers (FPL API, Understat, vaastav historical) → local parquet/CSV
2. Model layer: odds-based xPts + stats-based xPts, SAME decomposition:
   both output per-player {start_prob, goal_prob, assist_prob, cs_prob, xPts}
3. Eval layer: backtest.py, walk-forward by GW, metric = mean within-GW Spearman
   (divergence-explanation layer: NOT in scope for this build)

## Decisions already made — do not revisit

- Vig stripping: proportional normalization
- Name matching: team + fuzzy token match (rapidfuzz), never surname-only
- CS prob: from odds fetch, no hardcoded values anywhere
- Minutes model: rolling FPL minutes history → start probability
- Splits: train 2016–2023, holdout 2024–25, defined in eval/splits.json
- No deep learning. sklearn/lightgbm ceiling.

## Definition of done (per phase — verify before moving on)

- Phase 1: `make fetch-historical` produces data/ with row counts logged
- Phase 2: both models produce projections for any historical GW via one CLI command
- Phase 3: `python eval/backtest.py` prints holdout Spearman for both models
- Every phase: pytest passes, README updated

## Anti-lookahead rule (critical)

All rolling features use ONLY data from GWs strictly before the target GW.
Write a test that proves this.
