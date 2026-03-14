#!/usr/bin/env bash
set -e

cat << 'BANNER'

  ╔══════════════════════════════════════════╗
  ║                                          ║
  ║     ███████╗██╗ ██████╗ ███╗   ██╗      ║
  ║     ╚══███╔╝██║██╔═══██╗████╗  ██║      ║
  ║       ███╔╝ ██║██║   ██║██╔██╗ ██║      ║
  ║      ███╔╝  ██║██║   ██║██║╚██╗██║      ║
  ║     ███████╗██║╚██████╔╝██║ ╚████║      ║
  ║     ╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝      ║
  ║                                          ║
  ║        E N T E R I N G   T H E           ║
  ║            M A T R I X                   ║
  ║                                          ║
  ╚══════════════════════════════════════════╝

BANNER

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/docker/.env"
ENV_EXAMPLE="$PROJECT_ROOT/docker/.env.example"

if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed or not in PATH."
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "ERROR: Docker daemon is not running. Start Docker Desktop first."
    exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "WARNING: No .env file found. Copying from .env.example..."
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "IMPORTANT: Edit docker/.env with your actual API keys before proceeding."
    echo ""
fi

echo "Booting Zion..."
docker compose -f "$PROJECT_ROOT/docker/docker-compose.yml" up --build -d

echo ""
echo "Waiting for services to stabilize..."
sleep 5

"$PROJECT_ROOT/scripts/health_check.sh"

echo ""
echo "Zion is online. Welcome to the Matrix."
