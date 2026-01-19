#!/bin/bash

# Start Context Graph servers - PRODUCTION MODE
# This script is optimized for performance (no file watching, no auto-reload)

CONTEXT_GRAPH_DIR="/Users/dipenshah/Documents/Context Graph/Context graph"
FRONTEND_DIR="$CONTEXT_GRAPH_DIR/frontend"

echo "=== Starting Context Graph (Production Mode) ==="
echo ""

echo "Stopping any existing processes on ports 8000 and 3000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null
sleep 1

echo "Starting Backend on port 8000 (Production Mode - no hot reload)..."
cd "$CONTEXT_GRAPH_DIR"
source .venv/bin/activate

# Verify Python version
PYTHON_VERSION=$(python --version 2>&1)
echo "Using: $PYTHON_VERSION"

# PM Tool features only (from UNIFIED_PM_TOOL_VISION.md)
export FEATURE_PRD_CHANGES=true
export FEATURE_PRD_QUALITY_SCORING=true
export FEATURE_EFFORT_ESTIMATION=true
export FEATURE_EXPERT_ASSIST=true
export FEATURE_PM_PATTERN_LEARNING=true

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
