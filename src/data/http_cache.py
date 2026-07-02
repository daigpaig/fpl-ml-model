"""Fetch-once helper: every remote request lands in a raw cache file first.

If the cache file already exists the network is never touched, so re-running
`make fetch-historical` is free and downstream code always reads from disk.
"""

import time
from pathlib import Path

import requests

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "fpl-ml-model/0.1 (personal research project)"
)

# Small politeness delay between real network hits.
REQUEST_DELAY_SECONDS = 0.5


def fetch_cached(
    url: str, cache_path: Path, force: bool = False, headers: dict | None = None
) -> bytes:
    """Return the body of `url`, downloading only if `cache_path` is absent."""
    if cache_path.exists() and not force:
        return cache_path.read_bytes()

    request_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    response = requests.get(url, headers=request_headers, timeout=60)
    response.raise_for_status()

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(response.content)
    time.sleep(REQUEST_DELAY_SECONDS)
    return response.content
