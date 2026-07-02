"""Entry point for `make fetch-historical`.

Runs all three fetchers (vaastav historical, understat, FPL API snapshot).
Every remote file is cached under data/raw/ on first fetch; re-runs rebuild
the processed parquet files from cache without touching the network.
"""

import argparse

from src.data.fetch_fpl_api import build_fpl_snapshot
from src.data.fetch_understat import build_understat
from src.data.fetch_vaastav import build_gw_history


def main():
    parser = argparse.ArgumentParser(description="Fetch all historical data")
    parser.add_argument(
        "--force", action="store_true",
        help="re-download even if raw cache files exist",
    )
    args = parser.parse_args()

    print("[1/3] vaastav historical per-GW data")
    build_gw_history(force=args.force)

    print("[2/3] understat season + team-match data")
    build_understat(force=args.force)

    print("[3/3] FPL API current snapshot")
    build_fpl_snapshot(force=args.force)

    print("done.")


if __name__ == "__main__":
    main()
