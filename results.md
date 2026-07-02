# Experiment log (append-only)

Ratchet metric: **stats model, restricted (minutes > 0) mean within-GW
Spearman, dev split** — i.e. the number printed by
`python eval/backtest.py --split dev --model stats` on the HEADLINE line.

## Entry format

Each experiment appends one entry. Never edit or delete previous entries.

```
## Entry <N> — <YYYY-MM-DD> — <git SHA after commit/revert>
- dev score: 0.XXXX (previous best: 0.XXXX)
- change: <one sentence: what was changed, which files>
- hypothesis: <why this was expected to help>
- outcome: IMPROVED (committed) | NO CHANGE / WORSE (reverted) | ERROR (reverted)
- takeaway: <one line for future experiments>
```

---

## Entry 0 — 2026-07-02 — 852c4e9
- dev score: 0.3090 (baseline for the frozen model; this is the number to beat)
- change: none — infrastructure seed entry recording the frozen model's scores
- hypothesis: n/a
- outcome: BASELINE
- takeaway: full frozen-model score card below; both models beat the last-5
  baseline everywhere; odds > stats on both splits.

| model | dev restricted* | dev all | sealed restricted* | sealed all |
|-------|-----------------|---------|--------------------|------------|
| last5 | 0.2623          | 0.4451  | 0.2884             | 0.4635     |
| stats | 0.3090          | 0.6520  | 0.3333             | 0.6719     |
| odds  | 0.3287          | 0.6759  | 0.3436             | 0.6878     |

*restricted (minutes > 0) is the headline metric. The loop ratchets only on
**stats / restricted / dev** = **0.3090**. Sealed numbers are recorded here
once and must not be re-measured by the loop.
