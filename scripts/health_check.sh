#!/usr/bin/env bash

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "╔══════════════════════════════════════╗"
echo "║       ZION HEALTH CHECK              ║"
echo "╠══════════════════════════════════════╣"

if docker ps --format '{{.Names}}' | grep -q '^zion$'; then
    printf "║  zion-core:    ${GREEN}ONLINE${NC}               ║\n"
else
    printf "║  zion-core:    ${RED}OFFLINE${NC}              ║\n"
fi

if docker exec zion-redis redis-cli ping 2>/dev/null | grep -q 'PONG'; then
    printf "║  zion-redis:   ${GREEN}ONLINE${NC}               ║\n"
else
    printf "║  zion-redis:   ${RED}OFFLINE${NC}              ║\n"
fi

if curl -s http://localhost:8001/api/v1/heartbeat > /dev/null 2>&1; then
    printf "║  zion-chromadb:${GREEN}ONLINE${NC}               ║\n"
else
    printf "║  zion-chromadb:${RED}OFFLINE${NC}              ║\n"
fi

echo "╚══════════════════════════════════════╝"
