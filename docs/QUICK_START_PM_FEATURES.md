# Quick Start: Enable PM Features

## Enable All PM Features

**Recommended: Enable all features for the best experience!**

### Option 1: Environment Variables (Recommended)

```bash
# All PM features including pattern learning
export FEATURE_PRD_CHANGES=true
export FEATURE_PRD_QUALITY_SCORING=true
export FEATURE_EFFORT_ESTIMATION=true
export FEATURE_EXPERT_ASSIST=true
export FEATURE_PM_PATTERN_LEARNING=true  # ⭐ Recommended!
```

> 💡 **Tip:** See [Enable All PM Features](./ENABLE_ALL_PM_FEATURES.md) for complete setup guide.

### Option 2: Using Helper Script

**Linux/macOS:**
```bash
source scripts/enable-pm-features.sh
```

**Windows:**
```cmd
scripts\enable-pm-features.bat
```

### Option 3: Using .env File

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set all PM features to `true`:
   ```env
   FEATURE_PRD_CHANGES=true
   FEATURE_PRD_QUALITY_SCORING=true
   FEATURE_EFFORT_ESTIMATION=true
   FEATURE_EXPERT_ASSIST=true
   FEATURE_PM_PATTERN_LEARNING=true
   ```

3. Load the environment variables:
   ```bash
   # If using python-dotenv
   export $(cat .env | xargs)
   ```

## Enable Features Incrementally

You can enable features one at a time:

### Step 1: Start with PRD Changes
```bash
export FEATURE_PRD_CHANGES=true
```

### Step 2: Add Quality Scoring
```bash
export FEATURE_PRD_QUALITY_SCORING=true
```

### Step 3: Add Effort Estimation
```bash
export FEATURE_EFFORT_ESTIMATION=true
```

### Step 4: Add Expert Assist
```bash
export FEATURE_EXPERT_ASSIST=true
```

### Step 5: Add Pattern Learning (Recommended)
```bash
export FEATURE_PM_PATTERN_LEARNING=true
```

**Why enable Pattern Learning?**
- Makes the system smarter over time
- Learns from expert feedback
- Reduces false positives
- Improves predictions automatically
- See [Pattern Learning Guide](./PATTERN_LEARNING_GUIDE.md) for details

## Verify Features Are Enabled

### Check Backend Startup Logs

When you start the backend, you should see:
```
PM Features Status:
  - PRD Changes: ✅ Enabled
  - PRD Quality Scoring: ✅ Enabled
  - Effort Estimation: ✅ Enabled
  - Expert Assist: ✅ Enabled
  - PM Pattern Learning: ✅ Enabled
```

### Test API Endpoints

```bash
# Test PRD changes endpoint
curl http://localhost:8000/api/reviews/{review_id}/changes

# Should return 200 (if feature enabled) or 403 (if disabled)
```

## Feature Descriptions

| Feature | Description | Required For |
|---------|-------------|-------------|
| `FEATURE_PRD_CHANGES` | Diff-style PRD suggestions | Core PM experience |
| `FEATURE_PRD_QUALITY_SCORING` | PRD readiness score | Quality assessment |
| `FEATURE_EFFORT_ESTIMATION` | Time estimates | Planning |
| `FEATURE_EXPERT_ASSIST` | Quick expert validation | Expert workflow |
| `FEATURE_PM_PATTERN_LEARNING` | Learn from feedback | **Recommended** - Makes system smarter over time |

## Troubleshooting

### Features Not Working?

1. **Check environment variables are set:**
   ```bash
   echo $FEATURE_PRD_CHANGES
   # Should output: true
   ```

2. **Restart the backend server** after setting variables

3. **Check backend logs** for feature status

4. **Verify API response:**
   - 200 = Feature enabled
   - 403 = Feature disabled

### Common Issues

**Issue:** API returns 403 Forbidden
- **Solution:** Feature flag not enabled or backend not restarted

**Issue:** No PRD changes shown
- **Solution:** Ensure `FEATURE_PRD_CHANGES=true` and review has findings

**Issue:** Quality score not appearing
- **Solution:** Ensure `FEATURE_PRD_QUALITY_SCORING=true` and PRD changes exist

## Next Steps

1. ✅ Enable features (using one of the methods above)
2. ✅ Start backend server
3. ✅ Create a review with a PRD
4. ✅ Navigate to "PRD Changes" tab
5. ✅ See diff-style suggestions!

## Full Documentation

- [PM Features Feature Flags](./PM_FEATURES_FEATURE_FLAGS.md)
- [Pattern Learning Guide](./PATTERN_LEARNING_GUIDE.md) - Learn how pattern learning works
- [Complete Implementation Summary](./COMPLETE_IMPLEMENTATION_SUMMARY.md)
- [Frontend Testing Summary](./FRONTEND_TESTING_SUMMARY.md)
