# =============================================================================
# End-to-End Test Script (PowerShell) — Agentic Research Paper Assistant
# =============================================================================
# Verifies the containerised system works from configuration files alone.
#
# Usage: .\test_e2e.ps1
# =============================================================================

$ErrorActionPreference = "Stop"
$LogFile = "test_e2e_output.log"

function Write-Log {
    param([string]$Message)
    Write-Host $Message
    Add-Content -Path $LogFile -Value $Message
}

Write-Log "============================================="
Write-Log " E2E Test - Research Paper Assistant"
Write-Log "============================================="

# ── Pre-flight checks ───────────────────────────────────────────────────────
Write-Log "`n[1/7] Pre-flight checks..."

if (-not (Test-Path ".env")) {
    Write-Log "FAIL: .env file not found"
    exit 1
}

if (-not (Test-Path "secrets/firebase-credentials.json")) {
    Write-Log "Setting up secrets directory..."
    New-Item -ItemType Directory -Path "secrets" -Force | Out-Null
    if (Test-Path "research-paper-assistant.json") {
        Copy-Item "research-paper-assistant.json" "secrets/firebase-credentials.json"
        Write-Log "  Copied Firebase credentials to secrets/"
    } else {
        Write-Log "FAIL: No Firebase credentials found"
        exit 1
    }
}

Write-Log "  Pre-flight checks passed"

# ── Build ────────────────────────────────────────────────────────────────────
Write-Log "`n[2/7] Building container images..."
docker compose build 2>&1 | Tee-Object -FilePath $LogFile -Append
Write-Log "  Build complete"

# ── Start services ──────────────────────────────────────────────────────────
Write-Log "`n[3/7] Starting services..."
docker compose up -d 2>&1 | Tee-Object -FilePath $LogFile -Append

# ── Wait for health check ───────────────────────────────────────────────────
Write-Log "`n[4/7] Waiting for API health check..."
$maxRetries = 30
$retry = 0
$healthy = $false

while (-not $healthy -and $retry -lt $maxRetries) {
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -ErrorAction SilentlyContinue
        if ($health.status -eq "OK") {
            $healthy = $true
        }
    } catch {
        $retry++
        Start-Sleep -Seconds 1
    }
}

if (-not $healthy) {
    Write-Log "FAIL: API did not become healthy after ${maxRetries}s"
    docker compose logs 2>&1 | Tee-Object -FilePath $LogFile -Append
    docker compose down 2>&1
    exit 1
}

$healthJson = $health | ConvertTo-Json -Compress
Write-Log "  Health response: $healthJson"
Write-Log "  API is healthy"

# ── Send test query ─────────────────────────────────────────────────────────
Write-Log "`n[5/7] Sending test query to agent..."
$body = @{
    message = "Find papers about transformer neural networks"
    thread_id = "e2e-test-001"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/chat" `
        -Method Post `
        -ContentType "application/json" `
        -Body $body `
        -TimeoutSec 120
    
    $responseJson = $response | ConvertTo-Json -Compress -Depth 5
    Write-Log "  Response: $responseJson"

    if ($response.answer) {
        Write-Log "  Agent returned a valid answer"
    } else {
        Write-Log "FAIL: Agent did not return a valid answer"
        docker compose down 2>&1
        exit 1
    }

    if ($response.status -eq "success") {
        Write-Log "  Status: success"
    } else {
        Write-Log "FAIL: Status is not success"
        docker compose down 2>&1
        exit 1
    }
} catch {
    Write-Log "FAIL: Request to agent failed - $_"
    docker compose down 2>&1
    exit 1
}

# ── Verify persistence ──────────────────────────────────────────────────────
Write-Log "`n[6/7] Verifying persistence across restart..."

# Store a key in Redis
docker exec research-agent-redis redis-cli SET e2e-test-key "persistence-proof" | Out-Null

# Restart containers (without removing volumes)
docker compose down 2>&1 | Out-Null
docker compose up -d 2>&1 | Out-Null

# Wait for Redis to be ready
Start-Sleep -Seconds 5

# Check if key survived
$persisted = docker exec research-agent-redis redis-cli GET e2e-test-key 2>$null
if ($persisted -eq "persistence-proof") {
    Write-Log "  Data persisted across restart"
} else {
    Write-Log "FAIL: Data did NOT persist across restart"
    docker compose down 2>&1
    exit 1
}

# Clean up test key
docker exec research-agent-redis redis-cli DEL e2e-test-key | Out-Null

# ── Tear down ────────────────────────────────────────────────────────────────
Write-Log "`n[7/7] Tearing down..."
docker compose down 2>&1 | Tee-Object -FilePath $LogFile -Append

Write-Log ""
Write-Log "============================================="
Write-Log " ALL E2E TESTS PASSED"
Write-Log "============================================="
Write-Log "  Log saved to: $LogFile"
