# Enable All PM Features - Complete Setup

## ✅ Recommended: Enable All Features

For the best PM tool experience, enable all features:

```bash
# All PM features including pattern learning
export FEATURE_PRD_CHANGES=true
export FEATURE_PRD_QUALITY_SCORING=true
export FEATURE_EFFORT_ESTIMATION=true
export FEATURE_EXPERT_ASSIST=true
export FEATURE_PM_PATTERN_LEARNING=true  # ⭐ Recommended!
```

## Quick Setup

### Option 1: Copy & Paste

```bash
export FEATURE_PRD_CHANGES=true
export FEATURE_PRD_QUALITY_SCORING=true
export FEATURE_EFFORT_ESTIMATION=true
export FEATURE_EXPERT_ASSIST=true
export FEATURE_PM_PATTERN_LEARNING=true
```

### Option 2: Use Helper Script

**Linux/macOS:**
```bash
source scripts/enable-pm-features.sh
```

**Windows:**
```cmd
scripts\enable-pm-features.bat
```

### Option 3: Add to Your Shell Profile

Add to `~/.bashrc`, `~/.zshrc`, or `~/.profile`:

```bash
# PM Tool Features
export FEATURE_PRD_CHANGES=true
export FEATURE_PRD_QUALITY_SCORING=true
export FEATURE_EFFORT_ESTIMATION=true
export FEATURE_EXPERT_ASSIST=true
export FEATURE_PM_PATTERN_LEARNING=true
```

Then reload:
```bash
source ~/.bashrc  # or ~/.zshrc
```

## What Each Feature Does

| Feature | What It Does | Why Enable |
|---------|-------------|------------|
| **PRD Changes** | Diff-style PRD suggestions | Core feature - shows what to change |
| **Quality Scoring** | PRD readiness score (0-100) | Know if PRD is ready |
| **Effort Estimation** | Time estimates for implementation | Plan sprints and timelines |
| **Expert Assist** | Quick expert validation | Get expert feedback easily |
| **Pattern Learning** | Learns from expert responses | Makes system smarter over time ⭐ |

## Verify Features Are Enabled

### 1. Check Environment Variables

```bash
echo $FEATURE_PRD_CHANGES
echo $FEATURE_PRD_QUALITY_SCORING
echo $FEATURE_EFFORT_ESTIMATION
echo $FEATURE_EXPERT_ASSIST
echo $FEATURE_PM_PATTERN_LEARNING
```

All should output: `true`

### 2. Start Backend and Check Logs

When you start the backend, you should see:

```
PM Features Status:
  - PRD Changes: ✅ Enabled
  - PRD Quality Scoring: ✅ Enabled
  - Effort Estimation: ✅ Enabled
  - Expert Assist: ✅ Enabled
  - PM Pattern Learning: ✅ Enabled
```

### 3. Test API Endpoints

```bash
# Test PRD changes (should return 200, not 403)
curl http://localhost:8000/api/reviews/{review_id}/changes

# Test quality score
curl http://localhost:8000/api/reviews/{review_id}/quality

# Test effort estimation
curl http://localhost:8000/api/reviews/{review_id}/estimate

# Test pattern insights
curl http://localhost:8000/api/patterns/insights
```

All should return `200 OK` (not `403 Forbidden`).

## Complete Feature Set

With all features enabled, you get:

### 1. PRD Changes (Diff-Style)
- ✅ Red/green diff view
- ✅ Accept/reject/edit changes
- ✅ Bulk accept with filters
- ✅ Undo functionality
- ✅ Download updated PRD

### 2. Quality Scoring
- ✅ 0-100 score with letter grade
- ✅ Identifies gaps
- ✅ Shows blockers/likely/possible questions

### 3. Effort Estimation
- ✅ Min/likely/max days
- ✅ Codebase support percentage
- ✅ Sprint estimates
- ✅ TLDR summary

### 4. Expert Assist
- ✅ Quick ask (not ticketing)
- ✅ Expert search/selection
- ✅ One-click response
- ✅ Question pre-fill

### 5. Pattern Learning ⭐
- ✅ Learns from expert feedback
- ✅ Reduces false positives
- ✅ Improves predictions automatically
- ✅ Tracks accuracy

## Usage Flow

1. **Create Review** → Upload PRD
2. **System Analyzes** → Generates findings
3. **View PRD Changes Tab** → See diff-style suggestions
4. **Check Quality Score** → See if PRD is ready
5. **Check Effort Estimate** → Plan timeline
6. **Accept Changes** → One-click or bulk accept
7. **Ask Expert** → Get quick validation
8. **Expert Responds** → System learns (pattern learning)
9. **Future Reviews** → Better predictions automatically!

## Troubleshooting

### Features Not Working?

1. **Verify variables are set:**
   ```bash
   env | grep FEATURE
   ```

2. **Restart backend** after setting variables

3. **Check backend logs** for feature status

4. **Test API endpoints** - should return 200, not 403

### API Returns 403?

- Feature flag not enabled
- Backend not restarted after setting variables
- Check environment variable spelling

## Next Steps

1. ✅ Enable all features (using setup above)
2. ✅ Start backend server
3. ✅ Create a review with PRD
4. ✅ Navigate to "PRD Changes" tab
5. ✅ Explore all features!

## Documentation

- [Quick Start Guide](./QUICK_START_PM_FEATURES.md)
- [Pattern Learning Guide](./PATTERN_LEARNING_GUIDE.md)
- [Feature Flags Guide](./PM_FEATURES_FEATURE_FLAGS.md)
- [Complete Implementation](./COMPLETE_IMPLEMENTATION_SUMMARY.md)

---

**You're all set! 🚀**

All PM features are enabled and ready to use.
