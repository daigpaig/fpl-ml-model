# Per-experiment protocol

1. Read results.md for current best dev score and what's been tried.
2. Run `python eval/backtest.py --split dev --model stats` and confirm the
   restricted score matches the logged best. If not, STOP and log it.
3. Pick ONE untried change guided by program.md and past failures.
4. Implement it. Only files in model/ may change.
5. Re-run the dev backtest AND pytest.
   - Improved and tests green: git commit -m "dev: 0.XXX | <change>"
   - Otherwise: git checkout -- model/ (full revert)
6. Append a results.md entry either way.
7. Exit. Never touch eval/, data/, splits, or protocol files. Never run
   --split sealed. An idea that failed twice is retired.
