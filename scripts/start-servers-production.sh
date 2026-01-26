#!/bin/bash

# Start Context Graph servers - PRODUCTION MODE
# This script is optimized for performance (no file watching, no auto-reload)

# Get the directory where this script is located, then go up one level to repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTEXT_GRAPH_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$CONTEXT_GRAPH_DIR/frontend"

echo "=== Starting Context Graph (Production Mode) ==="
echo ""

echo "Stopping any existing processes on ports 8000 and 3000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null
sleep 1

echo "Starting Backend on port 8000 (Production Mode - no hot reload)..."
cd "$CONTEXT_GRAPH_DIR"

# Check if virtual environment exists
if [ ! -f ".venv/bin/activate" ]; then
    echo "ERROR: Python virtual environment not found at .venv/"
    echo "Please set up the Python environment first:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -e ."
    exit 1
fi

source .venv/bin/activate

# Verify Python version
PYTHON_VERSION=$(python --version 2>&1)
echo "Using: $PYTHON_VERSION"

# Persistent Storage (SQLite)
export STORAGE_BACKEND=sqlite
export STORAGE_DB_PATH="$CONTEXT_GRAPH_DIR/data/reviews.db"
mkdir -p "$CONTEXT_GRAPH_DIR/data"

# PM Tool features only (from UNIFIED_PM_TOOL_VISION.md)
export FEATURE_PRD_CHANGES=true
export FEATURE_PRD_QUALITY_SCORING=true
export FEATURE_EFFORT_ESTIMATION=true
export FEATURE_EXPERT_ASSIST=true
export FEATURE_PM_PATTERN_LEARNING=true

echo "Storage: SQLite ($STORAGE_DB_PATH)"
echo "PM Tool features enabled"
echo ""

# PERFORMANCE: Run without --reload flag and with optimized workers
# --workers 2: Use 2 worker processes for better CPU utilization
# --limit-concurrency 100: Limit concurrent connections to prevent overload
# No --reload: Disables file watching which saves CPU
python -m uvicorn context_graph.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --limit-concurrency 100 \
    --log-level warning &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to start..."
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "Backend is ready!"
        break
    fi
    sleep 1
done

echo ""
echo "========================================"
echo "Backend running on http://localhost:8000"
echo "========================================"
echo ""
echo "Production mode features:"
echo "  ✓ No file watching (saves CPU)"
echo "  ✓ 2 worker processes"
echo "  ✓ Connection limits enabled"
echo "  ✓ Reduced logging (warnings only)"
echo ""
echo "Press Ctrl+C to stop the server"

# Wait for Ctrl+C
trap "kill $BACKEND_PID 2>/dev/null; echo 'Server stopped.'; exit" INT
wait
