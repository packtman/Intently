#!/usr/bin/env bash
set -uo pipefail

# =============================================================================
# agent_test.sh — Structured Test Runner for AI Agents
#
# Runs all test suites and outputs machine-readable JSON results including
# exact file paths, line numbers, and failure messages for self-correction.
#
# Usage:
#   ./scripts/agent_test.sh              # Run all tests
#   ./scripts/agent_test.sh --unit       # Python unit tests only
#   ./scripts/agent_test.sh --boundary   # Boundary enforcement only
#   ./scripts/agent_test.sh --frontend   # Frontend tests only
#   ./scripts/agent_test.sh --quick      # Boundary + lint only (no services needed)
#
# Output: JSON report to stdout. Human-readable progress to stderr.
# Exit codes:
#   0 - All tests pass
#   1 - Test failures detected (details in JSON output)
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/frontend"
RESULTS_DIR="$REPO_ROOT/.agent_logs/test_results"

mkdir -p "$RESULTS_DIR"

MODE="${1:-all}"
OVERALL_STATUS="pass"
RESULTS=()

# Helper to add a test result
add_result() {
    local suite="$1"
    local status="$2"
    local file="$3"
    RESULTS+=("{\"suite\":\"$suite\",\"status\":\"$status\",\"results_file\":\"$file\"}")
    if [ "$status" = "fail" ]; then
        OVERALL_STATUS="fail"
    fi
}

# ---- Boundary Enforcement ----
run_boundary_check() {
    echo "Running boundary enforcement..." >&2
    local outfile="$RESULTS_DIR/boundary.json"

    cd "$REPO_ROOT"
    if [ -d ".venv" ]; then
        source .venv/bin/activate 2>/dev/null || true
    fi

    python3 scripts/enforce_boundaries.py --json > "$outfile" 2>/dev/null
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        add_result "boundary_enforcement" "pass" "$outfile"
    else
        add_result "boundary_enforcement" "fail" "$outfile"
    fi
    echo "  Boundary check: exit_code=$exit_code" >&2
}

# ---- Python Lint (ruff) ----
run_python_lint() {
    echo "Running Python lint (ruff)..." >&2
    local outfile="$RESULTS_DIR/ruff.json"

    cd "$REPO_ROOT"
    if [ -d ".venv" ]; then
        source .venv/bin/activate 2>/dev/null || true
    fi

    if command -v ruff &>/dev/null; then
        ruff check src/ --output-format json > "$outfile" 2>/dev/null
        local exit_code=$?
        if [ $exit_code -eq 0 ]; then
            add_result "python_lint" "pass" "$outfile"
        else
            add_result "python_lint" "fail" "$outfile"
        fi
        echo "  Ruff lint: exit_code=$exit_code" >&2
    else
        echo '{"status":"skipped","reason":"ruff not installed"}' > "$outfile"
        add_result "python_lint" "skipped" "$outfile"
        echo "  Ruff lint: skipped (not installed)" >&2
    fi
}

# ---- Python Unit Tests (pytest) ----
run_python_tests() {
    echo "Running Python tests (pytest)..." >&2
    local outfile="$RESULTS_DIR/pytest.json"

    cd "$REPO_ROOT"
    if [ -d ".venv" ]; then
        source .venv/bin/activate 2>/dev/null || true
    fi

    if command -v pytest &>/dev/null; then
        pytest src/context_graph/tests/ \
            --tb=short \
            --no-header \
            -q \
            --json-report \
            --json-report-file="$outfile" \
            2>"$RESULTS_DIR/pytest_stderr.log" || true

        # Fallback if json-report plugin not available
        if [ ! -f "$outfile" ] || [ ! -s "$outfile" ]; then
            pytest src/context_graph/tests/ \
                --tb=line \
                --no-header \
                -q \
                2>&1 | python3 -c "
import sys, json, re

lines = sys.stdin.read()
failures = []
for match in re.finditer(r'FAILED\s+(\S+)::(\S+)', lines):
    failures.append({'file': match.group(1), 'test': match.group(2)})

passed = len(re.findall(r'passed', lines))
failed = len(failures)

result = {
    'summary': {'passed': passed, 'failed': failed, 'total': passed + failed},
    'failures': failures,
    'raw_output': lines[-2000:] if len(lines) > 2000 else lines
}
json.dump(result, sys.stdout, indent=2)
" > "$outfile" 2>/dev/null || echo '{"status":"error","message":"pytest parsing failed"}' > "$outfile"
        fi

        if python3 -c "import json; d=json.load(open('$outfile')); exit(0 if d.get('summary',{}).get('failed',1)==0 else 1)" 2>/dev/null; then
            add_result "python_tests" "pass" "$outfile"
        else
            add_result "python_tests" "fail" "$outfile"
        fi
    else
        echo '{"status":"skipped","reason":"pytest not installed"}' > "$outfile"
        add_result "python_tests" "skipped" "$outfile"
        echo "  Pytest: skipped (not installed)" >&2
    fi
}

# ---- Frontend Tests (vitest) ----
run_frontend_tests() {
    echo "Running frontend tests (vitest)..." >&2
    local outfile="$RESULTS_DIR/frontend.json"

    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        echo '{"status":"skipped","reason":"node_modules not installed"}' > "$outfile"
        add_result "frontend_tests" "skipped" "$outfile"
        echo "  Frontend tests: skipped (no node_modules)" >&2
        return
    fi

    cd "$FRONTEND_DIR"
    npx vitest run --reporter=json > "$outfile" 2>"$RESULTS_DIR/frontend_stderr.log"
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        add_result "frontend_tests" "pass" "$outfile"
    else
        add_result "frontend_tests" "fail" "$outfile"
    fi
    echo "  Frontend tests: exit_code=$exit_code" >&2
    cd "$REPO_ROOT"
}

# ---- Execute based on mode ----
case "$MODE" in
    --quick)
        run_boundary_check
        run_python_lint
        ;;
    --boundary)
        run_boundary_check
        ;;
    --unit)
        run_python_tests
        ;;
    --frontend)
        run_frontend_tests
        ;;
    --lint)
        run_python_lint
        ;;
    all|*)
        run_boundary_check
        run_python_lint
        run_python_tests
        run_frontend_tests
        ;;
esac

# ---- Generate Final Report ----
RESULTS_JSON=$(printf '%s,' "${RESULTS[@]}" | sed 's/,$//')

cat <<EOF
{
  "overall_status": "$OVERALL_STATUS",
  "mode": "$MODE",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "results_directory": "$RESULTS_DIR",
  "suites": [$RESULTS_JSON]
}
EOF
