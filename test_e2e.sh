#!/usr/bin/env bash
# =============================================================================
# End-to-End Test Script — Agentic Research Paper Assistant
# =============================================================================
# Verifies the containerised system works from configuration files alone.
#
# Steps:
#   1. Build container images
#   2. Start all services
#   3. Wait for health check
#   4. Send a test query
#   5. Validate response
#   6. Verify data persistence across restart
#   7. Tear down
#
# Usage: bash test_e2e.sh
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

LOG_FILE="test_e2e_output.log"

echo "=============================================" | tee "$LOG_FILE"
echo " E2E Test — Research Paper Assistant" | tee -a "$LOG_FILE"
echo "=============================================" | tee -a "$LOG_FILE"

# ── Pre-flight checks ───────────────────────────────────────────────────────
echo -e "\n${YELLOW}[1/7] Pre-flight checks...${NC}" | tee -a "$LOG_FILE"

if [ ! -f ".env" ]; then
    echo -e "${RED}FAIL: .env file not found${NC}" | tee -a "$LOG_FILE"
    exit 1
fi

if [ ! -f "secrets/firebase-credentials.json" ]; then
    echo -e "${YELLOW}Setting up secrets directory...${NC}" | tee -a "$LOG_FILE"
    mkdir -p secrets
    if [ -f "research-paper-assistant.json" ]; then
        cp research-paper-assistant.json secrets/firebase-credentials.json
        echo "  Copied Firebase credentials to secrets/" | tee -a "$LOG_FILE"
    else
        echo -e "${RED}FAIL: No Firebase credentials found${NC}" | tee -a "$LOG_FILE"
        exit 1
    fi
fi

echo -e "${GREEN}  Pre-flight checks passed${NC}" | tee -a "$LOG_FILE"

# ── Build ────────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}[2/7] Building container images...${NC}" | tee -a "$LOG_FILE"
docker compose build 2>&1 | tee -a "$LOG_FILE"
echo -e "${GREEN}  Build complete${NC}" | tee -a "$LOG_FILE"

# ── Start services ──────────────────────────────────────────────────────────
echo -e "\n${YELLOW}[3/7] Starting services...${NC}" | tee -a "$LOG_FILE"
docker compose up -d 2>&1 | tee -a "$LOG_FILE"

# ── Wait for health check ───────────────────────────────────────────────────
echo -e "\n${YELLOW}[4/7] Waiting for API health check...${NC}" | tee -a "$LOG_FILE"
MAX_RETRIES=30
RETRY=0
until curl -sf http://localhost:8000/health > /dev/null 2>&1; do
    RETRY=$((RETRY + 1))
    if [ $RETRY -ge $MAX_RETRIES ]; then
        echo -e "${RED}FAIL: API did not become healthy after ${MAX_RETRIES}s${NC}" | tee -a "$LOG_FILE"
        docker compose logs 2>&1 | tee -a "$LOG_FILE"
        docker compose down 2>&1
        exit 1
    fi
    sleep 1
done

HEALTH=$(curl -s http://localhost:8000/health)
echo "  Health response: $HEALTH" | tee -a "$LOG_FILE"
echo -e "${GREEN}  API is healthy${NC}" | tee -a "$LOG_FILE"

# ── Send test query ─────────────────────────────────────────────────────────
echo -e "\n${YELLOW}[5/7] Sending test query to agent...${NC}" | tee -a "$LOG_FILE"
RESPONSE=$(curl -s -X POST http://localhost:8000/api/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "Find papers about transformer neural networks", "thread_id": "e2e-test-001"}')

echo "  Response: $RESPONSE" | tee -a "$LOG_FILE"

# Validate response has an answer
if echo "$RESPONSE" | grep -q '"answer"'; then
    echo -e "${GREEN}  Agent returned a valid answer${NC}" | tee -a "$LOG_FILE"
else
    echo -e "${RED}FAIL: Agent did not return a valid answer${NC}" | tee -a "$LOG_FILE"
    docker compose down 2>&1
    exit 1
fi

if echo "$RESPONSE" | grep -q '"status":"success"'; then
    echo -e "${GREEN}  Status: success${NC}" | tee -a "$LOG_FILE"
else
    echo -e "${RED}FAIL: Status is not success${NC}" | tee -a "$LOG_FILE"
    docker compose down 2>&1
    exit 1
fi

# ── Verify persistence ──────────────────────────────────────────────────────
echo -e "\n${YELLOW}[6/7] Verifying persistence across restart...${NC}" | tee -a "$LOG_FILE"

# Store a key in Redis
docker exec research-agent-redis redis-cli SET e2e-test-key "persistence-proof" > /dev/null 2>&1

# Restart containers (without removing volumes)
docker compose down 2>&1 | tee -a "$LOG_FILE"
docker compose up -d 2>&1 | tee -a "$LOG_FILE"

# Wait for Redis to be ready
sleep 5

# Check if key survived
PERSISTED=$(docker exec research-agent-redis redis-cli GET e2e-test-key 2>/dev/null)
if [ "$PERSISTED" = "persistence-proof" ]; then
    echo -e "${GREEN}  Data persisted across restart ✓${NC}" | tee -a "$LOG_FILE"
else
    echo -e "${RED}FAIL: Data did NOT persist across restart${NC}" | tee -a "$LOG_FILE"
    docker compose down 2>&1
    exit 1
fi

# Clean up test key
docker exec research-agent-redis redis-cli DEL e2e-test-key > /dev/null 2>&1

# ── Tear down ────────────────────────────────────────────────────────────────
echo -e "\n${YELLOW}[7/7] Tearing down...${NC}" | tee -a "$LOG_FILE"
docker compose down 2>&1 | tee -a "$LOG_FILE"

echo ""
echo "=============================================" | tee -a "$LOG_FILE"
echo -e "${GREEN} ALL E2E TESTS PASSED ✓${NC}" | tee -a "$LOG_FILE"
echo "=============================================" | tee -a "$LOG_FILE"
echo "  Log saved to: $LOG_FILE"
