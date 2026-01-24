# Storage Configuration

Context Graph supports two storage backends for persisting reviews and collaboration data.

## Storage Backends

| Backend | Persistence | Use Case |
|---------|-------------|----------|
| `memory` | None (data lost on restart) | Development, testing |
| `sqlite` | Local file | Production, desktop app |

## Configuration

Storage is configured via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `STORAGE_BACKEND` | Storage type: `memory` or `sqlite` | `memory` |
| `STORAGE_DB_PATH` | Path to SQLite database file | `~/.context-graph/reviews.db` |

## Quick Start

### Option 1: Using Startup Scripts (Recommended)

The startup scripts automatically configure SQLite storage:

```bash
# Development server with SQLite
./scripts/start-servers.sh

# Production server with SQLite
./scripts/start-servers-production.sh
```

Database is stored at: `Context graph/data/reviews.db`

### Option 2: Manual Configuration

```bash
# Set environment variables
export STORAGE_BACKEND=sqlite
export STORAGE_DB_PATH=/path/to/reviews.db

# Start the server
context-graph serve
```

### Option 3: Using .env File

Create a `.env` file in the project root:

```env
STORAGE_BACKEND=sqlite
STORAGE_DB_PATH=./data/reviews.db
```

## Desktop App

The Electron desktop app automatically uses SQLite storage with the database stored in the app's data directory:

- **macOS**: `~/Library/Application Support/Intently/data/reviews.db`
- **Windows**: `%APPDATA%/Intently/data/reviews.db`
- **Linux**: `~/.config/Intently/data/reviews.db`

No configuration needed - reviews persist automatically.

## What's Stored

The SQLite database persists:

### Reviews
- Complete review results with all findings
- Intent (parsed PRD data)
- State (codebase analysis)
- Findings by dimension (security, privacy, compliance, engineering, architecture)
- Executive summary and risk rating
- PM features (predicted questions, quality scores, effort estimates)

### Review Status
- Progress tracking for running reviews
- Status messages and dimension info

### Collaboration Data
- **Validations**: Finding validation decisions
- **Comments**: Threaded comments on findings
- **Assignments**: Team/user assignments
- **Expert Feedback**: Feedback from domain experts
- **Lifecycle**: Review state and history
- **Review Requests**: Cross-team review requests
- **Consensus Votes**: Team voting on findings
- **Patterns**: Learned patterns from feedback

## Database Location Priority

When `STORAGE_DB_PATH` is not set, the database path is determined by:

1. `STORAGE_DB_PATH` environment variable (if set)
2. `CONTEXT_GRAPH_DATA_DIR/reviews.db` (if `CONTEXT_GRAPH_DATA_DIR` is set)
3. `~/.context-graph/reviews.db` (default)

## Switching Between Backends

You can switch backends without code changes:

```bash
# Use in-memory for testing
STORAGE_BACKEND=memory context-graph serve

# Use SQLite for persistence
STORAGE_BACKEND=sqlite context-graph serve
```

## Programmatic Usage

```python
from context_graph.storage import (
    get_review_storage,
    get_collaboration_storage,
    get_storage_backend,
)

# Get configured storage instances
review_storage = get_review_storage()
collab_storage = get_collaboration_storage()

# Check current backend
print(f"Using: {get_storage_backend()}")  # "memory" or "sqlite"

# Use storage
await review_storage.save_review(review_id, result)
review = await review_storage.get_review(review_id)
reviews = await review_storage.list_reviews()
```

## Backup and Migration

### Backup SQLite Database

```bash
# Simple copy
cp ~/.context-graph/reviews.db ~/.context-graph/reviews.db.backup

# Or use SQLite backup command
sqlite3 ~/.context-graph/reviews.db ".backup 'backup.db'"
```

### View Database Contents

```bash
sqlite3 ~/.context-graph/reviews.db

# List tables
.tables

# View reviews
SELECT id, risk_rating, reviewed_at FROM reviews;

# View review count
SELECT COUNT(*) FROM reviews;
```

## Troubleshooting

### Database Locked Error

If you see "database is locked", ensure only one server instance is running:

```bash
# Find and kill existing processes
lsof -ti:8000 | xargs kill -9
```

### Reset Database

To start fresh, delete the database file:

```bash
rm ~/.context-graph/reviews.db
# Or for project-local storage:
rm ./data/reviews.db
```

### Check Storage Configuration

Add logging to see which storage is being used:

```bash
# The server logs storage type on startup
context-graph serve
# Look for: "📦 Storage: SQLite (/path/to/reviews.db)"
```
