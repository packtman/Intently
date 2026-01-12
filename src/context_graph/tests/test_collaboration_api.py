"""
Tests for Collaboration API Routes

Tests cover:
- Phase 1: Finding Validation endpoints
- Phase 2: Comments endpoints
- Phase 3: Team Assignment endpoints
- Phase 4: Expert Feedback endpoints
- Phase 5: Advanced Features (Lifecycle, Cross-Team Requests, Consensus, Patterns)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from context_graph.api.main import app
from context_graph.config.features import FeatureFlags, set_features
from context_graph.storage.memory import InMemoryCollaborationStorage


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def enable_all_features():
    """Enable all collaboration features for testing."""
    set_features(FeatureFlags.all_enabled())
    yield
    set_features(FeatureFlags())  # Reset to defaults


@pytest.fixture
def storage():
    """Create a fresh storage instance for each test."""
    return InMemoryCollaborationStorage()


class TestFeatureFlags:
    """Test feature flag endpoint and functionality."""
    
    def test_get_features_returns_current_flags(self, client):
        """Feature flags endpoint should return current configuration."""
        response = client.get("/api/collaboration/features")
        assert response.status_code == 200
        data = response.json()
        
        # Should have all expected keys
        assert "validation" in data
        assert "team_assignment" in data
        assert "comments" in data
        assert "expert_feedback" in data
        assert "review_lifecycle" in data
        assert "cross_team_requests" in data
        assert "consensus_mode" in data
        assert "pattern_learning" in data


class TestPhase1FindingValidation:
    """Test finding validation endpoints."""
    
    def test_validate_finding_requires_feature_flag(self, client):
        """Validation endpoint should require feature flag."""
        # Reset to default (disabled)
        set_features(FeatureFlags())
        
        response = client.post(
            "/api/collaboration/reviews/test-review/findings/test-finding/validate",
            json={
                "status": "validated",
                "notes": "Test validation",
                "validator_id": "user-1",
                "validator_team": "security",
            }
        )
        assert response.status_code == 403
        assert "not enabled" in response.json()["detail"]
    
    def test_validate_finding_success(self, client, enable_all_features):
        """Should successfully validate a finding."""
        response = client.post(
            "/api/collaboration/reviews/test-review/findings/test-finding/validate",
            json={
                "status": "validated",
                "notes": "Confirmed issue",
                "validator_id": "user-1",
                "validator_team": "security",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "validated"
        assert data["validator_team"] == "security"
        assert "validated_at" in data
    
    def test_validate_finding_invalid_status(self, client, enable_all_features):
        """Should reject invalid validation status."""
        response = client.post(
            "/api/collaboration/reviews/test-review/findings/test-finding/validate",
            json={
                "status": "invalid_status",
                "notes": "Test",
                "validator_id": "user-1",
                "validator_team": "security",
            }
        )
        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]
    
    def test_get_finding_validation_pending(self, client, enable_all_features):
        """Should return pending status for unvalidated finding."""
        response = client.get(
            "/api/collaboration/reviews/test-review/findings/new-finding/validation"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["validated"] is False


class TestPhase2Comments:
    """Test comments endpoints."""
    
    def test_add_comment_requires_feature_flag(self, client):
        """Comments endpoint should require feature flag."""
        set_features(FeatureFlags())
        
        response = client.post(
            "/api/collaboration/reviews/test-review/findings/test-finding/comments",
            json={
                "content": "Test comment",
                "author_id": "user-1",
                "author_name": "Test User",
                "author_team": "security",
            }
        )
        assert response.status_code == 403
    
    def test_add_comment_success(self, client, enable_all_features):
        """Should successfully add a comment."""
        response = client.post(
            "/api/collaboration/reviews/test-review/findings/test-finding/comments",
            json={
                "content": "This looks like a real issue",
                "author_id": "user-1",
                "author_name": "Jane Smith",
                "author_team": "security",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "This looks like a real issue"
        assert data["author_name"] == "Jane Smith"
        assert "created_at" in data
    
    def test_add_reply_comment(self, client, enable_all_features):
        """Should successfully add a reply to a comment."""
        # First add a parent comment
        parent_response = client.post(
            "/api/collaboration/reviews/test-review/findings/test-finding/comments",
            json={
                "content": "Original comment",
                "author_id": "user-1",
                "author_name": "Jane",
                "author_team": "security",
            }
        )
        parent_id = parent_response.json()["id"]
        
        # Add reply
        response = client.post(
            "/api/collaboration/reviews/test-review/findings/test-finding/comments",
            json={
                "content": "This is a reply",
                "author_id": "user-2",
                "author_name": "Bob",
                "author_team": "engineering",
                "parent_comment_id": parent_id,
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["parent_comment_id"] == parent_id
    
    def test_get_comments(self, client, enable_all_features):
        """Should retrieve comments for a finding."""
        # Add a comment first
        client.post(
            "/api/collaboration/reviews/test-review/findings/test-finding/comments",
            json={
                "content": "Test comment",
                "author_id": "user-1",
                "author_name": "Test",
                "author_team": "security",
            }
        )
        
        response = client.get(
            "/api/collaboration/reviews/test-review/findings/test-finding/comments"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1


class TestPhase3TeamAssignment:
    """Test team assignment endpoints."""
    
    def test_assign_finding_requires_feature_flag(self, client):
        """Assignment endpoint should require feature flag."""
        set_features(FeatureFlags())
        
        response = client.post(
            "/api/collaboration/reviews/test-review/findings/test-finding/assign",
            json={
                "team": "security",
            }
        )
        assert response.status_code == 403
    
    def test_assign_finding_success(self, client, enable_all_features):
        """Should successfully assign a finding to a team."""
        response = client.post(
            "/api/collaboration/reviews/test-review/findings/test-finding/assign",
            json={
                "team": "security",
                "assigned_by": "user-1",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["team"] == "security"
        assert "assigned_at" in data
    
    def test_get_team_queue(self, client, enable_all_features):
        """Should retrieve team queue."""
        # First assign some findings
        client.post(
            "/api/collaboration/reviews/review-1/findings/finding-1/assign",
            json={"team": "security"}
        )
        client.post(
            "/api/collaboration/reviews/review-2/findings/finding-2/assign",
            json={"team": "security"}
        )
        
        response = client.get("/api/collaboration/teams/security/queue")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2


class TestPhase4ExpertFeedback:
    """Test expert feedback endpoints."""
    
    def test_submit_feedback_requires_feature_flag(self, client):
        """Feedback endpoint should require feature flag."""
        set_features(FeatureFlags())
        
        response = client.post(
            "/api/collaboration/reviews/test-review/findings/test-finding/feedback",
            json={
                "feedback_type": "accuracy",
                "original_value": "valid",
                "expert_value": "false_positive",
                "expert_id": "user-1",
                "expert_team": "security",
                "reasoning": "This is not applicable",
            }
        )
        assert response.status_code == 403
    
    def test_submit_feedback_success(self, client, enable_all_features):
        """Should successfully submit expert feedback."""
        response = client.post(
            "/api/collaboration/reviews/test-review/findings/test-finding/feedback",
            json={
                "feedback_type": "severity",
                "original_value": "medium",
                "expert_value": "high",
                "expert_id": "user-1",
                "expert_team": "security",
                "reasoning": "External exposure increases risk",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["feedback_type"] == "severity"
        assert data["expert_value"] == "high"
    
    def test_submit_feedback_invalid_type(self, client, enable_all_features):
        """Should reject invalid feedback type."""
        response = client.post(
            "/api/collaboration/reviews/test-review/findings/test-finding/feedback",
            json={
                "feedback_type": "invalid_type",
                "original_value": "test",
                "expert_value": "test",
                "expert_id": "user-1",
                "expert_team": "security",
                "reasoning": "Test",
            }
        )
        assert response.status_code == 400


class TestPhase5ReviewLifecycle:
    """Test review lifecycle endpoints."""
    
    def test_update_lifecycle_requires_feature_flag(self, client):
        """Lifecycle endpoint should require feature flag."""
        set_features(FeatureFlags())
        
        response = client.post(
            "/api/collaboration/reviews/test-review/lifecycle",
            json={
                "state": "in_review",
                "updated_by": "user-1",
            }
        )
        assert response.status_code == 403
    
    def test_update_lifecycle_success(self, client, enable_all_features):
        """Should successfully update lifecycle state."""
        response = client.post(
            "/api/collaboration/reviews/test-review/lifecycle",
            json={
                "state": "team_review",
                "updated_by": "user-1",
                "notes": "Assigned to teams",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "team_review"
    
    def test_get_lifecycle_history(self, client, enable_all_features):
        """Should track lifecycle history."""
        # Update state multiple times
        client.post(
            "/api/collaboration/reviews/history-test/lifecycle",
            json={"state": "in_review", "updated_by": "user-1"}
        )
        client.post(
            "/api/collaboration/reviews/history-test/lifecycle",
            json={"state": "team_review", "updated_by": "user-1"}
        )
        
        response = client.get("/api/collaboration/reviews/history-test/lifecycle/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2


class TestPhase5CrossTeamRequests:
    """Test cross-team request endpoints."""
    
    def test_create_review_request_success(self, client, enable_all_features):
        """Should successfully create a cross-team request."""
        response = client.post(
            "/api/collaboration/reviews/test-review/requests",
            json={
                "finding_id": "finding-1",
                "requesting_team": "security",
                "target_team": "architecture",
                "question": "Can you assess scalability impact?",
                "requested_by": "user-1",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["target_team"] == "architecture"
        assert data["status"] == "pending"
    
    def test_respond_to_request(self, client, enable_all_features):
        """Should successfully respond to a request."""
        # Create request first
        create_response = client.post(
            "/api/collaboration/reviews/test-review/requests",
            json={
                "finding_id": "finding-1",
                "requesting_team": "security",
                "target_team": "architecture",
                "question": "Need your input",
                "requested_by": "user-1",
            }
        )
        request_id = create_response.json()["id"]
        
        # Respond
        response = client.post(
            f"/api/collaboration/requests/{request_id}/respond",
            json={
                "response": "The design should scale fine",
                "responded_by": "user-2",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "responded"
        assert data["response"] == "The design should scale fine"


class TestPhase5ConsensusMode:
    """Test consensus mode endpoints."""
    
    def test_add_consensus_vote(self, client, enable_all_features):
        """Should successfully add a consensus vote."""
        response = client.post(
            "/api/collaboration/reviews/test-review/findings/finding-1/consensus",
            json={
                "team": "security",
                "vote": "approve",
                "voter_id": "user-1",
                "notes": "Confirmed critical",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["vote"] == "approve"
        assert data["team"] == "security"
    
    def test_get_consensus_status(self, client, enable_all_features):
        """Should retrieve consensus status with vote counts."""
        # Add multiple votes
        client.post(
            "/api/collaboration/reviews/test-review/findings/finding-1/consensus",
            json={"team": "security", "vote": "approve", "voter_id": "user-1"}
        )
        client.post(
            "/api/collaboration/reviews/test-review/findings/finding-1/consensus",
            json={"team": "privacy", "vote": "approve", "voter_id": "user-2"}
        )
        
        response = client.get(
            "/api/collaboration/reviews/test-review/findings/finding-1/consensus"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_votes"] >= 2
        assert "vote_counts" in data
        assert "has_consensus" in data


class TestPhase5PatternLearning:
    """Test pattern learning endpoints."""
    
    def test_save_pattern(self, client, enable_all_features):
        """Should successfully save a learned pattern."""
        response = client.post(
            "/api/collaboration/patterns",
            json={
                "pattern_type": "false_positive",
                "pattern_signature": "CSRF on API-only endpoint",
                "decision": "not_applicable",
                "conditions": ["API-only", "Token auth"],
                "reasoning": "CSRF requires cookie-based sessions",
                "source_feedback_ids": ["fb-1", "fb-2"],
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pattern_type"] == "false_positive"
        assert data["times_applied"] == 0
    
    def test_get_pattern_insights(self, client, enable_all_features):
        """Should retrieve pattern learning insights."""
        response = client.get("/api/collaboration/patterns/insights")
        assert response.status_code == 200
        data = response.json()
        assert "total_patterns" in data
        assert "by_type" in data
        assert "by_decision" in data


class TestStorageIntegration:
    """Test storage layer integration."""
    
    @pytest.mark.asyncio
    async def test_validation_persistence(self, storage):
        """Validations should persist correctly."""
        result = await storage.save_finding_validation(
            review_id="review-1",
            finding_id="finding-1",
            status="validated",
            validator_id="user-1",
            validator_team="security",
            notes="Confirmed",
        )
        
        assert result["status"] == "validated"
        
        # Retrieve
        validation = await storage.get_finding_validation("review-1", "finding-1")
        assert validation is not None
        assert validation["status"] == "validated"
    
    @pytest.mark.asyncio
    async def test_comment_threading(self, storage):
        """Comments should support threading."""
        # Add parent comment
        parent = await storage.add_comment(
            review_id="review-1",
            finding_id="finding-1",
            author_id="user-1",
            author_name="Jane",
            author_team="security",
            content="Parent comment",
        )
        
        # Add reply
        reply = await storage.add_comment(
            review_id="review-1",
            finding_id="finding-1",
            author_id="user-2",
            author_name="Bob",
            author_team="engineering",
            content="Reply",
            parent_comment_id=parent["id"],
        )
        
        assert reply["parent_comment_id"] == parent["id"]
        
        # Get all comments
        comments = await storage.get_comments("review-1", "finding-1")
        assert len(comments) == 2
    
    @pytest.mark.asyncio
    async def test_team_queue_filtering(self, storage):
        """Team queue should filter by team correctly."""
        await storage.assign_finding("review-1", "finding-1", "security")
        await storage.assign_finding("review-1", "finding-2", "privacy")
        await storage.assign_finding("review-2", "finding-3", "security")
        
        security_queue = await storage.get_team_queue("security")
        privacy_queue = await storage.get_team_queue("privacy")
        
        assert len(security_queue) == 2
        assert len(privacy_queue) == 1

