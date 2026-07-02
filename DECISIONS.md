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
