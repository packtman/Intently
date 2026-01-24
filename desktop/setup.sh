#!/bin/bash
# Intently Desktop Setup Script
# Run this once to set up both Python backend and Node.js frontend

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "  Intently Desktop Setup"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# --- Python Backend Setup ---
echo -e "${YELLOW}[1/4] Setting up Python backend...${NC}"
cd "$PROJECT_ROOT"

# Check if venv exists, create if not
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install/upgrade pip (with trusted hosts for corporate environments)
pip install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org

# Install project with all dependencies (includes python-dotenv)
echo "Installing Python dependencies..."
pip install -e . --trusted-host pypi.org --trusted-host files.pythonhosted.org

echo -e "${GREEN}✓ Python backend ready${NC}"
echo ""

# --- Node.js Frontend Setup ---
echo -e "${YELLOW}[2/4] Setting up Node.js frontend...${NC}"
cd "$SCRIPT_DIR"

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js not found. Please install Node.js 18+ first.${NC}"
    exit 1
fi

echo "Node.js version: $(node --version)"

# Install npm dependencies
echo "Installing npm dependencies..."
npm install

echo -e "${GREEN}✓ Node.js frontend ready${NC}"
echo ""

# --- Build Electron files ---
echo -e "${YELLOW}[3/4] Building Electron files...${NC}"
npm run build:electron

echo -e "${GREEN}✓ Electron build ready${NC}"
echo ""

# --- Configure settings ---
echo -e "${YELLOW}[4/4] Configuring default settings...${NC}"

# Create config directory if needed
CONFIG_DIR="$HOME/Library/Application Support/intently-desktop"
CONFIG_FILE="$CONFIG_DIR/config.json"

mkdir -p "$CONFIG_DIR"

# Only create config if it doesn't exist (don't overwrite user settings)
if [ ! -f "$CONFIG_FILE" ]; then
    cat > "$CONFIG_FILE" << EOF
{
  "contextGraphPath": "$PROJECT_ROOT",
  "pythonPath": "$PROJECT_ROOT/.venv/bin/python",
  "openaiApiKey": "",
  "anthropicApiKey": "",
  "autoStartBackend": false
}
EOF
    echo "Created default configuration at: $CONFIG_FILE"
else
    echo "Configuration already exists at: $CONFIG_FILE"
fi

echo -e "${GREEN}✓ Configuration ready${NC}"
echo ""

# --- Done ---
echo "========================================"
echo -e "${GREEN}  Setup Complete!${NC}"
echo "========================================"
echo ""
echo "To start the desktop app:"
echo "  cd \"$SCRIPT_DIR\""
echo "  npm run electron:dev"
echo ""
echo "The backend path is configured to:"
echo "  $PROJECT_ROOT"
echo ""
