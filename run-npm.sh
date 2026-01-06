#!/bin/bash
# Load NVM and run npm commands
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

# Use default or install if needed
if ! command -v node &> /dev/null; then
    echo "Installing Node.js LTS..."
    nvm install --lts
fi

nvm use --lts --default 2>/dev/null || nvm use node 2>/dev/null || nvm use --lts 2>/dev/null

# Run the command passed as arguments
exec "$@"

