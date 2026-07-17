"""Run pytest from the repository root regardless of the caller's cwd.

With no path args, pytest uses ``[tool.pytest.ini_options] testpaths`` from
``pyproject.toml`` (``services/api/tests`` and ``tests``). Explicit paths such
as ``tests/pipelines/test_pipeline.py`` are passed through unchanged.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> None:
    os.chdir(_repo_root())
    import pytest

    raise SystemExit(pytest.main(sys.argv[1:]))
