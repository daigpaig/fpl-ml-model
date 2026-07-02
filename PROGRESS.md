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

## Next

### Phase 2 — Model layer

- Odds-based xPts model (absorb/replace legacy `src/fetch_odds_data.py` MVP):
  vig stripping via proportional normalization, name matching via
  team + rapidfuzz token match.
- Stats-based xPts model: minutes model from rolling FPL minutes history,
  goal/assist probs from Understat-derived features. No lookahead — rolling
  features use only GWs strictly before target, with a test proving it.
- Both emit per-player {start_prob, goal_prob, assist_prob, cs_prob, xPts}
  for any historical GW via one CLI command.

### Phase 3 — Eval layer

- `eval/splits.json` (train 2016-2023, holdout 2024-25).
- `eval/backtest.py` walk-forward by GW, prints holdout mean within-GW
  Spearman for both models.

## Blockers

- None. Note: historical odds for past GWs are not available from the current
  Odds API setup — Phase 2 odds model will project any GW where odds data
  exists; backtesting the odds model may be limited to GWs with captured odds
  (to be resolved in Phase 2/3).
