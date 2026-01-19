#!/bin/bash

# Start Context Graph servers
# This script ensures clean startup by killing existing processes first

CONTEXT_GRAPH_DIR="/Users/dipenshah/Documents/Context Graph/Context graph"
FRONTEND_DIR="$CONTEXT_GRAPH_DIR/frontend"

# Function to kill processes on a port
kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "  Killing processes on port $port: $pids"
        echo "$pids" | xargs kill -9 2>/dev/null
        return 0
    fi
    return 1
}

# Function to wait for port to be free
wait_for_port_free() {
    local port=$1
    local max_attempts=5
    for i in $(seq 1 $max_attempts); do
        if ! lsof -ti:$port > /dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    return 1
}

echo "=========================================="
echo "  Context Graph Server Startup"
echo "=========================================="
echo ""

echo "Step 1: Stopping existing processes..."
kill_port 8000 || echo "  Port 8000 is free"
kill_port 3000 || echo "  Port 3000 is free"
kill_port 3001 || echo "  Port 3001 is free"

# Wait for ports to be released
echo ""
echo "Step 2: Waiting for ports to be released..."
wait_for_port_free 8000 && echo "  Port 8000 is ready" || echo "  Warning: Port 8000 may still be in use"
wait_for_port_free 3000 && echo "  Port 3000 is ready" || echo "  Warning: Port 3000 may still be in use"
echo ""

echo "Step 3: Starting Backend on port 8000..."
cd "$CONTEXT_GRAPH_DIR"
source .venv/bin/activate

# Verify Python version
PYTHON_VERSION=$(python --version 2>&1)
echo "  Using: $PYTHON_VERSION"

# PM Tool features only (from UNIFIED_PM_TOOL_VISION.md)
export FEATURE_PRD_CHANGES=true
export FEATURE_PRD_QUALITY_SCORING=true
export FEATURE_EFFORT_ESTIMATION=true
export FEATURE_EXPERT_ASSIST=true
export FEATURE_PM_PATTERN_LEARNING=true
export FEATURE_SIDE_BY_SIDE_DIFF=true
export FEATURE_PRD_SAVE_TO_FILE=true

# Bulk PRD Analysis (up to 20 parallel reviews)
export FEATURE_BULK_PRD_ANALYSIS=true
export BULK_PRD_MAX_FILES=20
export BULK_PRD_MAX_PARALLEL_REVIEWS=20
export BULK_PRD_CODEBASE_THRESHOLD=3
export FEATURE_BULK_PRD_SMART_CODEBASE_DEFAULT=true

# PRD Generator (generate PRDs from codebases)
export FEATURE_PRD_GENERATOR=true
export PRD_GENERATOR_MAX_FILES=5000

echo "  Feature flags enabled:"
echo "    - PRD Changes"
echo "    - PRD Quality Scoring"
echo "    - Effort Estimation"
echo "    - Expert Assist"
echo "    - PM Pattern Learning"
echo "    - Side-by-Side Diff"
echo "    - PRD Save-to-File"
echo "    - Bulk PRD Analysis (up to 20 files, 20 parallel workers)"
echo "    - PRD Generator (generate PRDs from codebases)"
echo ""

python -m uvicorn context_graph.api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to be ready
echo "  Waiting for backend to start..."
for i in {1..15}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "  ✓ Backend is ready!"
        break
    fi
    if [ $i -eq 15 ]; then
        echo "  ⚠ Backend may not have started correctly"
    fi
    sleep 1
done

echo ""
echo "Step 4: Starting Frontend on port 3000..."
cd "$FRONTEND_DIR"
npm run dev -- --port 3000 &
FRONTEND_PID=$!

sleep 3
echo ""
echo "=========================================="
echo "  Servers Running"
echo "=========================================="
echo ""
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo ""
echo "  Press Ctrl+C to stop both servers"
echo "=========================================="
echo ""

# Wait for Ctrl+C
trap "echo ''; echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Servers stopped.'; exit" INT
wait
