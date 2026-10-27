"""Tests for the Windows-only, non-destructive PR52 three-way reconciler."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts.sky_pr52_reconcile_local import normalized, three_way


@pytest.mark.skipif(not shutil.which("git"), reason="Git executable is required")
def test_three_way_preserves_local_and_pr_changes(tmp_path: Path):
    base = b"one\ntwo\nthree\nfour\n"
    local = b"one local\ntwo\nthree\nfour\n"
    desired = b"one\ntwo\nthree\nfour target\n"
    merged, err = three_way(local, base, desired, tmp_path / "merge")
    assert err == ""
    assert merged is not None
    assert b"one local" in merged
    assert b"four target" in merged


@pytest.mark.skipif(not shutil.which("git"), reason="Git executable is required")
def test_three_way_refuses_overlapping_edits(tmp_path: Path):
    base = b"one\ntwo\nthree\n"
    local = b"one\nlocal version\nthree\n"
    desired = b"one\nnew version\nthree\n"
    merged, err = three_way(local, base, desired, tmp_path / "conflict")
    assert merged is None
    assert err


@pytest.mark.skipif(not shutil.which("git"), reason="Git executable is required")
def test_equal_length_operands_are_distinct_files(tmp_path: Path):
    base = b"a\nb\nc\n"
    local = b"x\nb\nc\n"
    desired = b"a\nb\ny\n"
    merged, err = three_way(local, base, desired, tmp_path / "equal")
    assert merged is not None, err
    assert b"x\n" in merged
    assert b"y\n" in merged


def test_line_ending_normalization():
    assert normalized(b"a\r\nb\r\n") == b"a\nb\n"
