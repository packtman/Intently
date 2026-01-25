# Contributing to Intently

Thank you for your interest in contributing to Intently — a multi-dimensional product analysis platform! This guide will help you get started.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)

## Development Setup

### Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.10+ | Backend analysis engine |
| Node.js | 18+ | Frontend builds |
| npm | 9+ | Package management |

### Clone and Install

```bash
# Clone the repository
git clone https://github.com/packtman/Intently.git
cd Intently

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python package in development mode
pip install -e ".[dev]"

# Install frontend dependencies
cd frontend && npm install && cd ..

# Install desktop app dependencies
cd desktop && npm install && cd ..
```

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required for AI-powered analysis (at least one)
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional: GitHub integration
GITHUB_TOKEN=ghp_your-token-here
```

## Project Structure

```
Intently/
├── src/context_graph/     # Python backend
│   ├── api/               # FastAPI routes
│   ├── analyzers/         # Language analyzers (Python, TS, Kotlin)
│   ├── llm/               # LLM providers (OpenAI, Anthropic)
│   ├── parsers/           # PRD parsers
│   ├── security/          # Multi-dimensional review engine
│   │                      # (Security, Privacy, Compliance, Engineering, Architecture)
│   ├── pm/                # PM tools (PRD generation, quality scoring, effort estimation)
│   ├── storage/           # Data persistence (SQLite)
│   └── cli.py             # CLI interface
├── frontend/              # React web dashboard
├── desktop/               # Electron desktop app
│   ├── electron/          # Main process
│   └── src/               # Desktop React UI
├── docs/                  # Documentation
├── scripts/               # Utility scripts
└── examples/              # Sample PRDs and codebases
```

## Development Workflow

### Running the Backend

```bash
# Development with auto-reload
context-graph serve --reload

# Or manually with uvicorn
uvicorn context_graph.api.main:app --reload --port 8000
```

### Running the Frontend

```bash
# Web dashboard
cd frontend
npm run dev  # Opens at http://localhost:5173

# Desktop app
cd desktop
npm run electron:dev
```

### Running Both Together

```bash
# Use the convenience script
./scripts/start-servers.sh
```

## Code Style

### Python

We use `black` for formatting, `ruff` for linting, and `mypy` for type checking.

```bash
# Format code
black src/

# Check linting
ruff check src/

# Fix linting issues automatically
ruff check src/ --fix

# Type checking
mypy src/
```

### TypeScript/JavaScript

```bash
cd frontend  # or desktop
npm run lint
npm run lint:fix
```

### Pre-commit Checks

Before committing, ensure:

1. Code is formatted (`black`, `prettier`)
2. No linting errors (`ruff`, `eslint`)
3. Tests pass (`pytest`, `npm test`)
4. Type checks pass (`mypy`)

## Testing

### Python Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=context_graph

# Run specific test file
pytest src/context_graph/tests/test_pm_features.py

# Run tests matching a pattern
pytest -k "test_quality"
```

### Frontend Tests

```bash
cd frontend  # or desktop
npm test

# Watch mode
npm run test:watch

# Coverage
npm run test:coverage
```

## Submitting Changes

### Pull Request Process

1. **Fork the repository** on GitHub
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** with clear, atomic commits
4. **Write/update tests** for your changes
5. **Run the full test suite** to ensure nothing is broken
6. **Push to your fork** and create a Pull Request

### Commit Messages

Use clear, descriptive commit messages:

```
Add quality scoring for PRD validation

- Implement scoring algorithm based on completeness metrics
- Add API endpoint for quality assessment
- Include unit tests for scoring logic
```

### PR Description

Include in your PR description:

- **What** the change does
- **Why** the change is needed
- **How** to test the change
- Any **breaking changes** or migration steps

### Review Process

- PRs require at least one approval before merging
- Address review feedback promptly
- Keep PRs focused and reasonably sized

## Getting Help

- **Issues**: Report bugs or request features via [GitHub Issues](https://github.com/packtman/Intently/issues)
- **Discussions**: Ask questions or discuss ideas in [GitHub Discussions](https://github.com/packtman/Intently/discussions)

---

Thank you for contributing to Intently!
