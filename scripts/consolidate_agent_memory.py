#!/usr/bin/env python3
"""Consolidate agent memories per scope (suggested nightly cron).

Usage (from repo root or services/api):
  uv run python scripts/consolidate_agent_memory.py
  uv run python scripts/consolidate_agent_memory.py --clinic-id 2 --staff-id 42

Suggested cron (document only):
  0 3 * * * cd /path/to/repo && uv run python scripts/consolidate_agent_memory.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_API = _REPO / "services" / "api"
for path in (_REPO, _API):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def main() -> int:
    parser = argparse.ArgumentParser(description="Consolidate agent memory scopes")
    parser.add_argument("--clinic-id", default=None)
    parser.add_argument("--staff-id", default=None)
    args = parser.parse_args()

    from app.domains.agent.memory.consolidate import consolidate_scope
    from app.domains.agent.memory.schemas import MemoryScope
    from app.domains.agent.memory.store import get_memory_store

    store = get_memory_store()
    if store is None:
        print("Memory store unavailable (Redis down or memory_enabled=false)")
        return 1

    if args.clinic_id and args.staff_id:
        scopes = [
            MemoryScope(clinic_id=args.clinic_id, staff_id=args.staff_id).normalized()
        ]
    else:
        # Scan Redis for mem:index:* keys
        scopes = []
        for key in store._redis.scan_iter(match="mem:index:*"):
            key_s = key.decode() if isinstance(key, bytes) else str(key)
            parts = key_s.split(":")
            # mem:index:{clinic}:{staff}
            if len(parts) >= 4:
                scopes.append(
                    MemoryScope(clinic_id=parts[2], staff_id=parts[3]).normalized()
                )

    if not scopes:
        print("No memory scopes found")
        return 0

    for scope in scopes:
        result = consolidate_scope(store, scope)
        print(f"{scope.clinic_id}/{scope.staff_id}: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
