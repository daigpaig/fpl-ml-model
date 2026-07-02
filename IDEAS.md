# Ideas / observed model issues (not acted on — models are frozen)

Noted during infrastructure work on 2026-07-02. Some overlap with
program.md directions; the loop should treat program.md as authoritative.

## Possible bugs / rough edges

- **Odds model goal_prob ignores availability.** goal_prob = f(team lambda x
  trailing share) is not multiplied by play_prob, so a player who stopped
  starting keeps a high goal_prob until the 20-GW share window catches up
  (seen: Ollie Watkins 2024-25 GW20, start_prob 0.20 but goal_prob 0.50).
  xPts partially compensates via appearance points only.
- **xPts uses P(>=1 event) x points**, undercounting multi-goal hauls —
  systematically penalises explosive forwards relative to E[goals] x points.
- **GKP ranking is weak in both models** (dev restricted Spearman ~0.10 vs
  ~0.42 for MID/FWD). Saves points are unmodeled; a saves proxy (opponent
  xG vs team xGA) might be the single biggest positional win.
- **Team-form NaN fill is a constant 1.35** for the pre-history boundary
  (start of 2016-17); a league-average-by-season would be cleaner.
- **start_prob for new signings is 0 until they appear** — no prior, so a
  marquee striker projects 0.0 xPts in his debut GW. Price could serve as a
  prior.
- **starts column exists in vaastav data from 2022-23** but the minutes
  model still proxies starts with minutes >= 60 everywhere; could use real
  starts where available.
- **Same-name same-position players** would pool cross-season rolling
  history (none observed in current data, but unguarded).

## Smaller ideas

- Bonus points are droppable from targets but predictable (BPS correlates
  with goals/assists/CS) — even a crude bonus term might lift restricted
  Spearman for premium players.
- Goals-conceded penalty for GKP/DEF (-1 per 2 conceded) is unmodeled and
  cheap to add from the existing lambdas / cs model.
- Odds model could blend O/U 1.5 and 3.5 markets if ever re-fetched
  (football-data only carries 2.5 consistently — would need new data, so
  out of scope for the loop).
