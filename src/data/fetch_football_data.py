"""Historical EPL match odds from football-data.co.uk.

One CSV per season (raw cache), normalized into match_odds.parquet with one
row per match: canonical team names, kickoff date, final score, and
market-average decimal odds for 1X2 and over/under 2.5 goals.

These are the pre-match odds the Phase 2 odds model turns into implied team
goal expectations. Column-name era differences:
- 1X2 / O/U averages are BbAvH/BbAvD/BbAvA / BbAv>2.5 / BbAv<2.5 up to
  2018-19, AvgH/AvgD/AvgA / Avg>2.5 / Avg<2.5 from 2019-20.
- Date is dd/mm/yy in old files, dd/mm/yyyy in new ones.
"""

import io

import pandas as pd

from .http_cache import fetch_cached
from .paths import MATCH_ODDS_PARQUET, RAW_FOOTBALL_DATA_DIR, SEASONS, ensure_dirs
from .team_names import canonical_team_name

BASE_URL = "https://www.football-data.co.uk/mmz4281/{code}/E0.csv"

# (preferred, fallback) column names per output field
ODDS_COLUMNS = {
    "home_odds": ("AvgH", "BbAvH"),
    "draw_odds": ("AvgD", "BbAvD"),
    "away_odds": ("AvgA", "BbAvA"),
    "over25_odds": ("Avg>2.5", "BbAv>2.5"),
    "under25_odds": ("Avg<2.5", "BbAv<2.5"),
}


def season_code(season: str) -> str:
    """'2016-17' -> '1617'."""
    start, end = season.split("-")
    return start[2:] + end


def fetch_season_odds_csv(season: str, force: bool = False) -> pd.DataFrame:
    raw = fetch_cached(
        BASE_URL.format(code=season_code(season)),
        RAW_FOOTBALL_DATA_DIR / f"E0_{season}.csv",
        force=force,
    )
    return pd.read_csv(io.BytesIO(raw), encoding="latin-1")


def normalize_season_odds(season: str, df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({
        "season": season,
        "date": pd.to_datetime(df["Date"], dayfirst=True, format="mixed"),
        "home_team": df["HomeTeam"].map(
            lambda n: canonical_team_name(n, "football_data")
        ),
        "away_team": df["AwayTeam"].map(
            lambda n: canonical_team_name(n, "football_data")
        ),
        "home_goals": df["FTHG"].astype(int),
        "away_goals": df["FTAG"].astype(int),
    })
    for field, (preferred, fallback) in ODDS_COLUMNS.items():
        col = preferred if preferred in df.columns else fallback
        out[field] = pd.to_numeric(df[col], errors="coerce")
    return out


def build_match_odds(force: bool = False) -> pd.DataFrame:
    """Fetch all seasons (cached) and write match_odds.parquet."""
    ensure_dirs()
    frames = []
    for season in SEASONS:
        raw = fetch_season_odds_csv(season, force=force)
        normalized = normalize_season_odds(season, raw)
        frames.append(normalized)
        print(f"  football-data {season}: {len(normalized):>4} matches")

    odds = pd.concat(frames, ignore_index=True)
    odds.to_parquet(MATCH_ODDS_PARQUET, index=False)
    print(f"  -> match_odds.parquet: {len(odds)} rows")
    return odds
