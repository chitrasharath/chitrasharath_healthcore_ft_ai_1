#!/usr/bin/env python3
"""CLI seed for the company knowledge-base Qdrant index.

Run with the API stopped when possible (local Qdrant file lock):
  uv run python scripts/seed_knowledge_base.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_API_ROOT = _REPO_ROOT / "services" / "api"
for _path in (_API_ROOT, _REPO_ROOT):
    path_str = str(_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from data.process.rag import bootstrap_env, main as setup_main, reset_qdrant_client  # noqa: E402


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    bootstrap_env()
    try:
        setup_main()
    finally:
        reset_qdrant_client()


if __name__ == "__main__":
    main()
