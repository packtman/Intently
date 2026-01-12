"""
Tests for PM-Focused Features (Unified PM Tool)

Tests cover:
- PRD Change Generator
- PRD Quality Scorer
- Effort Estimator
- PM API Routes (feature-flagged)
- Expert Assist
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from uuid import uuid4

from context_graph.api.main import app
from context_graph.config.features import FeatureFlags, set_features
from context_graph.core.models import (
    SecurityFinding,
    PrivacyFinding,
    EngineeringFinding,
    ReviewDimension,
    Severity,
    ThreatCategory,
    PrivacyCategory,
    EngineeringCategory,
    Intent,
    State,
)
from context_graph.pm.prd_change_generator import PRDChangeGenerator
from context_graph.pm.quality_scorer import PRDQualityScorer
from context_graph.pm.effort_estimator import EffortEstimator
from context_graph.security.review_engine import ReviewResult


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def enable_pm_features():
    """Enable all PM features for testing."""
    flags = FeatureFlags()
    flags.enable_prd_changes = True
    flags.enable_prd_quality_scoring = True
    flags.enable_effort_estimation = True
    flags.enable_expert_assist = True
    set_features(flags)
    yield
    set_features(FeatureFlags())  # Reset to defaults


@pytest.fixture
def sample_findings():
    """Create sample findings for testing."""
    return [
        SecurityFinding(
            id=uuid4(),
            title="Missing rate limiting",
            description="No rate limiting found in codebase",
            severity=Severity.HIGH,
            category=ThreatCategory.DENIAL_OF_SERVICE,
            dimension=ReviewDimension.SECURITY,
            recommendation="Add rate limiting: 100 requests/minute per user",
            source_reference="api/auth.py:45",
        ),
        PrivacyFinding(
            id=uuid4(),
            title="GDPR compliance not mentioned",
            description="PRD doesn't mention GDPR requirements",
            severity=Severity.MEDIUM,
            category=PrivacyCategory.NON_COMPLIANCE,
            dimension=ReviewDimension.PRIVACY,
            recommendation="Add GDPR compliance section",
        ),
        EngineeringFinding(
            id=uuid4(),
            title="High complexity code",
            description="Function has cyclomatic complexity of 15",
            severity=Severity.MEDIUM,
            category=EngineeringCategory.HIGH_COMPLEXITY,
            dimension=ReviewDimension.ENGINEERING,
            estimated_days="2-3 days",
            affected_files=["src/main.py"],
        ),
    ]


@pytest.fixture
def sample_prd_content():
    """Sample PRD content for testing."""
    return """# User Authentication Feature

## Overview
Implement user authentication with email/password.

## Features
- User registration
- User login
- Password reset

## Technical Requirements
- User authentication via OAuth 2.0
- Support for Google and GitHub providers
- JWT tokens for session management
"""


# ==================== PRD Change Generator Tests ====================

class TestPRDChangeGenerator:
    """Test PRD change generator."""
    
    def test_generate_changes_from_findings(self, sample_findings, sample_prd_content):
        """Should generate PRD changes from findings."""
        generator = PRDChangeGenerator()
        
        changes = generator.generate_changes(
            findings=sample_findings,
            prd_content=sample_prd_content,
        )
        
        assert len(changes) == 3
        assert all(c.suggested_change is not None for c in changes)
    
    def test_generate_question_text(self, sample_findings):
        """Should generate appropriate question text."""
        generator = PRDChangeGenerator()
        
        question = generator._finding_to_question(sample_findings[0], None)
        
        assert question.question.endswith("?")
        assert question.team == "security"
        assert question.severity == "blocker"  # HIGH severity -> blocker
    
    def test_extract_code_evidence(self, sample_findings):
        """Should extract code evidence from findings."""
        generator = PRDChangeGenerator()
        
        question = generator._finding_to_question(sample_findings[0], None)
        
        assert len(question.code_evidence) > 0
        assert question.code_evidence[0].file_path == "api/auth.py"
    
    def test_determine_section(self, sample_findings):
        """Should determine correct PRD section for changes."""
        generator = PRDChangeGenerator()
        
        section = generator._determine_section(sample_findings[0])
        assert section == "## Security Requirements"
        
        section = generator._determine_section(sample_findings[1])
        assert section == "## Privacy Requirements"
        
        section = generator._determine_section(sample_findings[2])
        assert section == "## Technical Requirements"
    
    def test_generate_diff_hunks(self, sample_prd_content):
        """Should generate diff hunks for rendering."""
        generator = PRDChangeGenerator()
        
        hunks = generator._generate_diff_hunks(
            current_text="",
            suggested_text="- Rate limiting: 100 requests/minute",
            start_line=10,
        )
        
        assert len(hunks) == 1
        assert hunks[0].operation == "add"
        assert "rate limiting" in hunks[0].content.lower()


# ==================== PRD Quality Scorer Tests ====================

class TestPRDQualityScorer:
    """Test PRD quality scorer."""
    
    def test_calculate_score_no_questions(self, sample_prd_content):
        """Should calculate score when no questions."""
        scorer = PRDQualityScorer()
        
        score = scorer.calculate_score([], sample_prd_content)
        
        assert score.score >= 90  # High score with no issues
        assert score.grade in ["A", "B"]
    
    def test_calculate_score_with_blockers(self, sample_prd_content):
        """Should penalize blockers heavily."""
        from context_graph.core.models import PredictedQuestion
        
        questions = [
            PredictedQuestion(
                question="What about rate limiting?",
                team="security",
                severity="blocker",
            ),
            PredictedQuestion(
                question="What about GDPR?",
                team="privacy",
                severity="blocker",
            ),
        ]
        
        scorer = PRDQualityScorer()
        score = scorer.calculate_score(questions, sample_prd_content)
        
        assert score.score < 90  # Penalized for blockers
        assert score.blockers == 2
        assert score.predicted_pushback == 2
    
    def test_identify_gaps(self):
        """Should identify key gaps in PRD."""
        from context_graph.core.models import PredictedQuestion
        
        questions = [
            PredictedQuestion(team="security", severity="blocker"),
            PredictedQuestion(team="security", severity="likely"),
            PredictedQuestion(team="privacy", severity="blocker"),
        ]
        
        scorer = PRDQualityScorer()
        score = scorer.calculate_score(questions, "")
        
        assert len(score.gaps) > 0
        assert any("security" in gap.lower() for gap in score.gaps)


# ==================== Effort Estimator Tests ====================

class TestEffortEstimator:
    """Test effort estimator."""
    
    def test_estimate_from_findings(self, sample_findings):
        """Should estimate effort from findings."""
        estimator = EffortEstimator()
        
        estimation = estimator.estimate(sample_findings, None)
        
        assert estimation.total_days["min"] > 0
        assert estimation.total_days["likely"] > 0
        assert estimation.total_days["max"] > 0
        assert len(estimation.by_requirement) == 3
    
    def test_parse_days_string(self):
        """Should parse days strings correctly."""
        estimator = EffortEstimator()
        
        result = estimator._parse_days_string("1-2 days")
        assert result["min"] == 1
        assert result["likely"] == 1
        assert result["max"] == 2
        
        result = estimator._parse_days_string("2 weeks")
        assert result["min"] == 14
        assert result["likely"] == 14
        assert result["max"] == 28
    
    def test_calculate_codebase_support(self, sample_findings):
        """Should calculate codebase support percentage."""
        from context_graph.core.models import State
        
        state = State()
        state.api_endpoints = [{"path": "/api/auth"}]
        
        estimator = EffortEstimator()
        estimation = estimator.estimate(sample_findings, state)
        
        assert 0 <= estimation.codebase_support <= 100


# ==================== PM API Routes Tests ====================

class TestPMAPIRoutes:
    """Test PM-focused API routes."""
    
    def test_get_prd_changes_requires_feature_flag(self, client):
        """PRD changes endpoint should require feature flag."""
        set_features(FeatureFlags())  # Disable all
        
        response = client.get("/api/reviews/test-review/changes")
        assert response.status_code == 403
        assert "not enabled" in response.json()["detail"]
    
    def test_get_prd_changes_not_found(self, client, enable_pm_features):
        """Should return 404 for non-existent review."""
        response = client.get("/api/reviews/non-existent/changes")
        assert response.status_code == 404
    
    @patch('context_graph.api.pm_routes.reviews_store')
    def test_get_prd_changes_success(self, mock_store, client, enable_pm_features, sample_findings, sample_prd_content):
        """Should return PRD changes for a review."""
        from context_graph.core.models import PredictedQuestion, PRDChange
        
        # Create mock review result
        review_result = ReviewResult()
        review_result.original_prd_content = sample_prd_content
        
        # Create predicted questions with changes
        change = PRDChange(
            section="## Security Requirements",
            change_type="addition",
            suggested_text="- Rate limiting: 100 requests/minute",
            reasoning="No rate limiting found",
        )
        question = PredictedQuestion(
            question="What about rate limiting?",
            team="security",
            severity="blocker",
            suggested_change=change,
        )
        review_result.predicted_questions = [question]
        
        mock_store["test-review"] = review_result
        
        response = client.get("/api/reviews/test-review/changes")
        assert response.status_code == 200
        data = response.json()
        assert "changes" in data
        assert "summary" in data
        assert len(data["changes"]) == 1
    
    def test_accept_change_requires_feature_flag(self, client):
        """Accept change endpoint should require feature flag."""
        set_features(FeatureFlags())
        
        response = client.post("/api/reviews/test-review/changes/change-1/accept")
        assert response.status_code == 403
    
    def test_reject_change_requires_feature_flag(self, client):
        """Reject change endpoint should require feature flag."""
        set_features(FeatureFlags())
        
        response = client.post("/api/reviews/test-review/changes/change-1/reject")
        assert response.status_code == 403
    
    def test_get_quality_requires_feature_flag(self, client):
        """Quality endpoint should require feature flag."""
        set_features(FeatureFlags())
        
        response = client.get("/api/reviews/test-review/quality")
        assert response.status_code == 403
    
    @patch('context_graph.api.pm_routes.reviews_store')
    def test_get_quality_success(self, mock_store, client, enable_pm_features):
        """Should return quality score."""
        from context_graph.core.models import PRDQualityScore
        
        review_result = ReviewResult()
        review_result.prd_quality_score = PRDQualityScore(
            score=72,
            grade="C",
            blockers=4,
            likely_questions=2,
        )
        
        mock_store["test-review"] = review_result
        
        response = client.get("/api/reviews/test-review/quality")
        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 72
        assert data["grade"] == "C"
        assert data["blockers"] == 4
    
    def test_get_estimate_requires_feature_flag(self, client):
        """Estimate endpoint should require feature flag."""
        set_features(FeatureFlags())
        
        response = client.get("/api/reviews/test-review/estimate")
        assert response.status_code == 403
    
    @patch('context_graph.api.pm_routes.reviews_store')
    def test_get_estimate_success(self, mock_store, client, enable_pm_features):
        """Should return effort estimation."""
        from context_graph.core.models import EffortEstimation
        
        review_result = ReviewResult()
        review_result.effort_estimation = EffortEstimation(
            total_days={"min": 14, "likely": 18, "max": 24},
            codebase_support=72.0,
            tldr="18 days, 3 sprints",
        )
        
        mock_store["test-review"] = review_result
        
        response = client.get("/api/reviews/test-review/estimate")
        assert response.status_code == 200
        data = response.json()
        assert data["total_days"]["likely"] == 18
        assert data["codebase_support"] == 72.0
        assert "tldr" in data


# ==================== Expert Assist Tests ====================

class TestExpertAssist:
    """Test expert assist endpoints."""
    
    def test_ask_expert_requires_feature_flag(self, client):
        """Expert ask endpoint should require feature flag."""
        set_features(FeatureFlags())
        
        response = client.post(
            "/api/expert-assist/ask",
            json={
                "prediction_id": "pred-1",
                "expert_id": "expert-1",
                "expert_name": "Bob",
                "question": "Is this correct?",
            }
        )
        assert response.status_code == 403
    
    def test_ask_expert_success(self, client, enable_pm_features):
        """Should successfully create expert ask."""
        response = client.post(
            "/api/expert-assist/ask",
            json={
                "prediction_id": "pred-1",
                "expert_id": "expert-1",
                "expert_name": "Bob Wilson",
                "question": "Is rate limiting configured correctly?",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "ask_id" in data
    
    def test_respond_to_expert_ask_requires_feature_flag(self, client):
        """Expert response endpoint should require feature flag."""
        set_features(FeatureFlags())
        
        response = client.post(
            "/api/expert-assist/respond/ask-1",
            json={
                "verdict": "correct",
                "note": "Looks good",
            }
        )
        assert response.status_code == 403
    
    def test_respond_to_expert_ask_success(self, client, enable_pm_features):
        """Should successfully respond to expert ask."""
        # First create an ask
        ask_response = client.post(
            "/api/expert-assist/ask",
            json={
                "prediction_id": "pred-1",
                "expert_id": "expert-1",
                "expert_name": "Bob",
                "question": "Is this correct?",
            }
        )
        ask_id = ask_response.json()["ask_id"]
        
        # Respond
        response = client.post(
            f"/api/expert-assist/respond/{ask_id}",
            json={
                "verdict": "wrong",
                "note": "Rate limiting exists in API gateway",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["responded"] is True
    
    def test_respond_to_nonexistent_ask(self, client, enable_pm_features):
        """Should return 404 for non-existent ask."""
        response = client.post(
            "/api/expert-assist/respond/non-existent",
            json={
                "verdict": "correct",
            }
        )
        assert response.status_code == 404


# ==================== Integration Tests ====================

class TestPMFeaturesIntegration:
    """Integration tests for PM features."""
    
    @patch('context_graph.api.routes.reviews_store')
    @patch('context_graph.api.routes.review_status')
    def test_full_pm_workflow(self, mock_status, mock_store, client, enable_pm_features, sample_findings, sample_prd_content):
        """Test complete PM workflow: review -> changes -> accept."""
        from context_graph.core.models import PredictedQuestion, PRDChange, PRDQualityScore, EffortEstimation
        
        # Create a complete review result
        review_result = ReviewResult()
        review_result.original_prd_content = sample_prd_content
        
        # Add predicted questions
        change = PRDChange(
            id=uuid4(),
            section="## Security Requirements",
            change_type="addition",
            suggested_text="- Rate limiting: 100 requests/minute",
            reasoning="No rate limiting found",
        )
        question = PredictedQuestion(
            id=uuid4(),
            question="What about rate limiting?",
            team="security",
            severity="blocker",
            suggested_change=change,
        )
        review_result.predicted_questions = [question]
        review_result.prd_quality_score = PRDQualityScore(score=65, grade="D", blockers=1)
        review_result.effort_estimation = EffortEstimation(
            total_days={"min": 5, "likely": 7, "max": 10},
            codebase_support=60.0,
        )
        
        mock_store["test-review"] = review_result
        mock_status["test-review"] = {"status": "completed", "progress": 100}
        
        # 1. Get changes
        changes_response = client.get("/api/reviews/test-review/changes")
        assert changes_response.status_code == 200
        changes_data = changes_response.json()
        assert len(changes_data["changes"]) == 1
        
        change_id = changes_data["changes"][0]["id"]
        
        # 2. Accept change
        accept_response = client.post(
            f"/api/reviews/test-review/changes/{change_id}/accept"
        )
        assert accept_response.status_code == 200
        assert accept_response.json()["applied"] is True
        
        # 3. Get quality score
        quality_response = client.get("/api/reviews/test-review/quality")
        assert quality_response.status_code == 200
        assert quality_response.json()["score"] == 65
        
        # 4. Get effort estimate
        estimate_response = client.get("/api/reviews/test-review/estimate")
        assert estimate_response.status_code == 200
        assert estimate_response.json()["total_days"]["likely"] == 7


class TestAdditionalPMFeatures:
    """Test additional PM features: undo, download, re-analyze, preferences."""
    
    def test_undo_change_requires_feature_flag(self, client):
        """Undo endpoint should require feature flag."""
        set_features(FeatureFlags())
        
        response = client.post("/api/reviews/test-review/changes/undo")
        assert response.status_code == 403
    
    @patch('context_graph.api.pm_routes.reviews_store')
    @patch('context_graph.api.pm_routes.prd_history_store')
    def test_undo_change_success(self, mock_history, mock_store, client, enable_pm_features):
        """Should successfully undo last change."""
        from context_graph.core.models import PredictedQuestion, PRDChange
        
        review_result = ReviewResult()
        review_result.original_prd_content = "Original PRD"
        
        change = PRDChange(
            id=uuid4(),
            section="## Security",
            suggested_text="- Rate limiting",
            status="accepted",
        )
        question = PredictedQuestion(
            id=uuid4(),
            question="What about rate limiting?",
            suggested_change=change,
        )
        review_result.predicted_questions = [question]
        
        mock_store["test-review"] = review_result
        mock_history["test-review"] = ["Original PRD", "Original PRD\n- Rate limiting"]
        
        response = client.post("/api/reviews/test-review/changes/undo")
        assert response.status_code == 200
        data = response.json()
        assert data["reverted"] is True
        assert "restored_prd" in data
    
    def test_download_prd_requires_feature_flag(self, client):
        """Download endpoint should require feature flag."""
        set_features(FeatureFlags())
        
        response = client.get("/api/reviews/test-review/prd/download")
        assert response.status_code == 403
    
    @patch('context_graph.api.pm_routes.reviews_store')
    def test_download_prd_success(self, mock_store, client, enable_pm_features):
        """Should successfully download updated PRD."""
        review_result = ReviewResult()
        review_result.intent.title = "Test PRD"
        review_result.original_prd_content = "# Test PRD\n\nContent"
        
        mock_store["test-review"] = review_result
        
        response = client.get("/api/reviews/test-review/prd/download")
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "filename" in data
        assert data["filename"].endswith(".md")
    
    def test_re_analyze_requires_feature_flag(self, client):
        """Re-analyze endpoint should require feature flag."""
        set_features(FeatureFlags())
        
        response = client.post("/api/reviews/test-review/re-analyze")
        assert response.status_code == 403
    
    @patch('context_graph.api.pm_routes.reviews_store')
    def test_re_analyze_success(self, mock_store, client, enable_pm_features, sample_findings):
        """Should successfully re-analyze PRD."""
        review_result = ReviewResult()
        review_result.intent.title = "Test PRD"
        review_result.intent.raw_content = "# Test PRD\n\nUpdated content"
        review_result.original_prd_content = "# Test PRD\n\nUpdated content"
        review_result.state = State()  # Mock state
        review_result.all_findings = sample_findings
        
        mock_store["test-review"] = review_result
        
        response = client.post("/api/reviews/test-review/re-analyze")
        assert response.status_code == 200
        data = response.json()
        assert data["re_analyzed"] is True
    
    def test_get_preferences_requires_feature_flag(self, client):
        """Preferences endpoint should require feature flag."""
        set_features(FeatureFlags())
        
        response = client.get("/api/preferences")
        assert response.status_code == 403
    
    def test_get_preferences_success(self, client, enable_pm_features):
        """Should return default preferences."""
        response = client.get("/api/preferences?user_id=test-user")
        assert response.status_code == 200
        data = response.json()
        assert "feedback_teams" in data
        assert "severity_filter" in data
    
    def test_update_preferences_success(self, client, enable_pm_features):
        """Should successfully update preferences."""
        response = client.put(
            "/api/preferences?user_id=test-user",
            json={
                "feedback_teams": ["engineering", "security"],
                "severity_filter": ["blocker"],
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["feedback_teams"] == ["engineering", "security"]
        assert data["severity_filter"] == ["blocker"]
    
    def test_mute_pattern_success(self, client, enable_pm_features):
        """Should successfully mute a pattern."""
        response = client.post(
            "/api/preferences/mute?user_id=test-user",
            json={
                "pattern_description": "GDPR compliance suggestions",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["learned"] is True
        assert "pattern_id" in data
    
    def test_get_pattern_insights_requires_feature_flag(self, client):
        """Pattern insights endpoint should require feature flag."""
        set_features(FeatureFlags())
        
        response = client.get("/api/patterns/insights")
        assert response.status_code == 403
    
    def test_get_pattern_insights_success(self, client, enable_pm_features):
        """Should return pattern insights."""
        response = client.get("/api/patterns/insights")
        assert response.status_code == 200
        data = response.json()
        assert "total_patterns" in data
        assert "by_type" in data
