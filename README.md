# FPL ML Model

This project is an early-stage MVP for an FPL projection model built around betting odds.

## Current goal

The current version is trying to answer a very simple question:

**Given bookmaker odds and FPL player/fixture data, can we generate a rough expected points projection for players in a given gameweek?**

Right now, the project is focused on **GW32** and is intentionally very lightweight.

---

## What the current pipeline does

### 1. Pull FPL data

Using the public FPL API, the project pulls:

- player metadata
- team information
- position information
- fixture information

This is used to create a gameweek-specific player table containing:

- player name
- team
- position
- price
- opponent
- home/away indicator

---

### 2. Pull betting odds

Using The Odds API, the project currently pulls:

- **player anytime goalscorer odds**
- **team totals odds** (used to infer clean sheet probability)

These are converted into simple implied probabilities.

For example:

- `goal_prob = 1 / goal_odds`
- `clean_sheet_prob = 1 / clean_sheet_odds`

At the moment, bookmaker prices are averaged if multiple bookmakers are returned.

---

### 3. Merge odds onto FPL players

The project then tries to merge betting market data onto the FPL player table.

Currently this is done using a very simple name-matching approach. The idea is to attach:

- a player-level goal probability
- a team-level clean sheet probability

to each FPL player row.

---

### 4. Compute rough expected FPL points

The current MVP uses a very simple expected-points formula:

\[
\text{Expected Points} =
\text{Appearance Points}

- \text{Expected Goal Points}
- \text{Expected Clean Sheet Points}
  \]

Using rough assumptions:

- all matched players receive **2 appearance points**
- goal points are based on FPL scoring by position
- clean sheet points are based on FPL scoring by position

So this version is not really a full machine learning model yet. It is better described as a **market-implied FPL projection prototype**.

---

## Current project structure

- `src/fetch_fpl_data.py`  
  Pulls player/team/position/fixture data from the FPL API and creates gameweek-specific player tables.

- `src/fetch_odds_data.py`  
  Pulls odds data from The Odds API and extracts player goal odds and team-based clean sheet information.

- `src/merge_tables.py` / `src/build_model.py`  
  Merges FPL data with odds data and computes rough expected points.

- `data/`  
  Stores intermediate CSV outputs.

---

## Current limitations

This version is very much an MVP and has a lot of limitations.

### 1. Name matching is imperfect

The current merge between FPL players and bookmaker player names is very naive.

This can cause incorrect matches. For example, players with the same surname may get linked to the wrong odds row.

This is currently acceptable for prototyping, but it needs to be improved before the model can be trusted.

---

### 2. Minutes are not modeled

The model currently assumes matched players get full appearance points.

This is a major simplification. In reality, expected FPL points depend heavily on:

- whether a player starts
- whether they play 60+ minutes
- substitution risk
- rotation risk

This is probably the biggest missing piece in the current version.

---

### 3. Assist odds are not included yet

The current model only uses:

- goal probability
- clean sheet probability

It does **not** yet include assists, which means many creators and midfielders are undervalued.

---

### 4. Clean sheet probability is inferred in a simplified way

The project currently uses team totals markets to estimate clean sheet probability.

This is a reasonable MVP approach, but it is still a simplification and may not always be available or consistent across bookmakers.

---

### 5. Bookmaker margin is not removed

Probabilities are currently calculated directly as:

\[
p = 1 / \text{odds}
\]

This means bookmaker vig/overround is still present in the estimates.

That is acceptable for a first pass, but not ideal long term.

---

### 6. No bonus, cards, saves, or defensive contribution modeling

The current expected-points formula ignores:

- assists
- bonus points
- yellow/red cards
- goalkeeper saves
- goals conceded penalties
- defensive contributions
- penalty miss risk
- own goals

So projections are only rough attacking/clean-sheet based estimates.

---

### 7. Only a single-gameweek MVP so far

The project is currently focused on getting a working projection table for one target gameweek.

There is not yet:

- backtesting
- model evaluation
- historical training pipeline
- transfer/chip strategy layer

---

## What this project is becoming

The long-term goal is to build a stronger FPL decision framework with multiple layers:

1. **Betting-market-based projection model**
2. **Stats/Opta-style projection model**
3. **A comparison layer that explains differences between the two**
4. **Eventually, transfer and chip strategy logic**

The current repository is just the first small step: building a betting-based projection MVP.

---

## Immediate next steps

Likely next improvements:

- improve player name matching
- add assist probabilities
- build a minutes / starting probability model
- improve clean sheet estimation
- backtest projections against historical FPL outcomes

---

## Status

**Current status:** early MVP / prototype

Useful for:

- testing the pipeline
- understanding how bookmaker markets can map to FPL points
- building a first ranking system

Not yet reliable enough for:

- serious decision-making
- automated transfers
- robust player comparisons without manual checking
