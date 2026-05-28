#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# agent_boot.sh — Headless Environment Bootstrap for AI Agents
#
# This script programmatically installs all dependencies, configures the
# environment, and starts services in a fully headless, idempotent manner.
# Running it twice produces the same result.
#
# Output: Structured JSON status report to stdout on completion.
# Exit codes:
#   0 - Environment ready
#   1 - Dependency installation failed
#   2 - Backend failed to start
#   3 - Frontend failed to start
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/frontend"
DATA_DIR="$REPO_ROOT/data"
LOG_DIR="$REPO_ROOT/.agent_logs"

mkdir -p "$DATA_DIR" "$LOG_DIR"

# JSON output helper
json_status() {
    local status="$1"
    local message="$2"
    local phase="$3"
    echo "{\"status\":\"$status\",\"phase\":\"$phase\",\"message\":\"$message\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"
}

json_report() {
    cat <<EOF
{
  "status": "$1",
  "environment": {
    "python_version": "$PYTHON_VERSION",
    "node_version": "$NODE_VERSION",
    "backend_pid": ${BACKEND_PID:-null},
    "backend_url": "http://localhost:8000",
    "frontend_url": "http://localhost:3000",
    "storage": "sqlite",
    "storage_path": "$DATA_DIR/reviews.db"
  },
  "feature_flags": "all_enabled",
  "logs": {
    "backend": "$LOG_DIR/backend.log",
    "frontend": "$LOG_DIR/frontend.log"
  },
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
}

# ---- Phase 1: System Dependencies ----
echo "$(json_status "running" "Checking system dependencies" "dependencies")" >&2

PYTHON_VERSION="unknown"
NODE_VERSION="unknown"

if ! command -v python3 &>/dev/null; then
    echo "$(json_status "error" "python3 not found in PATH" "dependencies")" >&2
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')

if ! command -v node &>/dev/null; then
    echo "$(json_status "warning" "node not found, attempting install via nvm or apt" "dependencies")" >&2
    if command -v apt-get &>/dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y -qq nodejs npm >/dev/null 2>&1 || true
    fi
fi

if command -v node &>/dev/null; then
    NODE_VERSION=$(node --version 2>&1)
fi

# ---- Phase 2: Python Environment ----
echo "$(json_status "running" "Setting up Python environment" "python")" >&2

cd "$REPO_ROOT"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate

pip install -e ".[dev]" --quiet 2>"$LOG_DIR/pip_install.log" || {
    echo "$(json_status "error" "pip install failed — see $LOG_DIR/pip_install.log" "python")" >&2
    exit 1
}

# ---- Phase 3: Node Environment ----
echo "$(json_status "running" "Setting up Node environment" "node")" >&2

if [ -d "$FRONTEND_DIR" ] && command -v npm &>/dev/null; then
    cd "$FRONTEND_DIR"
    if [ ! -d "node_modules" ]; then
        npm install --silent 2>"$LOG_DIR/npm_install.log" || {
            echo "$(json_status "error" "npm install failed — see $LOG_DIR/npm_install.log" "node")" >&2
            exit 3
        }
    fi
    cd "$REPO_ROOT"
fi

# ---- Phase 4: Environment Variables ----
echo "$(json_status "running" "Configuring environment" "config")" >&2

export STORAGE_BACKEND=sqlite
export STORAGE_DB_PATH="$DATA_DIR/reviews.db"

# Enable all feature flags for testing
export FEATURE_PRD_CHANGES=true
export FEATURE_PRD_QUALITY_SCORING=true
export FEATURE_EFFORT_ESTIMATION=true
export FEATURE_EXPERT_ASSIST=true
export FEATURE_PM_PATTERN_LEARNING=true
export FEATURE_SIDE_BY_SIDE_DIFF=true
export FEATURE_PRD_SAVE_TO_FILE=true
export FEATURE_BULK_PRD_ANALYSIS=true
export FEATURE_PRD_GENERATOR=true
export FEATURE_ITERATIVE_ANALYSIS=true
export FEATURE_LIVE_ANALYSIS=true
export FEATURE_CHAT=true
export FEATURE_ANALYTICS=true
export FEATURE_VERSION_HISTORY=true
export FEATURE_CODEBASE_PROFILE=true
export FEATURE_THREAT_CANVAS=true
export FEATURE_REVIEW_REQUESTS=true

# ---- Phase 5: Kill Stale Processes ----
echo "$(json_status "running" "Cleaning stale processes" "cleanup")" >&2

for port in 8000 3000; do
    pids=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
done

# ---- Phase 6: Start Backend ----
echo "$(json_status "running" "Starting backend" "backend")" >&2

cd "$REPO_ROOT"
source .venv/bin/activate

python -m uvicorn context_graph.api.main:app \
    --host 0.0.0.0 --port 8000 \
    > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

# Wait for backend health
BACKEND_READY=false
for i in $(seq 1 20); do
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        BACKEND_READY=true
        break
    fi
    sleep 1
done

if [ "$BACKEND_READY" != "true" ]; then
    echo "$(json_status "error" "Backend failed to respond on port 8000 within 20s" "backend")" >&2
    kill $BACKEND_PID 2>/dev/null || true
    exit 2
fi

# ---- Phase 7: Start Frontend ----
echo "$(json_status "running" "Starting frontend" "frontend")" >&2

if [ -d "$FRONTEND_DIR" ] && command -v npm &>/dev/null; then
    cd "$FRONTEND_DIR"
    npm run dev -- --port 3000 > "$LOG_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    sleep 3
    cd "$REPO_ROOT"
fi

# ---- Final Report ----
echo "$(json_status "ready" "All services running" "complete")" >&2
json_report "ready"
