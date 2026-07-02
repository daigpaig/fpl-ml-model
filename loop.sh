#!/usr/bin/env bash
# Autonomous research loop: run N one-experiment iterations (default 5).
#   ./loop.sh [N]
set -euo pipefail
cd "$(dirname "$0")"

# Protocol commands say `python` / `pytest`; resolve them to the venv.
export PATH="$PWD/venv/bin:$PATH"

N="${1:-5}"
for i in $(seq 1 "$N"); do
    echo "=== loop iteration $i/$N — $(date '+%Y-%m-%d %H:%M:%S') ==="
    claude --dangerously-skip-permissions -p "Read CLAUDE.loop.md, program.md, and the last 30 lines of results.md. Run exactly ONE experiment per the protocol, then exit."
done
