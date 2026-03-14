#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Zion shutting down..."
docker compose -f "$PROJECT_ROOT/docker/docker-compose.yml" down

echo "You are now leaving the Matrix."
