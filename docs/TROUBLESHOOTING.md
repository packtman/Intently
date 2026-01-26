# Troubleshooting Guide

## Installation Issues

### "command not found: context-graph" after pip install

**Symptoms:**
```
zsh: command not found: context-graph
```

**Causes & Solutions:**

1. **Virtual environment not activated:**
   ```bash
   # Activate your virtual environment first
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   
   # Then try again
   context-graph --help
   ```

2. **Installed outside virtual environment:**
   ```bash
   # Create and activate venv, then reinstall
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

3. **PATH issue (pip installed to user directory):**
   ```bash
   # Check where pip installed the command
   pip show context-graph
   
   # Try running with python -m instead
   python -m context_graph.cli --help
   ```

### "pip install -e ." fails with "-e option requires 1 argument"

**Symptoms:**
```
error: -e option requires 1 argument
```

**Cause:** You're in the wrong directory. The `.` means "current directory" and pip can't find a `pyproject.toml` file there.

**Solution:**
```bash
# Check if pyproject.toml exists in your current directory
ls pyproject.toml

# If "No such file", navigate to where you cloned the repo
cd /path/to/Intently

# Verify again
ls pyproject.toml   # Should now show the file

# Then install
pip install -e .
```

### "pip install -e ." fails with dependency errors

**Symptoms:**
```
ERROR: Could not find a version that satisfies the requirement...
ERROR: No matching distribution found...
```

**Solutions:**

1. **Wrong directory** - Make sure you're in the project root (where `pyproject.toml` is):
   ```bash
   # Check if pyproject.toml exists
   ls pyproject.toml
   
   # If not, navigate to the correct directory
   cd /path/to/Intently
   ```

2. **Python version too old:**
   ```bash
   # Check Python version (needs 3.10+)
   python3 --version
   
   # If < 3.10, install newer Python
   # macOS: brew install python@3.12
   # Ubuntu: sudo apt install python3.12
   ```

3. **pip is outdated:**
   ```bash
   pip install --upgrade pip
   pip install -e .
   ```

4. **Network/proxy issues:**
   ```bash
   # Try with verbose output to see what's failing
   pip install -e . -v
   ```

### ModuleNotFoundError after installation

**Symptoms:**
```
ModuleNotFoundError: No module named 'context_graph'
```

**Solution:**
You're likely running Python outside the virtual environment:
```bash
# Always activate venv before running
source .venv/bin/activate
context-graph --help
```

---

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
| `command not found: context-graph` | Activate venv: `source .venv/bin/activate` |
| `-e option requires 1 argument` | Wrong directory - run `ls pyproject.toml` to check |
| `pip install -e .` fails | Check you're in project root (has `pyproject.toml`) |
| Python version error | Need Python 3.10+: `python3 --version` |
| ModuleNotFoundError | Activate venv before running |
| Clone permission error | Ensure using `/tmp/context-graph-repos/` on macOS |
| Server won't reload | Kill processes and restart with `./start-servers.sh` |
| Old code still running | Clear `__pycache__` directories |
| Port already in use | `lsof -ti:8000 \| xargs kill -9` |

---

*Last updated: 2026-01-25*
*Added installation troubleshooting section*
