# FPL Projection Tool

A Fantasy Premier League points-projection tool built on two independent models:

1. **Betting-market model** — bookmaker odds → implied probabilities → expected points
2. **Stats model** — Understat/FPL historical data → expected points

Both models share the same output decomposition per player —
`{start_prob, goal_prob, assist_prob, cs_prob, xPts}` — so a future divergence
layer can diff them component-wise and explain *why* the market disagrees with
the stats (injuries, tactics, manager news). See `SPEC.md` for the full build
spec and `PROGRESS.md` for current status.

## Setup

```bash
python -m venv venv
venv/bin/pip install -r requirements.txt
```

## Phase 1 — Data layer (done)

```bash
make fetch-historical   # fetch + cache all historical data, build parquets
make test               # pytest (data-shape tests)
```

`fetch-historical` pulls three sources, caches every raw response under
`data/raw/` (re-runs never touch the network unless `--force`), and writes
processed tables to `data/processed/`:

| Source | Raw cache | Processed output |
|---|---|---|
| [vaastav/Fantasy-Premier-League](https://github.com/vaastav/Fantasy-Premier-League) per-GW history, 2016-17 → 2024-25 | `data/raw/vaastav/` | `gw_history.parquet` (~224k player-GW rows, canonical schema across all seasons) |
| Understat EPL (league JSON endpoint) | `data/raw/understat/` | `understat_players.parquet` (season player xG/xA aggregates), `understat_team_matches.parquet` (per-team per-match xG, date-stamped) |
| Official FPL API (bootstrap-static + fixtures) | `data/raw/fpl_api/` | `fpl_players.parquet`, `fpl_fixtures.parquet` |

Season-to-season schema quirks (name formats, missing position/team columns
pre-2020-21, encodings, COVID GW renumbering in 2019-20, assistant-manager
rows in 2024-25) are normalized in `src/data/fetch_vaastav.py`.

## Phase 2 — Models (next)

Odds-based xPts and stats-based xPts, both emitting the shared decomposition
for any historical GW via one CLI command.

## Phase 3 — Evaluation

`eval/backtest.py`: walk-forward by GW, metric = mean within-GW Spearman on
the 2024-25 holdout (splits in `eval/splits.json`).

## Repo layout

```
src/data/            Phase 1 fetchers (vaastav, understat, FPL API) + http cache
src/fetch_historical.py   entry point for `make fetch-historical`
tests/               data-shape tests
data/raw|processed/  gitignored; rebuilt by make fetch-historical
SPEC.md              build spec (phases, decisions already made)
PROGRESS.md          what's done / what's next
DECISIONS.md         ambiguity resolutions with rationale
```

Legacy single-GW MVP scripts (`src/fetch_fpl_data.py`, `src/fetch_odds_data.py`,
`src/merge_tables.py`, `src/build_model.py`) predate the spec and will be
absorbed into the odds model in Phase 2.
