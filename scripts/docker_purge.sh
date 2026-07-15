#!/usr/bin/env bash
# Stop the HealthCore Compose stack and free Docker disk (volumes, build cache, unused images).
# Run from anywhere; resolves to the monorepo root (parent of scripts/).
#
# Usage:
#   ./scripts/docker_purge.sh           # full purge (default)
#   ./scripts/docker_purge.sh --soft    # compose down -v only (keep images/cache)
#   ./scripts/docker_purge.sh --help

set -euo pipefail

SOFT=0
for arg in "$@"; do
  case "$arg" in
    --soft) SOFT=1 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg (try --help)" >&2
      exit 1
      ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> repo: $ROOT"
echo "==> docker compose down -v"
docker compose down -v

if [[ "$SOFT" -eq 1 ]]; then
  echo "==> soft mode: skipped builder/volume/image prune"
else
  echo "==> docker builder prune -af"
  docker builder prune -af
  echo "==> docker volume prune -f"
  docker volume prune -f
  echo "==> docker image prune -af"
  docker image prune -af
fi

echo "==> disk after purge:"
df -h /workspaces 2>/dev/null || df -h "$ROOT"
echo "==> done. Rebuild with: docker compose up --build"
