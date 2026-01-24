# Context Graph for Security Reviews

A semantic security analysis pipeline that bridges Product Requirement Documents (PRDs) to code impact analysis, enabling proactive security reviews before implementation.

## Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   PRD Parser    │────▶│  Context Graph   │────▶│ Security Review │
│ (Intent Extract)│     │   (Knowledge)    │     │    Engine       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               ▲
                               │
                        ┌──────────────┐
                        │  Codebase    │
                        │  Analyzer    │
                        │ (State)      │
                        └──────────────┘
```

## Key Concepts

- **Intent**: What the PRD wants to achieve (features, data flows, user interactions)
- **State**: Current codebase reality (APIs, data models, auth patterns, trust boundaries)
- **Delta**: The gap between intent and state that requires implementation
- **Security Surface**: Attack vectors, trust boundaries, and risk areas in the delta

## Features

- 📄 **PRD Parsing**: Extract structured intent from product requirements
- 🔍 **Codebase Analysis**: Map existing security-relevant patterns
- 🕸️ **Context Graph**: Build knowledge graph of entities and relationships
- ⚡ **Impact Analysis**: Understand how changes affect security posture
- 🛡️ **Security Review**: Automated threat modeling on proposed changes

## Installation

```bash
cd "Context graph"
pip install -e .
```

## Quick Start

```bash
# Analyze a PRD against a codebase
context-graph review --prd ./docs/feature.md --codebase ./src

# Generate security report
context-graph report --format markdown --output security-review.md

# Interactive mode
context-graph interactive
```

## Architecture

### 1. PRD Parser (`src/parsers/`)
Extracts structured intent from various document formats:
- Markdown
- Plain text
- Notion (via API)
- Confluence (via API)

### 2. Codebase Analyzer (`src/analyzers/`)
Maps the current state of security-relevant code:
- API endpoints and their auth requirements
- Data models and sensitive fields
- Trust boundaries
- Existing security controls

### 3. Context Graph (`src/graph/`)
Neo4j-inspired knowledge graph storing:
- Entities (Users, Data, APIs, Components)
- Relationships (accesses, owns, trusts, flows_to)
- Security properties (auth_required, encryption, pii)

### 4. Security Review Engine (`src/security/`)
Applies security analysis frameworks:
- STRIDE threat modeling
- OWASP Top 10 pattern matching
- Custom security rules
- Trust boundary analysis

## Configuration

```yaml
# context-graph.yaml
llm:
  provider: anthropic  # or openai, local
  model: claude-sonnet-4-20250514

codebase:
  languages: [python, typescript]
  exclude: [node_modules, __pycache__, .git]

security:
  frameworks: [stride, owasp]
  severity_threshold: medium
```

## Quick Start

### 1. Install Python Package

```bash
cd "Context graph"
pip install -e .
```

### 2. Set Environment Variables

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

### 3. Run CLI Review

```bash
# Parse a PRD and analyze against codebase
context-graph review examples/sample-prd.md /path/to/your/codebase --output report.md

# Use LLM for deeper analysis
context-graph review examples/sample-prd.md /path/to/codebase --llm -o report.md
```

### 4. Start Web UI

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

### 5. Desktop App (Electron)

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

## License

MIT

