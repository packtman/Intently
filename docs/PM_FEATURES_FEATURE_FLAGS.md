# PM-Focused Features - Feature Flags Guide

This document explains how to enable/disable the PM-focused features (Unified PM Tool) using feature flags.

## Overview

All PM-focused features are **disabled by default** to maintain backward compatibility with existing Desktop and SaaS tools. Features can be enabled incrementally via environment variables.

## Available Features

### 1. PRD Changes (Diff-Style Suggestions)
**Flag:** `FEATURE_PRD_CHANGES`

Converts findings into actionable PRD changes displayed as diffs (red/green). PMs can accept/reject/edit changes with one click.

**API Endpoints:**
- `GET /api/reviews/{review_id}/changes` - Get all suggested changes
- `POST /api/reviews/{review_id}/changes/{change_id}/accept` - Accept a change
- `POST /api/reviews/{review_id}/changes/{change_id}/reject` - Reject a change
- `POST /api/reviews/{review_id}/changes/bulk-accept` - Bulk accept changes

### 2. PRD Quality Scoring
**Flag:** `FEATURE_PRD_QUALITY_SCORING`

Calculates PRD readiness score (0-100) and identifies gaps. Provides letter grade and breakdown by severity.

**API Endpoints:**
- `GET /api/reviews/{review_id}/quality` - Get quality score

### 3. Effort Estimation
**Flag:** `FEATURE_EFFORT_ESTIMATION`

Code-grounded time estimates for PRD implementation. Estimates days, sprints, and codebase support percentage.

**API Endpoints:**
- `GET /api/reviews/{review_id}/estimate` - Get effort estimation

### 4. Expert Assist (Quick Ask)
**Flag:** `FEATURE_EXPERT_ASSIST`

Lightweight expert validation - PM can ping specific experts for quick validation (not a ticketing system).

**API Endpoints:**
- `POST /api/expert-assist/ask` - Send quick ask to expert
- `POST /api/expert-assist/respond/{ask_id}` - Expert responds

### 5. PM Pattern Learning
**Flag:** `FEATURE_PM_PATTERN_LEARNING`

Learns from expert responses to improve future predictions. Stores patterns and applies them automatically.

**Note:** This feature is planned but not yet fully implemented.

## Enabling Features

### Environment Variables

Set environment variables before starting the API server:

```bash
# Enable all PM features
export FEATURE_PRD_CHANGES=true
export FEATURE_PRD_QUALITY_SCORING=true
export FEATURE_EFFORT_ESTIMATION=true
export FEATURE_EXPERT_ASSIST=true
export FEATURE_PM_PATTERN_LEARNING=true

# Start the API
python -m context_graph.api.main
```

### Docker/Container

```yaml
environment:
  - FEATURE_PRD_CHANGES=true
  - FEATURE_PRD_QUALITY_SCORING=true
  - FEATURE_EFFORT_ESTIMATION=true
  - FEATURE_EXPERT_ASSIST=true
```

### Desktop App

The Desktop app can pass feature flags via environment variables or configuration file. Check the Desktop app documentation for configuration options.

### SaaS Tool

For SaaS deployments, feature flags can be set via:
- Environment variables in deployment config
- Configuration file
- Admin dashboard (if implemented)

## Feature Dependencies

Some features depend on others:

- **PRD Quality Scoring** works best with **PRD Changes** enabled (uses predicted questions)
- **Expert Assist** can work independently but benefits from **PRD Changes** (can ask about specific changes)
- **PM Pattern Learning** requires **Expert Assist** (learns from expert responses)

## Backward Compatibility

When features are **disabled** (default):
- Existing API endpoints continue to work
- Review results don't include PM-focused fields
- PM-specific endpoints return 403 Forbidden
- No performance impact

When features are **enabled**:
- Review results include `predicted_questions`, `prd_quality_score`, `effort_estimation`
- PM-specific endpoints become available
- Slight increase in processing time (PRD change generation)

## Testing

To test with all features enabled:

```python
from context_graph.config.features import set_features, FeatureFlags

# Enable all PM features for testing
features = FeatureFlags.all_enabled()
set_features(features)
```

## API Response Changes

When PM features are enabled, the review result includes additional fields:

```json
{
  "review_id": "...",
  "status": "completed",
  "result": {
    "overview": {...},
    "findings_table": [...],
    // PM-focused fields (when enabled)
    "predicted_questions": [...],
    "prd_quality_score": {
      "score": 72,
      "grade": "C",
      "blockers": 4,
      ...
    },
    "effort_estimation": {
      "total_days": {"min": 14, "likely": 18, "max": 24},
      "codebase_support": 72,
      "tldr": "18 days, 3 sprints, 72% patterns exist"
    }
  }
}
```

## Troubleshooting

### Feature Not Working

1. Check that the feature flag is set: `echo $FEATURE_PRD_CHANGES`
2. Check API logs for feature status on startup
3. Verify the endpoint returns 403 (not enabled) vs 404 (not found)

### Performance Issues

If PRD change generation is slow:
- Consider enabling only specific features you need
- PRD changes generation scales with number of findings
- Quality scoring is fast (O(n) where n = number of questions)

## Migration Path

For existing deployments:

1. **Phase 1:** Enable `FEATURE_PRD_CHANGES` only - test diff-style suggestions
2. **Phase 2:** Enable `FEATURE_PRD_QUALITY_SCORING` - add quality metrics
3. **Phase 3:** Enable `FEATURE_EFFORT_ESTIMATION` - add time estimates
4. **Phase 4:** Enable `FEATURE_EXPERT_ASSIST` - add expert validation
5. **Phase 5:** Enable `FEATURE_PM_PATTERN_LEARNING` - enable learning

This incremental approach allows testing each feature independently.
