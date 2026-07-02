"""Tamper guard for the frozen eval layer.

The autonomous loop may only modify files under model/. This test pins the
eval scripts and the splits config to their frozen content by hash, so any
edit — accidental or otherwise — fails the whole suite (which the loop must
keep green to commit).

If the HUMAN maintainer deliberately changes the eval layer: update the
hashes below in the same commit and note it in DECISIONS.md. The loop must
never do this (tests/ is outside its allowed surface).
"""

import hashlib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

FROZEN_EVAL_FILES = {
    "eval/backtest.py":
        "0cbd2e3a40619aed3b0fdea72cf4003c80becc1bef1aa3853e0ee1b01f4b45a9",
    "eval/baselines.py":
        "7cd350dc4d3f92f3fcdc092b8988a1750b8beabd9418d7c7c57d60018a67906e",
    "eval/splits.json":
        "0e654f0465f00fb62d23723f9292ee981a714d74f27ae79adcceecb7031c6873",
}


@pytest.mark.parametrize("rel_path", sorted(FROZEN_EVAL_FILES))
def test_eval_file_unchanged(rel_path):
    path = PROJECT_ROOT / rel_path
    assert path.exists(), f"{rel_path} is missing — eval layer is frozen"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == FROZEN_EVAL_FILES[rel_path], (
        f"{rel_path} differs from its frozen state. The eval layer and "
        f"splits are off limits to experiments; revert the change "
        f"(git checkout -- {rel_path})."
    )
