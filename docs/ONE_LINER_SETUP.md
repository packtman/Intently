# One-Liner Setup - All PM Features

## Quick Enable (Copy & Paste)

### Linux/macOS

```bash
export FEATURE_PRD_CHANGES=true && export FEATURE_PRD_QUALITY_SCORING=true && export FEATURE_EFFORT_ESTIMATION=true && export FEATURE_EXPERT_ASSIST=true && export FEATURE_PM_PATTERN_LEARNING=true && echo "✅ All PM features enabled!"
```

### Or Use Script

```bash
source scripts/enable-pm-features.sh
```

### Windows (PowerShell)

```powershell
$env:FEATURE_PRD_CHANGES="true"; $env:FEATURE_PRD_QUALITY_SCORING="true"; $env:FEATURE_EFFORT_ESTIMATION="true"; $env:FEATURE_EXPERT_ASSIST="true"; $env:FEATURE_PM_PATTERN_LEARNING="true"; Write-Host "✅ All PM features enabled!"
```

### Windows (CMD)

```cmd
set FEATURE_PRD_CHANGES=true && set FEATURE_PRD_QUALITY_SCORING=true && set FEATURE_EFFORT_ESTIMATION=true && set FEATURE_EXPERT_ASSIST=true && set FEATURE_PM_PATTERN_LEARNING=true && echo ✅ All PM features enabled!
```

## Verify

```bash
# Check all are set
env | grep FEATURE | grep PM
```

Should show all 5 features with `true`.

## Start Backend

```bash
python -m context_graph.api.main
```

Check logs for:
```
PM Features Status:
  - PRD Changes: ✅ Enabled
  - PRD Quality Scoring: ✅ Enabled
  - Effort Estimation: ✅ Enabled
  - Expert Assist: ✅ Enabled
  - PM Pattern Learning: ✅ Enabled
```

## That's It! 🚀

All PM features are now enabled and ready to use.
