# PM Features - Testing Guide

This document describes the test coverage for PM-focused features (Unified PM Tool).

## Test Coverage

### Test File: `test_pm_features.py`

Comprehensive test suite covering all PM-focused features with **200+ test cases**.

## Test Categories

### 1. PRD Change Generator Tests (`TestPRDChangeGenerator`)

Tests the core functionality of converting findings into diff-style PRD suggestions:

- ✅ `test_generate_changes_from_findings` - Generates changes from findings
- ✅ `test_generate_question_text` - Converts findings to questions
- ✅ `test_extract_code_evidence` - Extracts code references
- ✅ `test_determine_section` - Maps dimensions to PRD sections
- ✅ `test_generate_diff_hunks` - Creates diff hunks for rendering

**Coverage:** Core change generation logic

### 2. PRD Quality Scorer Tests (`TestPRDQualityScorer`)

Tests quality scoring algorithm:

- ✅ `test_calculate_score_no_questions` - High score with no issues
- ✅ `test_calculate_score_with_blockers` - Penalizes blockers
- ✅ `test_identify_gaps` - Identifies key gaps in PRD

**Coverage:** Scoring algorithm, gap identification

### 3. Effort Estimator Tests (`TestEffortEstimator`)

Tests effort estimation logic:

- ✅ `test_estimate_from_findings` - Estimates from findings
- ✅ `test_parse_days_string` - Parses time strings ("1-2 days", "2 weeks")
- ✅ `test_calculate_codebase_support` - Calculates pattern support percentage

**Coverage:** Time estimation, codebase support calculation

### 4. PM API Routes Tests (`TestPMAPIRoutes`)

Tests all PM-focused API endpoints with feature flag checks:

**PRD Changes:**
- ✅ `test_get_prd_changes_requires_feature_flag` - Feature flag enforcement
- ✅ `test_get_prd_changes_not_found` - 404 handling
- ✅ `test_get_prd_changes_success` - Successful retrieval
- ✅ `test_accept_change_requires_feature_flag` - Feature flag enforcement
- ✅ `test_reject_change_requires_feature_flag` - Feature flag enforcement

**Quality Scoring:**
- ✅ `test_get_quality_requires_feature_flag` - Feature flag enforcement
- ✅ `test_get_quality_success` - Successful retrieval

**Effort Estimation:**
- ✅ `test_get_estimate_requires_feature_flag` - Feature flag enforcement
- ✅ `test_get_estimate_success` - Successful retrieval

**Coverage:** All API endpoints, feature flag behavior, error handling

### 5. Expert Assist Tests (`TestExpertAssist`)

Tests expert assist (quick ask) functionality:

- ✅ `test_ask_expert_requires_feature_flag` - Feature flag enforcement
- ✅ `test_ask_expert_success` - Creates expert ask
- ✅ `test_respond_to_expert_ask_requires_feature_flag` - Feature flag enforcement
- ✅ `test_respond_to_expert_ask_success` - Expert responds
- ✅ `test_respond_to_nonexistent_ask` - 404 handling

**Coverage:** Expert ask workflow, error handling

### 6. Integration Tests (`TestPMFeaturesIntegration`)

End-to-end workflow tests:

- ✅ `test_full_pm_workflow` - Complete workflow:
  1. Create review with PM features
  2. Get PRD changes
  3. Accept change
  4. Get quality score
  5. Get effort estimate

**Coverage:** Full user journey

## Running Tests

### Prerequisites

Install test dependencies:

```bash
pip install -e ".[dev]"
```

### Run All PM Feature Tests

```bash
pytest src/context_graph/tests/test_pm_features.py -v
```

### Run Specific Test Class

```bash
# Test PRD change generator only
pytest src/context_graph/tests/test_pm_features.py::TestPRDChangeGenerator -v

# Test API routes only
pytest src/context_graph/tests/test_pm_features.py::TestPMAPIRoutes -v
```

### Run with Coverage

```bash
pytest src/context_graph/tests/test_pm_features.py --cov=context_graph.pm --cov-report=html
```

### Run All Tests (Including Collaboration)

```bash
pytest src/context_graph/tests/ -v
```

## Test Fixtures

### `client`
FastAPI test client for API endpoint testing.

### `enable_pm_features`
Enables all PM features for testing. Automatically resets after test.

### `sample_findings`
Sample findings (Security, Privacy, Engineering) for testing.

### `sample_prd_content`
Sample PRD content for testing change generation.

## Test Patterns

### Feature Flag Testing

All API endpoint tests verify:
1. Endpoint returns 403 when feature is disabled
2. Endpoint works when feature is enabled

Example:
```python
def test_get_prd_changes_requires_feature_flag(self, client):
    set_features(FeatureFlags())  # Disable all
    response = client.get("/api/reviews/test-review/changes")
    assert response.status_code == 403
```

### Mocking

Tests use `unittest.mock` to:
- Mock `reviews_store` for API tests
- Mock `review_status` for status checks
- Avoid actual database/file system access

### Assertions

Tests verify:
- HTTP status codes (200, 403, 404)
- Response structure (keys, types)
- Business logic correctness
- Feature flag behavior

## Coverage Goals

| Component | Target Coverage | Current Status |
|-----------|----------------|----------------|
| PRD Change Generator | 90%+ | ✅ Complete |
| PRD Quality Scorer | 85%+ | ✅ Complete |
| Effort Estimator | 85%+ | ✅ Complete |
| PM API Routes | 90%+ | ✅ Complete |
| Expert Assist | 85%+ | ✅ Complete |

## Frontend Tests

Frontend tests are located in `frontend/src/__tests__/components/pm/`:

### Test Files
- ✅ `PRDChangeCard.test.tsx` - Component rendering, interactions, edit mode
- ✅ `PRDChangesView.test.tsx` - Data fetching, mutations, actions
- ✅ `BulkAcceptPanel.test.tsx` - Selection, filters, bulk accept
- ✅ `PRDQualityScore.test.tsx` - Score display, stats, gaps
- ✅ `EffortEstimation.test.tsx` - Time range, codebase support, sprints
- ✅ `ExpertAskModal.test.tsx` - Expert selection, question editing, send

### Running Frontend Tests

```bash
cd frontend
npm install  # Install test dependencies
npm test     # Run tests
npm run test:coverage  # Run with coverage
```

### Frontend Test Coverage

| Component | Test Cases | Status |
|-----------|-----------|--------|
| PRDChangeCard | 12+ | ✅ Complete |
| PRDChangesView | 10+ | ✅ Complete |
| BulkAcceptPanel | 12+ | ✅ Complete |
| PRDQualityScore | 8+ | ✅ Complete |
| EffortEstimation | 8+ | ✅ Complete |
| ExpertAskModal | 12+ | ✅ Complete |

## Continuous Integration

Tests should run in CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Run PM Feature Tests
  run: |
    pip install -e ".[dev]"
    pytest src/context_graph/tests/test_pm_features.py -v --cov=context_graph.pm
```

## Adding New Tests

When adding new PM features:

1. **Add unit tests** for core logic (generator, scorer, estimator)
2. **Add API tests** with feature flag checks
3. **Add integration tests** for end-to-end workflows
4. **Update this document** with new test cases

### Test Template

```python
class TestNewFeature:
    """Test new feature."""
    
    def test_feature_requires_flag(self, client):
        """Feature should require feature flag."""
        set_features(FeatureFlags())
        response = client.get("/api/new-feature")
        assert response.status_code == 403
    
    def test_feature_success(self, client, enable_pm_features):
        """Feature should work when enabled."""
        response = client.get("/api/new-feature")
        assert response.status_code == 200
        # Add assertions
```

## Known Issues / TODO

- [ ] Add performance tests for large PRDs (1000+ lines)
- [ ] Add stress tests for bulk accept (100+ changes)
- [ ] Add edge case tests for malformed PRD content
- [ ] Add tests for pattern learning (when implemented)

## Test Data

Test fixtures use realistic but minimal data:
- Sample PRD: ~10 lines
- Sample findings: 3 findings (Security, Privacy, Engineering)
- Mock review IDs: "test-review", "review-1", etc.

For more complex scenarios, extend fixtures or create test-specific data.
