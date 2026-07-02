## Working style

- Work through SPEC.md phases in order. Do not start phase N+1 until phase N's
  definition-of-done passes.
- Commit after every working unit with descriptive messages. Never leave the
  repo in a broken state at a commit.
- When you hit an ambiguity SPEC.md doesn't cover: make the simplest reasonable
  choice, and log it in DECISIONS.md with your rationale. Do not stop to ask.
- Write tests as you go, not at the end. Data-shape tests especially
  (right columns, no NaN player IDs, GW counts match expectations).
- Maintain PROGRESS.md: what's done, what's next, any blockers.
- Live API calls: fetch once, cache to disk, all downstream code reads cache.
  Never put API calls in a loop.
