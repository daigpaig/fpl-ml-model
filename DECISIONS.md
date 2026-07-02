# Decisions

Ambiguity resolutions not covered by SPEC.md, with rationale. Newest last.

## Phase 1

- **Season range = 2016-17 → 2024-25.** SPEC defines train 2016-2023 and
  holdout 2024-25; fetching exactly those nine seasons covers both splits with
  no dead weight.
- **Canonical per-GW schema keeps a minimal column set** (identity, fixture
  context, the FPL scoring events, price, xP/xG/xA where available) rather
  than all ~40 vaastav columns. Models in Phase 2 need interpretable inputs;
  anything else can be added by extending `CANONICAL_COLUMNS` and re-running
  the (cached, offline) build.
- **Old columns missing in early seasons (xP pre-2020-21, expected_goals /
  expected_assists pre-2022-23) are carried as NaN** instead of dropped, so
  downstream code sees one schema and decides per-feature what to do.
- **2024-25 assistant-manager rows are dropped** — they aren't players and
  have no position.
- **Team id → name mapping: master_team_list.csv first, per-season teams.csv
  as fallback.** master_team_list is the one file that spans all seasons but
  is unmaintained past 2023-24; without the fallback every 2024-25
  opponent_team_name was NaN.
- **Understat fetched from the `getLeagueData/{league}/{year}` JSON endpoint**,
  not by scraping embedded JSON out of HTML pages — the HTML pages are now
  empty client-rendered shells.
- **Data-shape tests skip (not fail) when parquets are absent**, with a
  message pointing at `make fetch-historical`. Keeps `pytest` meaningful on a
  fresh clone without committing data.
- **GW-count expectations encode known anomalies**: 2019-20 COVID restart
  renumbered GWs up to 47; 2022-23 GW7 was postponed (37 distinct GWs).

## Phase 2

- **Historical odds source = football-data.co.uk match markets (1X2 +
  over/under 2.5), not player props.** Free historical player-prop odds don't
  exist, and Phase 3 requires the odds model to backtest on the whole
  holdout. Team goal expectations are fitted from the match markets
  (independent Poisson, minimizing squared error vs the vig-free
  probabilities) and allocated to players by their trailing share of team
  goals/assists. The live Odds API player-prop path (legacy MVP scripts) can
  replace the allocation step for current GWs later.
- **Market-average odds columns (Avg / BbAv), not a single bookmaker** —
  less idiosyncratic noise, available across all nine seasons.
- **Cross-season player identity = (player_name, position)** — vaastav
  `element` ids reset every season. Within a season, joins also include
  team_name to separate distinct players sharing a name (SPEC: team + name,
  never name-only). Known residual risk: two same-name same-position players
  would still pool cross-season history; none observed in this data.
- **Pre-2020-21 per-row team derived from the fixture pairing** (each fixture
  lists exactly two opponent ids; a row's team is the one it doesn't list) —
  players_raw's team is season-static and wrong for mid-season transfers.
- **start_prob := P(plays 60+ minutes)**, estimated as the trailing 5-GW rate
  of 60+-minute appearances (the "starts" column only exists from 2022-23).
  Both models share this minutes model — the market does not price starts.
  New players with no history get start_prob 0 until they appear.
- **Rolling windows: 5 GWs (minutes), 10 (goal/assist rates), 20 (share of
  team goals), 10 matches (team xG form).** Chosen for form-vs-noise balance,
  not tuned; they're named constants in src/features/build.py.
- **xPts uses P(>=1 event) x points, ignoring multi-goal games, bonus,
  cards, saves, and goals-conceded penalties.** Keeps the two models'
  decompositions exactly comparable and interpretable; the ignored terms are
  small and mostly rank-neutral.
- **Double GWs: components combine as 1 - prod(1-p), xPts adds across
  fixtures**; blank GWs simply have no rows.
- **CS training target comes from football-data final scores**, not from
  player-level goals_conceded aggregation — one unambiguous source.
- **Models retrain on demand (~seconds) instead of persisting to disk** — no
  staleness, no artefact management.
- **eval/splits.json created in Phase 2** (models need the train-season list
  at fit time); train = 2016-17..2023-24, holdout = 2024-25 per SPEC.

## Phase 3

- **Stats model is fitted once on the train seasons, never refit inside the
  holdout walk.** Stricter than refitting each GW on everything-so-far (zero
  holdout leakage) and matches how the tool would deploy: a fixed model
  scoring new GWs.
- **Spearman is reported over two populations**: all players with a fixture
  (the SPEC metric — what a tool user browsing the full table experiences)
  and only players with minutes > 0 (harder; strips the free wins from
  ranking bench-sitters last). The headline metric is the all-players one.
- **Per-GW results are written to eval/backtest_results.csv (gitignored)** —
  derived output, regenerable by `make backtest`. (Superseded: they now go
  to runs/, see loop infrastructure below.)

## Autonomous-loop infrastructure (2026-07-02)

- **Experiment surface moved to a top-level model/ package** (pure `git mv`
  of src/models/* and src/features/build.py; imports updated mechanically).
  The loop protocol — required verbatim — confines experiments to `model/`
  and reverts with `git checkout -- model/`, so that directory had to exist
  and contain exactly what experiments may touch (models + features +
  minutes model). Zero logic change, verified by exact reproduction of the
  frozen sealed scores (odds .3436/.6878, stats .3333/.6719) and a green
  suite. Known revert gap: `git checkout -- model/` does not delete NEW
  untracked files an experiment adds under model/; they are inert once the
  tracked entry points are reverted.
- **splits.json: named splits under a "splits" key; legacy top-level keys
  kept equal to the sealed era** so the frozen model/common.py and the
  src/project.py CLI defaults did not need edits.
- **Dev split = all 38 GWs of 2023-24 as-is** (double and blank GWs
  included; the decomposition already aggregates DGWs, blanks simply have no
  rows). Training = 2016-17..2022-23, strictly before the eval season.
- **`--split` defaults to sealed** so the pre-existing `make backtest`
  behavior is unchanged; the loop always passes `--split dev` explicitly.
- **Per-GW backtest CSVs moved to gitignored runs/** because `make lockdown`
  makes eval/ unwritable and the loop must still run backtests.
- **The last-5 baseline lives in eval/ and imports nothing from model/** so
  loop experiments can never move the baseline.
- **Eval integrity = sha256 pins in tests/test_eval_integrity.py** on
  eval/backtest.py, eval/baselines.py, eval/splits.json (splits config).
  Stronger than a git-diff check (still fails after a tampered commit).
  Deliberate human changes to eval/ must update the hashes in the same
  commit. results.md/program.md/CLAUDE.loop.md are protocol-protected but
  not hash-pinned (results.md is append-only by design; program.md is meant
  to be human-editable between runs).
- **loop.sh prepends venv/bin to PATH** so the protocol's literal `python`
  and `pytest` commands resolve to the project venv in headless runs.
- **Model observations found during this session went to IDEAS.md, not into
  code** (models frozen per instruction).
