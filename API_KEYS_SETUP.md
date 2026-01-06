# API Keys Setup Guide

## Quick Summary

To use **AI-based findings only** (no pattern-based findings), you need to set API keys as environment variables.

## Required API Keys

You need **at least one** of these:

- `OPENAI_API_KEY` - For OpenAI GPT models (recommended for chat functionality)
- `ANTHROPIC_API_KEY` - For Anthropic Claude models

## Where API Keys Are Used

### 1. Security Review (AI Findings)
**Location:** `src/context_graph/api/routes.py` lines 462-463

```python
openai_key = request.config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
anthropic_key = request.config.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY")
```

**What happens:**
- If API keys are present → AI-based findings only (pattern-based disabled)
- If API keys are missing → Falls back to pattern-based findings only

### 2. Chat Functionality
**Location:** `src/context_graph/api/routes.py` line 298

```python
openai_key = os.getenv("OPENAI_API_KEY")
```

**What happens:**
- If `OPENAI_API_KEY` is present → Full AI chat works
- If missing → Shows error message explaining API key is required

## How to Set API Keys

### Option 1: Terminal Session (Temporary)
```bash
export OPENAI_API_KEY="sk-your-actual-key-here"
export ANTHROPIC_API_KEY="sk-ant-your-actual-key-here"
```

### Option 2: Shell Profile (Permanent)
Add to your `~/.zshrc` or `~/.bashrc`:

```bash
echo 'export OPENAI_API_KEY="sk-your-actual-key-here"' >> ~/.zshrc
echo 'export ANTHROPIC_API_KEY="sk-ant-your-actual-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### Option 3: Project `.env` File (Development)
Create `.env` in project root:

```bash
OPENAI_API_KEY=sk-your-actual-key-here
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

**Note:** Make sure `.env` is in `.gitignore` (it should be already).

### Option 4: IDE Environment Variables
- **VS Code/Cursor:** Set in workspace settings or launch configuration
- **PyCharm:** Settings → Build, Execution, Deployment → Python → Environment Variables

## Verify API Keys Are Set

```bash
# Check if keys are set
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# Test in Python
python -c "import os; print('OPENAI:', bool(os.getenv('OPENAI_API_KEY'))); print('ANTHROPIC:', bool(os.getenv('ANTHROPIC_API_KEY')))"
```

## Get Your API Keys

1. **OpenAI:**
   - Go to: https://platform.openai.com/api-keys
   - Sign up/login
   - Create new secret key
   - Copy the key (starts with `sk-`)

2. **Anthropic:**
   - Go to: https://console.anthropic.com/settings/keys
   - Sign up/login
   - Create API key
   - Copy the key (starts with `sk-ant-`)

## Troubleshooting

### "LLM requested but no API keys found"
- **Problem:** API keys not set in environment
- **Solution:** Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` as shown above
- **Verify:** Restart your terminal/server after setting keys

### Chat shows "Chat functionality requires an OpenAI API key"
- **Problem:** `OPENAI_API_KEY` not set
- **Solution:** Set `OPENAI_API_KEY` environment variable
- **Note:** Chat currently only works with OpenAI (not Anthropic)

### Still getting pattern-based findings
- **Problem:** API keys not detected by the server
- **Solution:** 
  1. Verify keys are set: `echo $OPENAI_API_KEY`
  2. Restart the server: `context-graph serve`
  3. Check server logs for API key detection

## Code Locations Reference

- **Review configuration:** `src/context_graph/api/routes.py:461-478`
- **Chat endpoint:** `src/context_graph/api/routes.py:290-310`
- **LLM analyzer:** `src/context_graph/llm/parallel_analyzer.py:50-72`

