# Progress

## Done

### Phase 1 — Data layer ✅ (2026-07-02)

- `make fetch-historical` fetches and caches all three sources, logs row
  counts, writes processed parquets:
  - vaastav per-GW history 2016-17 → 2024-25 → `gw_history.parquet`
    (223,821 player-GW rows, canonical schema)
  - Understat league data → `understat_players.parquet` (4,806 rows),
    `understat_team_matches.parquet` (6,840 rows)
  - FPL API snapshot → `fpl_players.parquet` (841), `fpl_fixtures.parquet` (380)
- Fetch-once/cache-to-disk enforced via `src/data/http_cache.py`; re-runs are
  offline.
- Fixed: 2024-25 opponent team names were all NaN (master_team_list.csv stops
  at 2023-24) — now falls back to per-season `teams.csv`.
- 15 data-shape tests in `tests/test_data_shapes.py`, all passing
  (`make test`).
- README rewritten around the spec architecture.

### Phase 2 — Model layer ✅ (2026-07-02)

- Historical odds sourced from football-data.co.uk (1X2 + O/U 2.5, all nine
  seasons) → `match_odds.parquet`; canonical team names across all sources.
- Leak-free rolling feature layer (`src/features/build.py`) with an
  anti-lookahead proof test (`tests/test_no_lookahead.py`).
- Odds model: vig strip (proportional) → implied Poisson team lambdas →
  player probs via trailing goal/assist share.
- Stats model: logistic regressions (goal, assist, clean sheet) on named
  rolling features, trained on `eval/splits.json` train seasons.
- Shared decomposition + xPts in `src/models/common.py`; shared minutes
  model (start_prob from trailing 60+-minute rate).
- One CLI for any historical GW:
  `python -m src.project --season 2024-25 --gw 20 [--model odds|stats|both]`
- Fixed pre-2020-21 mid-season-transfer team assignment (derived from
  fixture pairing).
- 28 tests passing.

## Next

### Phase 3 — Eval layer

- `eval/backtest.py`: walk-forward by GW over the 2024-25 holdout, prints
  mean within-GW Spearman (projection xPts vs actual total_points) for both
  models. `eval/splits.json` already exists.

## Blockers

- None.

## Notes

- GW1 of 2016-17 projects all-zero (no prior history exists at the dataset
  boundary) — harmless, it's in train, not holdout.
- Legacy MVP scripts (`src/fetch_fpl_data.py`, `src/fetch_odds_data.py`,
  `src/merge_tables.py`, `src/build_model.py`) still present; the live
  player-prop odds path can later replace the share-allocation step for
  current GWs.
