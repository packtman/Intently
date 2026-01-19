# Intently Frontend Options

> **Choose the right interface for your workflow**

Intently provides two frontend interfaces for interacting with the security analysis engine. This guide helps you choose and set up the right one for your needs.

---

## Quick Comparison

| | Web Dashboard | Desktop App |
|---|:---:|:---:|
| **Best For** | Teams, server deployment | Power users, daily driver |
| **Setup Time** | ~2 minutes | ~5 minutes |
| **Backend Management** | Manual | Automatic |
| **File Access** | Path input | Native dialogs |
| **Offline Support** | No | Yes |
| **Multi-user** | Yes | No |

---

## At a Glance

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         INTENTLY FRONTENDS                              │
├─────────────────────────────────┬───────────────────────────────────────┤
│        WEB DASHBOARD            │           DESKTOP APP                 │
│         (frontend/)             │            (desktop/)                 │
├─────────────────────────────────┼───────────────────────────────────────┤
│                                 │                                       │
│   ┌─────────────────────┐       │      ┌─────────────────────┐         │
│   │      Browser        │       │      │    Electron App     │         │
│   │  localhost:5173     │       │      │    Native Window    │         │
│   └──────────┬──────────┘       │      └──────────┬──────────┘         │
│              │                  │                 │                     │
│              │ HTTP             │                 │ IPC                 │
│              ▼                  │                 ▼                     │
│   ┌─────────────────────┐       │      ┌─────────────────────┐         │
│   │   Expects running   │       │      │   Manages backend   │         │
│   │      backend        │       │      │    automatically    │         │
│   └─────────────────────┘       │      └─────────────────────┘         │
│                                 │                                       │
│   npm run dev                   │      npm run electron:dev             │
│                                 │                                       │
└─────────────────────────────────┴───────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │     Python Backend      │
                    │    FastAPI + Analysis   │
                    │    localhost:8000       │
                    └─────────────────────────┘
```

---

## Detailed Comparison

### Features

| Feature | Web Dashboard | Desktop App |
|---------|:-------------:|:-----------:|
| Create security reviews | ✅ | ✅ |
| View findings & reports | ✅ | ✅ |
| Multi-dimensional analysis | ✅ | ✅ |
| AI-powered analysis | ✅ | ✅ |
| PRD Generator | ✅ | ✅ |
| Bulk PRD analysis | ✅ | ✅ |
| Team queue & assignments | ✅ | ✅ |
| Dark theme UI | ✅ | ✅ |

### Platform & Access

| Feature | Web Dashboard | Desktop App |
|---------|:-------------:|:-----------:|
| Works in browser | ✅ | ❌ |
| Native app (macOS/Win/Linux) | ❌ | ✅ |
| Native file dialogs | ❌ | ✅ |
| Native notifications | ❌ | ✅ |
| Keyboard shortcuts | Limited | Full |
| Works offline | ❌ | ✅ |

### Backend & Deployment

| Feature | Web Dashboard | Desktop App |
|---------|:-------------:|:-----------:|
| Auto-start backend | ❌ | ✅ |
| Auto-stop backend | ❌ | ✅ |
| Health monitoring | Basic | Advanced |
| Server deployable | ✅ | ❌ |
| Docker support | ✅ | ❌ |
| Multi-user access | ✅ | ❌ |

### GitHub Integration

| Feature | Web Dashboard | Desktop App |
|---------|:-------------:|:-----------:|
| Analyze GitHub repos | ✅ (via backend) | ✅ (built-in download) |
| Paste GitHub URL | ✅ | ✅ |
| Cached repo downloads | ❌ | ✅ |

---

## When to Use Each

### Choose Web Dashboard If You...

- ✅ Want quick access without installing an app
- ✅ Are deploying Intently for a team
- ✅ Already run the backend separately (Docker, server)
- ✅ Prefer a lightweight browser-based solution
- ✅ Need multi-user access to the same backend

### Choose Desktop App If You...

- ✅ Want a dedicated native application
- ✅ Prefer native file/folder selection dialogs
- ✅ Want the backend to start/stop automatically
- ✅ Work offline frequently
- ✅ Want native OS notifications and shortcuts

---

## Quick Start

### Option A: Web Dashboard

```bash
# 1. Start the backend (in one terminal)
cd "Context graph"
context-graph serve

# 2. Start the web dashboard (in another terminal)
cd frontend
npm install
npm run dev

# 3. Open http://localhost:5173
```

### Option B: Desktop App

```bash
# 1. Install and run (backend starts automatically)
cd desktop
npm install
npm run electron:dev

# 2. Configure in Settings:
#    - Intently Path: /path/to/Context graph
#    - API Keys: OpenAI and/or Anthropic
```

### Option C: Both (Development)

You can run both simultaneously for development:

```bash
# Terminal 1: Backend
context-graph serve

# Terminal 2: Web Dashboard
cd frontend && npm run dev

# Terminal 3: Desktop App (will detect running backend)
cd desktop && npm run electron:dev
```

---

## Installation Details

### Prerequisites (Both)

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Node.js | 18+ | Frontend build/runtime |
| Python | 3.10+ | Backend analysis engine |
| npm | 9+ | Package management |

### Web Dashboard Setup

```bash
cd frontend

# Install dependencies
npm install

# Development
npm run dev           # Start dev server at localhost:5173

# Production
npm run build         # Build to dist/
npm run preview       # Preview production build
```

**Environment Variables** (optional):
```env
# frontend/.env
VITE_BACKEND_URL=http://127.0.0.1:8000
```

### Desktop App Setup

```bash
cd desktop

# Install dependencies
npm install

# Development
npm run electron:dev  # Start with hot reload

# Production
npm run electron:build  # Build native installers
```

**First-time Configuration** (in Settings):
- **Intently Path**: Path to the project root
- **Python Path**: `python3` or path to venv
- **API Keys**: OpenAI and/or Anthropic

---

## Architecture Comparison

### Web Dashboard Architecture

```
┌──────────────┐     HTTP      ┌──────────────┐
│   Browser    │◄─────────────►│   Backend    │
│ React + Vite │               │   FastAPI    │
└──────────────┘               └──────────────┘
     Port 5173                    Port 8000

- Browser makes direct HTTP calls to backend
- Backend must be started manually
- State managed with React Query
- Routing with React Router (BrowserRouter)
```

### Desktop App Architecture

```
┌─────────────────────────────────────────────┐
│              Electron App                    │
├──────────────────┬──────────────────────────┤
│   Main Process   │    Renderer Process      │
│   (Node.js)      │    (React + Vite)        │
├──────────────────┼──────────────────────────┤
│ • Window mgmt    │ • UI rendering           │
│ • File dialogs   │ • State management       │
│ • Backend spawn  │ • API calls              │
│ • IPC handling   │ • User interactions      │
└────────┬─────────┴────────────┬─────────────┘
         │ spawn                │ HTTP
         ▼                      ▼
┌──────────────────────────────────────────────┐
│              Python Backend                   │
│              FastAPI Server                   │
│              localhost:8000                   │
└──────────────────────────────────────────────┘

- Main process spawns and manages backend
- Renderer communicates via IPC for native features
- Renderer makes HTTP calls to backend for analysis
- Routing with React Router (HashRouter for file://)
```

---

## Shared Components

Both frontends share similar React components but with platform-specific adaptations:

| Component | Web | Desktop | Difference |
|-----------|-----|---------|------------|
| `useBackend` hook | ✅ | ✅ | Desktop adds start/stop backend |
| `api.ts` service | ✅ | ✅ | Desktop gets URL from Electron |
| `Layout.tsx` | ✅ | ✅ | Desktop adds drag regions |
| Pages | ✅ | ✅ | Desktop adds file dialogs |
| `Settings.tsx` | ✅ | ✅ | Desktop has backend config |

---

## Development Scripts

### Web Dashboard (`frontend/`)

| Script | Description |
|--------|-------------|
| `npm run dev` | Start Vite dev server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm test` | Run tests |
| `npm run lint` | Lint code |

### Desktop App (`desktop/`)

| Script | Description |
|--------|-------------|
| `npm run electron:dev` | Start Electron + Vite with hot reload |
| `npm run electron:build` | Build native installers |
| `npm run dev` | Start Vite only (for UI development) |
| `npm run build:electron` | Build Electron main/preload |
| `npm test` | Run tests |

---

## Troubleshooting

### Backend Connection Issues

**Web Dashboard:**
```bash
# Check if backend is running
curl http://localhost:8000/health

# Start backend if not running
context-graph serve
```

**Desktop App:**
1. Go to Settings
2. Verify Intently Path is correct
3. Click "Start" to manually start backend
4. Check console for errors

### Port Conflicts

**Web Dashboard (port 5173):**
```bash
# Find and kill process on port
lsof -i :5173
kill -9 <PID>
```

**Backend (port 8000):**
```bash
# Find and kill process on port
lsof -i :8000
kill -9 <PID>
```

### Build Issues

```bash
# Clean install for either frontend
rm -rf node_modules package-lock.json
npm install
```

---

## Summary

| Scenario | Recommended |
|----------|-------------|
| Quick browser access | **Web Dashboard** |
| Server/team deployment | **Web Dashboard** |
| Docker deployment | **Web Dashboard** |
| Daily security reviews | **Desktop App** |
| Native file handling | **Desktop App** |
| Offline work | **Desktop App** |
| Auto-managed backend | **Desktop App** |

Both frontends connect to the same Python backend and provide the same analysis capabilities. Choose based on your deployment needs and workflow preferences.

---

<p align="center">
  <strong>Intently</strong> - Proactive Security for Product Development
</p>
