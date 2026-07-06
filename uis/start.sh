#!/bin/sh
set -e

WEBSITE_PORT="${WEBSITE_PORT:-3000}"
BACKOFFICE_PORT="${BACKOFFICE_PORT:-3001}"

cd /app/uis/website
npm run dev -- --port "$WEBSITE_PORT" --hostname 0.0.0.0 &

cd /app/uis/backoffice/landing
npm run dev -- --port "$BACKOFFICE_PORT" --hostname 0.0.0.0 &

wait
