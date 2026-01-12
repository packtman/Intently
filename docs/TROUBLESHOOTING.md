# Troubleshooting Guide

## Known Issues and Solutions

### 1. GitHub Clone "Operation not permitted" Error (macOS)

**Symptoms:**
```
Review failed: Failed to clone repository: fatal: could not create work tree dir 
'/Users/.../Library/Caches/context-graph/repos/...': Operation not permitted
```

Or:
```
/private/var/folders/.../.git: Operation not permitted
```

**Root Cause:**
macOS has strict sandboxing and security restrictions on certain directories:
- `~/Library/Caches/` - Can be restricted when app is sandboxed (Electron)
- `/var/folders/` (via `tempfile.gettempdir()`) - Can have quarantine/security restrictions
- These restrictions prevent git from creating the `.git` directory during clone

**Solution:**
The fix is implemented in `src/context_graph/integrations/github.py`:
- Use `/tmp/context-graph-repos/` directly on macOS instead of restricted directories
- `/tmp` is a symlink to `/private/tmp` which has full write access

**Code Location:**
```python
# In github.py clone() method
if platform.system() == "Darwin":
    # Use /tmp directly - /var/folders can have quarantine restrictions
    user_cache = Path("/tmp") / "context-graph-repos"
```

**If the issue recurs:**
1. Check if the clone path is using `/tmp/context-graph-repos/`
2. If using a different path, update to use `/tmp` directly
3. Ensure `CONTEXT_GRAPH_CACHE_DIR` env var (if set) points to a writable directory
4. Restart the backend server after any code changes

**If error occurs with already-downloaded repos (or fresh clone fails):**

The macOS sandbox blocks ALL git operations (clone, fetch, push) when Python is 
spawned by a sandboxed Electron app. This is a known macOS security restriction.

**Workaround implemented in `github.py`:**
1. Detects existing clones of the same repo (e.g., `cal.com-*`)
2. Reuses them directly WITHOUT any git operations
3. Falls back to `rm -rf` for cleanup when needed

**To add a new repo for scanning:**
```bash
# Clone manually from terminal (outside Electron)
cd /tmp/context-graph-repos
git clone --depth 1 https://github.com/owner/repo.git repo-cached
```

**To refresh an existing repo:**
```bash
cd /tmp/context-graph-repos/repo-cached
git fetch --depth=1 origin
git reset --hard origin/HEAD
```

**To clear all cached repos:**
```bash
rm -rf /tmp/context-graph-repos/*
```

**Environment Variable Override:**
You can also set a custom cache directory:
```bash
export CONTEXT_GRAPH_CACHE_DIR="/path/to/writable/directory"
```

---

### 2. Server Won't Restart / Reload Issues

**Symptoms:**
- uvicorn `--reload` crashes with `PermissionError: [Errno 1] Operation not permitted`
- Changes not picked up after editing files

**Solution:**
1. Kill all server processes manually:
   ```bash
   lsof -ti:8000 | xargs kill -9
   lsof -ti:3000 | xargs kill -9
   ```
2. Clear Python cache:
   ```bash
   find . -type d -name "__pycache__" -exec rm -rf {} +
   ```
3. Restart using `./start-servers.sh`

---

### 3. Electron Desktop App Build Errors

**Symptoms:**
```
TypeError: Cannot read properties of undefined (reading 'isPackaged')
```

**Solution:**
This is typically a build/bundling issue. Try:
1. `cd "context graph Desktop app"`
2. `rm -rf node_modules dist-electron`
3. `npm install`
4. `npm run electron:dev`

---

## Quick Reference

| Issue | Quick Fix |
|-------|-----------|
| Clone permission error | Ensure using `/tmp/context-graph-repos/` on macOS |
| Server won't reload | Kill processes and restart with `./start-servers.sh` |
| Old code still running | Clear `__pycache__` directories |
| Port already in use | `lsof -ti:8000 \| xargs kill -9` |

---

*Last updated: 2026-01-11*
*Issue first encountered: macOS sandbox restrictions on Electron-spawned Python processes*
