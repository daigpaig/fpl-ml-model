"""Central definition of data locations and the fetch-once/cache-to-disk rule.

All fetchers write raw responses under data/raw/<source>/ and processed
parquet under data/processed/. Downstream code (models, eval) reads ONLY
from data/processed/.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

RAW_VAASTAV_DIR = RAW_DIR / "vaastav"
RAW_UNDERSTAT_DIR = RAW_DIR / "understat"
RAW_FPL_API_DIR = RAW_DIR / "fpl_api"
RAW_FOOTBALL_DATA_DIR = RAW_DIR / "football_data"

GW_HISTORY_PARQUET = PROCESSED_DIR / "gw_history.parquet"
MATCH_ODDS_PARQUET = PROCESSED_DIR / "match_odds.parquet"
UNDERSTAT_PLAYERS_PARQUET = PROCESSED_DIR / "understat_players.parquet"
UNDERSTAT_TEAM_MATCHES_PARQUET = PROCESSED_DIR / "understat_team_matches.parquet"
FPL_PLAYERS_PARQUET = PROCESSED_DIR / "fpl_players.parquet"
FPL_FIXTURES_PARQUET = PROCESSED_DIR / "fpl_fixtures.parquet"

# Seasons covered by the historical build. Train 2016-2023, holdout 2024-25
# (split definition itself lives in eval/splits.json, phase 3).
SEASONS = [
    "2016-17",
    "2017-18",
    "2018-19",
    "2019-20",
    "2020-21",
    "2021-22",
    "2022-23",
    "2023-24",
    "2024-25",
]


def ensure_dirs():
    for d in (
        RAW_VAASTAV_DIR,
        RAW_UNDERSTAT_DIR,
        RAW_FPL_API_DIR,
        RAW_FOOTBALL_DATA_DIR,
        PROCESSED_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)
