# Intently Desktop

> **Native desktop application for multi-dimensional product analysis**

A cross-platform Electron application that brings the full power of Intently's analysis pipeline to your desktop. Analyze PRDs against codebases across security, privacy, compliance, engineering, and architecture dimensions with native file system integration, automatic backend management, and offline capability.

---

## Table of Contents

- [Overview](#overview)
- [Desktop vs Web](#desktop-vs-web)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Architecture](#architecture)
- [Development](#development)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Overview

Intently Desktop provides a native application experience for running comprehensive product security reviews. It manages the Python backend automatically and provides seamless integration with your local file system.

```
┌────────────────────────────────────────────────────────────────┐
│                     Intently Desktop                           │
├────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   Parse     │───▶│   Analyze   │───▶│   Review    │        │
│  │    PRD      │    │  Codebase   │    │  Security   │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                  │                  │                │
│         └──────────────────┴──────────────────┘                │
│                            │                                   │
│                    ┌───────▼───────┐                          │
│                    │  AI Analysis  │                          │
│                    │ OpenAI/Claude │                          │
│                    └───────────────┘                          │
└────────────────────────────────────────────────────────────────┘
```

---

## Desktop vs Web

Intently offers two frontend options. Choose based on your workflow:

| Feature | Desktop App | Web Dashboard |
|---------|-------------|---------------|
| **Installation** | Native app (macOS/Windows/Linux) | Browser-based |
| **Backend Management** | Auto-starts Python backend | Requires manual backend start |
| **File Access** | Native file/folder dialogs | Manual path entry |
| **GitHub Integration** | Built-in repo download | Via backend API |
| **Offline Support** | Works offline after setup | Requires network |
| **Notifications** | Native OS notifications | Browser notifications |
| **Keyboard Shortcuts** | Full native shortcuts | Limited |
| **Best For** | Daily driver, power users | Quick access, server deployment |

### When to Use Desktop

- You want a dedicated app for security reviews
- You prefer native file dialogs for selecting PRDs and codebases
- You want the backend to start/stop automatically
- You work offline frequently

### When to Use Web

- You're running Intently on a server
- Multiple team members need access via browser
- You prefer a lighter-weight solution
- You already have the backend running separately

---

## Features

### Core Analysis

- **Multi-Dimensional Security Review**
  - Security (STRIDE, OWASP Top 10)
  - Privacy (LINDDUN, GDPR/CCPA)
  - Compliance (SOC 2, HIPAA, PCI-DSS)
  - Engineering (code quality, testing)
  - Architecture (API design, dependencies)

- **AI-Powered Analysis**
  - OpenAI GPT-4 integration
  - Anthropic Claude integration
  - Parallel analysis with consensus

- **Multi-Language Support**
  - Python, Kotlin, TypeScript/JavaScript
  - YAML/OpenAPI, JSON schemas

### Desktop-Specific

- **Native File System Integration**
  - File picker for PRDs (Markdown, Text)
  - Directory picker for codebases
  - Save reports to any location

- **Automatic Backend Management**
  - Start/stop Python backend from the app
  - Health monitoring with auto-reconnect
  - Virtual environment detection

- **GitHub Repository Download**
  - Paste GitHub URL to analyze
  - Automatic tarball download (bypasses git clone)
  - Cached repos for quick re-analysis

- **PRD Generator**
  - Generate PRDs from existing codebases
  - AI-powered documentation extraction

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Node.js | 18+ | For building the desktop app |
| Python | 3.10+ | For the analysis backend |
| npm | 9+ | Package manager |

### API Keys (Optional but Recommended)

For AI-powered analysis, you need at least one:

- **OpenAI**: [Get API Key](https://platform.openai.com/api-keys)
- **Anthropic**: [Get API Key](https://console.anthropic.com/settings/keys)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/packtman/Intently.git
cd Intently
```

### 2. Install Python Backend

```bash
# Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .
```

### 3. Install Desktop App Dependencies

```bash
cd desktop
npm install
```

### 4. Run the Desktop App

```bash
# Development mode (with hot reload)
npm run electron:dev

# Or build for production
npm run electron:build
```

---

## Configuration

On first launch, open **Settings** (⌘/Ctrl + ,) to configure:

### Required Settings

| Setting | Description | Example |
|---------|-------------|---------|
| **Intently Path** | Path to the project root | `/Users/you/intently` |
| **Python Path** | Python executable | `python3` or `.venv/bin/python` |

### Optional Settings

| Setting | Description |
|---------|-------------|
| **OpenAI API Key** | For GPT-4 powered analysis |
| **Anthropic API Key** | For Claude powered analysis |
| **Auto-start Backend** | Start backend when app launches |

---

## Usage

### Creating a New Review

1. Click **New Review** or press ⌘/Ctrl + N
2. **Step 1 - PRD**: Paste content or click "Select File" to load a Markdown PRD
3. **Step 2 - Codebase**: Browse to select a local directory, or paste a GitHub URL
4. **Step 3 - Config**: Choose analysis dimensions and enable AI analysis
5. **Step 4 - Review**: Confirm and start the review

### Analyzing a GitHub Repository

1. In the codebase step, paste a GitHub URL:
   - `https://github.com/owner/repo`
   - `owner/repo`
2. The app automatically downloads and caches the repository
3. Proceed with analysis as normal

### Viewing Results

- **Dashboard**: Overview of all reviews with risk ratings
- **Review Detail**: Deep dive into findings by dimension
- **Export**: Generate Markdown reports for sharing

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Electron App                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────┐          ┌───────────────────┐              │
│  │   Main Process    │◀── IPC ──│  Renderer Process │              │
│  │   (Node.js)       │          │  (React + Vite)   │              │
│  └─────────┬─────────┘          └─────────┬─────────┘              │
│            │                              │                         │
│            │ spawn                        │ HTTP                    │
│            ▼                              ▼                         │
│  ┌───────────────────┐          ┌───────────────────┐              │
│  │  Python Backend   │◀─────────│   FastAPI Server  │              │
│  │  (child process)  │          │   localhost:8000  │              │
│  └───────────────────┘          └───────────────────┘              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| Main Process | Electron + Node.js | Window management, IPC, process spawning |
| Renderer | React 18 + TypeScript | User interface |
| Styling | Tailwind CSS | Dark theme UI |
| State | React Query | Server state management |
| Backend | FastAPI + Python | Security analysis engine |
| AI | OpenAI / Anthropic | LLM-powered analysis |

---

## Development

### Scripts

```bash
# Start development mode (Vite + Electron with hot reload)
npm run electron:dev

# Build Electron main/preload scripts only
npm run build:electron

# Build production app
npm run electron:build

# Run Vite dev server only (for UI development)
npm run dev

# Run tests
npm test
```

### Project Structure

```
desktop/
├── electron/
│   ├── main.ts          # Electron main process
│   └── preload.ts       # IPC bridge to renderer
├── src/
│   ├── components/      # React components
│   │   ├── collaboration/   # Team features
│   │   ├── pm/              # PM tools
│   │   └── security/        # Security visualizations
│   ├── pages/           # Route pages
│   ├── hooks/           # React hooks
│   ├── services/        # API client
│   └── types/           # TypeScript definitions
├── public/              # Static assets
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| ⌘/Ctrl + N | New Review |
| ⌘/Ctrl + O | Open PRD File |
| ⌘/Ctrl + Shift + O | Open Codebase Directory |
| ⌘/Ctrl + E | Export Report |
| ⌘/Ctrl + , | Open Settings |
| ⌘/Ctrl + R | Reload Window |

---

## Troubleshooting

### Backend Won't Start

1. **Check Intently Path**
   - Go to Settings → Verify the path points to the project root
   - The path should contain `src/context_graph/cli.py`

2. **Check Python Path**
   - Verify Python 3.10+ is installed: `python3 --version`
   - If using a virtual environment, point to `.venv/bin/python`

3. **Check Dependencies**
   ```bash
   cd /path/to/intently
   pip install -e .
   ```

### AI Analysis Not Working

1. Verify API keys are configured in Settings
2. Check that keys are valid and have credits
3. Ensure "AI-Powered Analysis" is enabled when creating a review

### Build Errors

```bash
# Clean install
rm -rf node_modules package-lock.json
npm install

# Clear build cache
rm -rf dist dist-electron release
```

### App Won't Launch (macOS)

If you see "app is damaged" error:
```bash
xattr -cr /Applications/Intently.app
```

---

## License

MIT License - see [LICENSE](../LICENSE) for details.

---

<p align="center">
  <strong>Intently</strong> — Multi-Dimensional Product Analysis
</p>
