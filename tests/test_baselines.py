"""Unit tests for the last-5-appearance baseline (anti-lookahead included)."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))
from baselines import last5_projection  # noqa: E402


def _history(points_minutes: list[tuple[int, int]]) -> pd.DataFrame:
    """One player, one row per consecutive GW of 2023-24."""
    rows = []
    for i, (points, minutes) in enumerate(points_minutes, start=1):
        rows.append({
            "season": "2023-24", "gw": i, "element": 1,
            "player_name": "Test Player", "position": "MID",
            "total_points": points, "minutes": minutes,
        })
    return pd.DataFrame(rows)


def _xpts(history: pd.DataFrame) -> dict[int, float]:
    proj = last5_projection(history)
    return dict(zip(proj["gw"], proj["xpts"]))


class TestLast5Baseline:
    def test_uses_only_prior_appearances(self):
        xpts = _xpts(_history([(2, 90), (5, 90), (0, 0), (7, 90)]))
        assert xpts[1] == 0.0                    # no history yet
        assert xpts[2] == pytest.approx(2.0)     # mean of GW1
        assert xpts[3] == pytest.approx(3.5)     # bench GW: mean of GW1-2
        assert xpts[4] == pytest.approx(3.5)     # GW3 was not an appearance

    def test_window_is_five_appearances(self):
        # 6 appearances of 6 pts then one of 0: GW8 sees only the last 5.
        xpts = _xpts(_history([(6, 90)] * 6 + [(0, 90), (0, 90)]))
        assert xpts[7] == pytest.approx(6.0)
        assert xpts[8] == pytest.approx((6 * 4 + 0) / 5)

    def test_current_gw_points_never_leak(self):
        quiet = _history([(2, 90), (3, 90)])
        haul = _history([(2, 90), (20, 90)])
        assert _xpts(quiet)[2] == _xpts(haul)[2]

    def test_double_gw_second_fixture_cannot_see_first(self):
        # Two fixtures in GW2: baseline for GW2 must only reflect GW1.
        history = _history([(2, 90)])
        dgw = pd.concat([
            history,
            pd.DataFrame([
                {"season": "2023-24", "gw": 2, "element": 1,
                 "player_name": "Test Player", "position": "MID",
                 "total_points": 10, "minutes": 90},
                {"season": "2023-24", "gw": 2, "element": 1,
                 "player_name": "Test Player", "position": "MID",
                 "total_points": 12, "minutes": 90},
            ]),
        ], ignore_index=True)
        proj = last5_projection(dgw)
        gw2 = proj[proj["gw"] == 2]
        assert len(gw2) == 1                       # one row per player-GW
        assert gw2["xpts"].iloc[0] == pytest.approx(2.0)
