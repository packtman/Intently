# Intently Desktop

A desktop application for running Intently security analysis locally. Built with Electron, React, and TypeScript.

## Features

- Full security review pipeline running locally on your machine
- PRD parsing with intent extraction
- Multi-language codebase analysis (Python, Kotlin, TypeScript, YAML, JSON)
- AI-powered analysis with OpenAI and Anthropic integration
- Security (STRIDE, OWASP), Privacy (LINDDUN), and Compliance (SOC2, HIPAA, PCI-DSS) analysis
- Native file system integration for selecting files and directories
- Beautiful dark theme UI with animations

## Prerequisites

1. Node.js 18+ and npm
2. Python 3.10+ with the Intently package installed
3. API keys for OpenAI and/or Anthropic (for AI-powered analysis)

## Installation

### 1. Install Dependencies

```bash
cd "context graph Desktop app"
npm install
```

### 2. Set Up Intently Python Package

Make sure the Intently Python package is installed:

```bash
cd "../Context graph"
pip install -e .
```

### 3. Configure the Application

On first launch, go to Settings and configure:

- **Intently Path**: Path to the Intently project directory
- **Python Path**: Path to Python 3.10+ executable (default: python3)
- **API Keys**: OpenAI and/or Anthropic API keys for AI analysis

## Development

### Run in Development Mode

```bash
npm run electron:dev
```

This starts both Vite dev server and Electron in development mode with hot reload.

### Build for Production

```bash
npm run electron:build
```

This creates platform-specific installers in the `release/` directory.

## Project Structure

```
context graph Desktop app/
|-- electron/              # Electron main process
|   |-- main.ts           # Main process entry
|   |-- preload.ts        # Preload script for IPC
|-- src/                   # React frontend
|   |-- components/       # Reusable components
|   |-- pages/            # Page components
|   |-- hooks/            # Custom React hooks
|   |-- services/         # API services
|   |-- types/            # TypeScript types
|-- public/               # Static assets
```

## Architecture

The desktop app communicates with the Intently Python backend:

1. **Electron Main Process**: Manages window, native menus, file dialogs, and spawns the Python backend
2. **Python Backend**: FastAPI server running locally (started automatically or manually)
3. **React Frontend**: User interface for creating and viewing security reviews

```
+------------------+     IPC      +------------------+
|  React Frontend  | <----------> |  Electron Main   |
+------------------+              +------------------+
        |                                  |
        | HTTP                             | spawn
        v                                  v
+------------------+              +------------------+
|  FastAPI Backend |              |  Python Process  |
+------------------+              +------------------+
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Cmd/Ctrl + N | New Review |
| Cmd/Ctrl + O | Open PRD File |
| Cmd/Ctrl + Shift + O | Open Codebase Directory |
| Cmd/Ctrl + E | Export Report |
| Cmd/Ctrl + , | Open Settings |

## Troubleshooting

### Backend Won't Start

1. Check that the Intently path is correctly configured in Settings
2. Verify Python 3.10+ is installed: `python3 --version`
3. Ensure the Intently package is installed: `pip list | grep context-graph`

### AI Analysis Not Working

1. Verify API keys are configured in Settings
2. Check that keys are valid and have sufficient credits
3. Enable LLM analysis when creating a review

### Build Errors

1. Clear node_modules and reinstall: `rm -rf node_modules && npm install`
2. Clear build cache: `rm -rf dist dist-electron release`

## License

MIT

