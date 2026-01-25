# Intently Web Dashboard

> **Browser-based interface for multi-dimensional product analysis**

A React-based web dashboard for running Intently reviews across security, privacy, compliance, engineering, and architecture dimensions. Lightweight, deployable, and perfect for team access via browser.

---

## Table of Contents

- [Overview](#overview)
- [Choosing Your Interface](#choosing-your-interface)
- [Features](#features)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Development](#development)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [License](#license)

---

## Overview

Intently Web Dashboard provides a browser-based interface for the security analysis pipeline. It connects to the Python backend via HTTP and provides a clean UI for creating and managing security reviews.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Intently Web Dashboard                       │  │
│  │                  (React + Vite)                           │  │
│  └─────────────────────────┬─────────────────────────────────┘  │
└────────────────────────────┼────────────────────────────────────┘
                             │ HTTP
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                              │
│                   localhost:8000                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Parsers   │  │  Analyzers  │  │  Security   │             │
│  │             │  │             │  │   Engine    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Choosing Your Interface

Intently provides two frontend options. Choose the one that fits your workflow:

| Feature | Web Dashboard | Desktop App |
|---------|---------------|-------------|
| **Access** | Any browser | Native application |
| **Backend** | Start manually | Auto-managed |
| **File Selection** | Paste paths manually | Native file dialogs |
| **GitHub Repos** | Via backend API | Built-in download |
| **Multi-user** | Yes (shared backend) | Single user |
| **Deployment** | Server/Docker | Local install |
| **Offline** | No | Yes |
| **Setup Time** | ~2 minutes | ~5 minutes |

### Use Web Dashboard When

- You want quick browser access without installing an app
- You're deploying Intently on a server for team access
- You already have the backend running (e.g., via Docker)
- You prefer a lightweight solution

### Use Desktop App When

- You want native file system integration
- You prefer the backend to start/stop automatically
- You work offline frequently
- You want native OS notifications and shortcuts

➡️ **Desktop App**: See [`../desktop/README.md`](../desktop/README.md)

---

## Features

### Security Analysis

- **Multi-Dimensional Reviews**
  - Security (STRIDE, OWASP Top 10)
  - Privacy (LINDDUN, GDPR/CCPA)
  - Compliance (SOC 2, HIPAA, PCI-DSS)
  - Engineering (code quality, testing gaps)
  - Architecture (API design, dependencies)

- **AI-Powered Insights**
  - OpenAI GPT-4 integration
  - Anthropic Claude integration
  - Parallel analysis with consensus

### Dashboard Features

- **Review Management** - Create, view, and export security reviews
- **Real-time Status** - Live progress tracking during analysis
- **Findings Browser** - Filter by severity, dimension, category
- **Team Queue** - Assign findings to teams for remediation
- **PRD Generator** - Generate PRDs from existing codebases
- **Bulk Analysis** - Analyze multiple PRDs at once

---

## Quick Start

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Node.js | 18+ | For the web dashboard |
| Python | 3.10+ | For the backend |
| Backend Running | - | Start with `context-graph serve` |

### 1. Start the Backend

```bash
# From the project root
cd ..

# Option A: Using the CLI
context-graph serve

# Option B: Using the start script
./scripts/start-servers.sh
```

The backend runs at `http://localhost:8000`

### 2. Start the Web Dashboard

```bash
# From the frontend directory
npm install
npm run dev
```

The dashboard runs at `http://localhost:5173`

### 3. Open in Browser

Navigate to [http://localhost:5173](http://localhost:5173)

---

## Configuration

### Environment Variables

Create a `.env` file in the frontend directory:

```env
# Backend URL (default: http://127.0.0.1:8000)
VITE_BACKEND_URL=http://127.0.0.1:8000
```

### Backend API Keys

The backend needs API keys for AI analysis. Set them before starting the backend:

```bash
# OpenAI (for GPT-4 analysis)
export OPENAI_API_KEY="sk-..."

# Anthropic (for Claude analysis)
export ANTHROPIC_API_KEY="sk-ant-..."

# Then start the backend
context-graph serve
```

---

## Development

### Scripts

```bash
# Start development server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm test

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage

# Lint code
npm run lint
```

### Tech Stack

| Technology | Purpose |
|------------|---------|
| React 18 | UI framework |
| TypeScript | Type safety |
| Vite | Build tool & dev server |
| Tailwind CSS | Styling |
| React Query | Server state management |
| React Router | Client-side routing |
| Framer Motion | Animations |
| Recharts | Data visualization |
| Vitest | Testing |

---

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── collaboration/   # Team collaboration features
│   │   │   ├── CommentsThread.tsx
│   │   │   ├── FindingValidationPanel.tsx
│   │   │   └── TeamAssignmentPanel.tsx
│   │   ├── pm/              # PM tools
│   │   │   ├── PRDChangeCard.tsx
│   │   │   ├── PRDChangesView.tsx
│   │   │   └── SideBySideDiffModal.tsx
│   │   ├── security/        # Security visualizations
│   │   │   ├── AttackFlowDiagram.tsx
│   │   │   ├── RiskMatrixView.tsx
│   │   │   └── RemediationStrategy.tsx
│   │   ├── Layout.tsx       # App shell
│   │   └── IntentBreakdown.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx    # Home page
│   │   ├── NewReview.tsx    # Create review wizard
│   │   ├── ReviewDetail.tsx # Review results
│   │   ├── Reviews.tsx      # All reviews list
│   │   ├── BulkAnalysis.tsx # Bulk PRD analysis
│   │   ├── PRDGenerator.tsx # Generate PRDs
│   │   ├── TeamQueue.tsx    # Team assignments
│   │   └── Settings.tsx     # Configuration
│   ├── hooks/
│   │   └── useBackend.tsx   # Backend connection hook
│   ├── services/
│   │   └── api.ts           # API client
│   ├── types/
│   │   └── index.ts         # TypeScript definitions
│   ├── __tests__/           # Test files
│   ├── App.tsx              # Root component
│   ├── main.tsx             # Entry point
│   └── index.css            # Global styles
├── index.html
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
└── vitest.config.ts
```

---

## API Reference

The web dashboard communicates with the backend via REST API:

### Reviews

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/reviews` | List all reviews |
| `POST` | `/api/reviews` | Create new review |
| `GET` | `/api/reviews/{id}/status` | Get review progress |
| `GET` | `/api/reviews/{id}/dashboard` | Get review results |
| `GET` | `/api/reviews/{id}/markdown` | Export as Markdown |

### Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/parse-prd` | Parse PRD content |
| `POST` | `/api/analyze-codebase` | Analyze codebase |
| `GET` | `/api/reviews/{id}/changes` | Get suggested PRD changes |
| `GET` | `/api/reviews/{id}/quality` | Get PRD quality score |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Backend health check |

---

## Deployment

### Docker (Recommended)

```dockerfile
# Dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### Static Hosting

```bash
# Build for production
npm run build

# Output is in dist/ - deploy to any static host
# (Vercel, Netlify, S3, etc.)
```

**Note**: For production, ensure `VITE_BACKEND_URL` points to your deployed backend.

---

## License

MIT License - see [LICENSE](../LICENSE) for details.

---

<p align="center">
  <strong>Intently</strong> — Multi-Dimensional Product Analysis
</p>
