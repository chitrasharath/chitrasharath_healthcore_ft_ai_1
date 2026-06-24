"""Run API tests from the repository root regardless of the caller's cwd."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> None:
    root = _repo_root()
    os.chdir(root)
    test_dir = root / "services" / "api" / "tests"

    import pytest

    args = [str(test_dir), *sys.argv[1:]]
    raise SystemExit(pytest.main(args))
