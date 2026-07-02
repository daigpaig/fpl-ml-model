"""Canonical team names across data sources.

Canonical form = the FPL/vaastav short name (e.g. "Man Utd", "Spurs"),
because gw_history.parquet is the spine every other table joins onto.
Mappings are explicit — team names are a small closed set, so fuzzy
matching (reserved for player names per SPEC) is unnecessary risk here.
"""

# understat team_title -> canonical
UNDERSTAT_TO_CANONICAL = {
    "Manchester City": "Man City",
    "Manchester United": "Man Utd",
    "Newcastle United": "Newcastle",
    "Nottingham Forest": "Nott'm Forest",
    "Sheffield United": "Sheffield Utd",
    "Tottenham": "Spurs",
    "West Bromwich Albion": "West Brom",
    "Wolverhampton Wanderers": "Wolves",
}

# football-data.co.uk HomeTeam/AwayTeam -> canonical
FOOTBALL_DATA_TO_CANONICAL = {
    "Man United": "Man Utd",
    "Tottenham": "Spurs",
    "Sheffield United": "Sheffield Utd",
}


def canonical_team_name(name: str, source: str) -> str:
    """Map a source team name onto the canonical (FPL short) name."""
    mapping = {
        "understat": UNDERSTAT_TO_CANONICAL,
        "football_data": FOOTBALL_DATA_TO_CANONICAL,
        "fpl": {},
    }[source]
    return mapping.get(name, name)
