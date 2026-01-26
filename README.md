# Intently

> **Multi-Dimensional Product Analysis** — Bridge PRDs to code with comprehensive review across security, privacy, compliance, engineering, and architecture dimensions. Enable proactive analysis before implementation.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Table of Contents

- [Overview](#overview)
- [Key Concepts](#key-concepts)
- [Analysis Dimensions](#analysis-dimensions)
- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [CLI Commands](#cli-commands)
- [Supported Languages](#supported-languages)
- [GitHub Integration](#github-integration)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────────────────┐
│   PRD Parser    │────▶│  Context Graph   │────▶│    Multi-Dimensional Review     │
│ (Intent Extract)│     │   (Knowledge)    │     ├─────────────────────────────────┤
└─────────────────┘     └──────────────────┘     │ Security │ Privacy │ Compliance │
                               ▲                 │ Engineering │ Architecture      │
                               │                 └─────────────────────────────────┘
                        ┌──────────────┐                        │
                        │  Codebase    │                        ▼
                        │  Analyzer    │              ┌─────────────────┐
                        │  (State)     │              │   PM Tools      │
                        └──────────────┘              │ PRD Generation  │
                                                      │ Quality Scoring │
                                                      └─────────────────┘
```

## Key Concepts

- **Intent**: What the PRD wants to achieve (features, data flows, user interactions)
- **State**: Current codebase reality (APIs, data models, patterns, dependencies)
- **Delta**: The gap between intent and state that requires implementation
- **Dimensions**: Five analysis perspectives (Security, Privacy, Compliance, Engineering, Architecture)
- **Findings**: Issues discovered across any dimension with severity and remediation guidance

## Analysis Dimensions

Intently runs parallel analysis across five dimensions:

| Dimension | Frameworks | What's Analyzed |
|-----------|------------|-----------------|
| **Security** | STRIDE, OWASP Top 10 | Threats, vulnerabilities, trust boundaries, attack vectors |
| **Privacy** | LINDDUN, GDPR/CCPA | Data flows, PII handling, consent, data retention |
| **Compliance** | SOC 2, HIPAA, PCI-DSS | Regulatory requirements, audit controls, certifications |
| **Engineering** | Best practices | Code quality, testing gaps, error handling, maintainability |
| **Architecture** | Design patterns | API design, dependencies, scalability, integration points |

## Features

### Core Analysis
- 📄 **PRD Parsing**: Extract structured intent from product requirements
- 🔍 **Codebase Analysis**: Map code patterns across multiple languages
- 🕸️ **Context Graph**: Build knowledge graph of entities and relationships
- ⚡ **Impact Analysis**: Understand how changes affect system posture
- 🎯 **Multi-Dimensional Review**: Parallel analysis across all five dimensions

### PM Tools
- 📝 **PRD Generator**: Generate PRDs from existing codebases
- ✏️ **PRD Change Suggestions**: Diff-style recommendations for PRD improvements
- 📊 **Quality Scoring**: Assess PRD completeness and readiness
- ⏱️ **Effort Estimation**: Time and complexity estimates for implementation
- 📚 **Bulk Analysis**: Analyze multiple PRDs at once
- 🧠 **Pattern Learning**: System improves from expert feedback over time

### Collaboration
- 👥 **Team Queue**: Assign findings to teams for remediation
- 💬 **Comments**: Threaded discussions on findings
- ✅ **Validation**: Expert review and approval workflows

## Quick Start

```bash
# 1. Clone and navigate to the project folder
git clone https://github.com/packtman/Intently.git
cd Intently

# 2. Verify you're in the right directory (should see pyproject.toml)
ls pyproject.toml   # If this fails, you're in the wrong directory

# 3. Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# 4. Upgrade pip/setuptools and install the package
pip install --upgrade pip setuptools wheel
pip install -e .

# 5. Set API key (OpenAI or Anthropic)
export OPENAI_API_KEY="sk-..."

# 6. Run a multi-dimensional review
context-graph review examples/sample-prd.md /path/to/codebase --llm

# 7. Or start the web UI
./scripts/start-servers.sh   # Opens at http://localhost:3000
```

**Getting "-e option requires 1 argument" error?** You're in the wrong directory. Make sure `pyproject.toml` exists in your current folder (`ls pyproject.toml`).

For detailed setup including the Desktop app, see [Installation](#installation).

## Architecture

### 1. PRD Parser (`src/parsers/`)
Extracts structured intent from various document formats:
- Markdown
- Plain text
- Notion (via API)
- Confluence (via API)

### 2. Codebase Analyzer (`src/analyzers/`)
Maps the current state of the codebase:
- API endpoints and their auth requirements
- Data models and sensitive fields
- Dependencies and integration points
- Code patterns and architecture

### 3. Context Graph (`src/code_graph/`)
Knowledge graph storing:
- Entities (Users, Data, APIs, Components)
- Relationships (accesses, owns, trusts, flows_to)
- Properties (auth_required, encryption, pii, public)

### 4. Review Engine (`src/security/`)
Multi-dimensional analysis engine:
- **Security**: STRIDE, OWASP Top 10, threat modeling
- **Privacy**: LINDDUN, data flow analysis, PII detection
- **Compliance**: SOC 2, HIPAA, PCI-DSS mapping
- **Engineering**: Code quality, testing coverage, error handling
- **Architecture**: Design patterns, scalability, dependencies

### 5. PM Tools (`src/pm/`)
Product management utilities:
- PRD generation from codebases
- Quality scoring and readiness assessment
- Effort estimation
- Change suggestions with diff view

## Configuration

```yaml
# context-graph.yaml
llm:
  provider: anthropic  # or openai
  model: claude-sonnet-4-20250514

codebase:
  languages: [python, typescript, kotlin]
  exclude: [node_modules, __pycache__, .git]

# Analysis dimensions to run
dimensions:
  security: true      # STRIDE, OWASP Top 10
  privacy: true       # LINDDUN, GDPR/CCPA
  compliance: true    # SOC 2, HIPAA, PCI-DSS
  engineering: true   # Code quality, testing
  architecture: true  # Design patterns, dependencies

severity_threshold: medium  # low, medium, high, critical
```

## Installation

### Prerequisites

- **Python 3.10 or higher** (required)
  ```bash
  python3 --version   # Must be 3.10+
  ```
  If your version is older, install Python 3.12:
  - **macOS:** `brew install python@3.12`
  - **Ubuntu:** `sudo apt install python3.12 python3.12-venv`
  - **Windows:** Download from https://python.org/downloads/
  
- **pip** - Usually included with Python
- **Node.js 18+** (optional) - Only needed for web UI or desktop app

### 1. Clone the Repository

```bash
git clone https://github.com/packtman/Intently.git
cd Intently
```

### 2. Create a Virtual Environment (Recommended)

Using a virtual environment keeps dependencies isolated and prevents conflicts:

```bash
# Create virtual environment (use python3.12 if python3 is too old)
python3 -m venv .venv
# OR if you installed a newer Python separately:
# python3.12 -m venv .venv

# Activate it
source .venv/bin/activate      # macOS/Linux
# OR
.venv\Scripts\activate         # Windows (Command Prompt)
# OR
.venv\Scripts\Activate.ps1     # Windows (PowerShell)
```

**Note:** You'll need to activate the virtual environment each time you open a new terminal.

**Python version error?** If you get "requires Python >=3.10", see [Troubleshooting](docs/TROUBLESHOOTING.md#requires-a-different-python-39x-not-in-310).

### 3. Install the Python Package

**First, verify you're in the correct directory:**
```bash
ls pyproject.toml
```
If this command shows "No such file", you're in the wrong directory. Navigate to where you cloned the repo.

**Then install:**
```bash
# Upgrade pip and setuptools first (required for editable installs)
pip install --upgrade pip setuptools wheel

# Install in "editable" mode (allows code changes without reinstalling)
pip install -e .
```

This installs the `context-graph` CLI command and all Python dependencies.

> **Common error:** `-e option requires 1 argument` means pip can't find `pyproject.toml` in your current directory.

**Verify installation:**
```bash
context-graph --help
```

You should see the list of available commands.

**Having trouble?** See [Troubleshooting](docs/TROUBLESHOOTING.md) for common installation issues like "command not found" or pip errors.

### 4. Set Environment Variables

**Required for AI-based findings and chat functionality:**

You need at least one of these API keys set as environment variables:

```bash
# Option 1: OpenAI (recommended for chat)
export OPENAI_API_KEY="sk-..."

# Option 2: Anthropic (alternative)
export ANTHROPIC_API_KEY="sk-ant-..."

# Option 3: Both (for parallel analysis and consensus)
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Where to set these:**

1. **For terminal/CLI usage:**
   ```bash
   # In your current terminal session
   export OPENAI_API_KEY="sk-your-key-here"
   
   # Or add to your shell profile (~/.zshrc, ~/.bashrc, etc.)
   echo 'export OPENAI_API_KEY="sk-your-key-here"' >> ~/.zshrc
   source ~/.zshrc
   ```

2. **For web server (context-graph serve):**
   ```bash
   # Set before starting the server
   export OPENAI_API_KEY="sk-your-key-here"
   context-graph serve
   ```

3. **For development (VS Code/Cursor):**
   - Create a `.env` file in the project root (not committed to git)
   - Add: `OPENAI_API_KEY=sk-your-key-here`
   - Or set in your IDE's environment variables

**Get API Keys:**
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/settings/keys

**Note:** Without API keys, the system will fall back to pattern-based analysis only. AI-based findings and chat require valid API keys.

### 5. Run CLI Review

```bash
# Parse a PRD and analyze against codebase
context-graph review examples/sample-prd.md /path/to/your/codebase --output report.md

# Use LLM for deeper analysis
context-graph review examples/sample-prd.md /path/to/codebase --llm -o report.md
```

### 6. Start Web UI (Optional)

**Option A: Quick Start (using start script)**

```bash
# Start both backend and frontend with one command
./scripts/start-servers.sh
```

Open http://localhost:3000 to access the dashboard.

**Option B: Manual Start**

```bash
# Terminal 1: Start backend
context-graph serve

# Terminal 2: Start frontend
cd frontend
npm install
npm run dev
```

### 7. Desktop App (Optional)

For a native desktop experience with local file system integration:

```bash
# From the repo root
cd desktop

# Install dependencies
npm install

# Run in development mode
npm run electron:dev

# Or build for production
npm run electron:build
```

**First-time setup:** Go to Settings and configure:
- **Intently Path**: Path to this repo root (e.g., `/path/to/Intently`)
- **Python Path**: Path to your python3 or venv (e.g., `.venv/bin/python`)
- **API Keys**: OpenAI and/or Anthropic keys

**Desktop App Features:**
- Native file/folder selection dialogs
- Auto-start/stop Python backend
- PRD Generator from codebases
- Keyboard shortcuts (Cmd+N: New Review, Cmd+O: Open PRD)
- Works offline (after initial setup)

## CLI Commands

```bash
# Full security review (local codebase)
context-graph review <prd-file> <codebase-path> [--output FILE] [--llm]

# Full security review (GitHub repo)
context-graph review <prd-file> owner/repo [--branch main] [--llm]
context-graph review <prd-file> https://github.com/owner/repo [--pr 123] [--llm]

# Parse PRD only (show extracted intent)
context-graph parse <prd-file>

# Analyze codebase (local or GitHub)
context-graph analyze <codebase-path> [--lang auto]  # Auto-detect all languages
context-graph analyze owner/repo --lang python --lang typescript
context-graph analyze owner/repo --branch develop

# Start web server
context-graph serve [--host 0.0.0.0] [--port 8000] [--reload]
```

## Supported Languages

| Language | Extensions | What's Analyzed |
|----------|------------|-----------------|
| Python | `.py` | Classes, functions, Flask/FastAPI routes, SQLAlchemy models |
| Kotlin | `.kt`, `.kts` | Classes, Spring endpoints, data classes |
| TypeScript/JS | `.ts`, `.tsx`, `.js`, `.jsx` | Express/NestJS routes, TypeORM models, interfaces |
| YAML | `.yaml`, `.yml` | OpenAPI specs, configs, security settings |
| JSON | `.json` | JSON Schema definitions, config files |

Use `--lang auto` to detect and analyze all supported languages automatically.

## GitHub Integration

Analyze repositories directly from GitHub:

```bash
# Public repos - just use owner/repo
context-graph analyze pallets/flask
context-graph review prd.md fastapi/fastapi --llm

# Specific branch
context-graph review prd.md owner/repo --branch develop

# Pull request analysis
context-graph review prd.md owner/repo --pr 123

# Private repos - set GITHUB_TOKEN
export GITHUB_TOKEN="ghp_..."
context-graph review prd.md private-org/private-repo --llm
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/reviews` | Create new security review |
| GET | `/api/reviews/{id}/status` | Get review status |
| GET | `/api/reviews/{id}` | Get review results (JSON) |
| GET | `/api/reviews/{id}/dashboard` | Get dashboard data |
| GET | `/api/reviews/{id}/markdown` | Get markdown report |
| POST | `/api/parse-prd` | Parse PRD only |
| POST | `/api/analyze-codebase` | Analyze codebase only |

## Project Structure

```
Intently/
├── src/context_graph/     # Python backend
│   ├── core/              # Core models and graph
│   ├── parsers/           # PRD parsers (Markdown, Notion, GDocs)
│   ├── analyzers/         # Codebase analyzers (Python, Kotlin, TS)
│   ├── llm/               # LLM providers (OpenAI, Anthropic)
│   ├── security/          # Security review engine
│   ├── reports/           # Report generators
│   ├── api/               # FastAPI web API
│   └── cli.py             # CLI interface
├── frontend/              # React web dashboard
├── desktop/               # Electron desktop app
│   ├── electron/          # Main process (backend management)
│   ├── src/               # Desktop-specific React UI
│   └── package.json       # Desktop dependencies
├── scripts/               # Server startup scripts
├── examples/              # Sample PRDs
├── docs/                  # Documentation
└── context-graph.yaml     # Configuration
```

## Documentation

| Document | Description |
|----------|-------------|
| [Frontend Options](docs/FRONTEND_OPTIONS.md) | Compare Web Dashboard vs Desktop App |
| [Desktop App](desktop/README.md) | Native Electron app setup & usage |
| [Web Dashboard](frontend/README.md) | Browser-based dashboard setup |
| [Storage Configuration](docs/STORAGE_CONFIGURATION.md) | Configure SQLite persistent storage |
| [Iterative Analysis](docs/ITERATIVE_ANALYSIS.md) | Multi-round LLM analysis for comprehensive coverage |
| [API Keys Setup](API_KEYS_SETUP.md) | Configure OpenAI & Anthropic keys |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues & solutions |

## Contributing

We welcome contributions! Here's how to get started:

### Development Setup

```bash
# 1. Fork and clone the repo
git clone https://github.com/YOUR_USERNAME/Intently.git
cd Intently

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# OR: .venv\Scripts\activate  # Windows

# 3. Upgrade pip/setuptools and install with dev dependencies
pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"

# 4. Verify installation
context-graph --help
pytest  # Run tests

# 5. (Optional) Frontend web dashboard
cd frontend && npm install

# 6. (Optional) Desktop app
cd desktop && npm install
```

### Contribution Steps

1. **Fork the repository** and clone locally (see above)
2. **Create a feature branch**: `git checkout -b my-feature`
3. **Make your changes** and add tests
4. **Run tests**: `pytest`
5. **Submit a pull request**

### Code Quality

```bash
# Format code
black src/

# Lint
ruff check src/

# Type checking
mypy src/
```

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Intently</strong> — Multi-Dimensional Product Analysis
</p>
