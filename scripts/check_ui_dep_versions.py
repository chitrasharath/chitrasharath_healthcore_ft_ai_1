#!/usr/bin/env python3
"""Compare shared npm dependency version specs across active UI apps."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

ACTIVE_APPS = (
    "uis/website",
    "uis/backoffice/landing",
    "uis/backoffice/backoffice_functions",
    "uis/backoffice/talent-tracker",
    "uis/incident_analyzer",
    "uis/supplier_directory",
)


def load_deps(app_rel: str) -> dict[str, str]:
    package_json = REPO_ROOT / app_rel / "package.json"
    data = json.loads(package_json.read_text(encoding="utf-8"))
    merged: dict[str, str] = {}
    for section in ("dependencies", "devDependencies"):
        merged.update(data.get(section, {}))
    return merged


def main() -> int:
    specs_by_package: dict[str, dict[str, str]] = {}

    for app_rel in ACTIVE_APPS:
        for name, spec in load_deps(app_rel).items():
            specs_by_package.setdefault(name, {})[app_rel] = spec

    mismatches: list[tuple[str, dict[str, str]]] = []
    for package, per_app in sorted(specs_by_package.items()):
        unique_specs = set(per_app.values())
        if len(per_app) > 1 and len(unique_specs) > 1:
            mismatches.append((package, per_app))

    if mismatches:
        print("UI dependency version mismatches:")
        for package, per_app in mismatches:
            print(f"\n{package}:")
            for app_rel, spec in sorted(per_app.items()):
                print(f"  {app_rel}: {spec}")
        return 1

    shared_count = sum(1 for per_app in specs_by_package.values() if len(per_app) > 1)
    print(
        f"OK: {len(ACTIVE_APPS)} active apps checked; "
        f"{shared_count} shared packages aligned across apps."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
