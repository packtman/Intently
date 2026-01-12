"""
Abstract base classes for storage backends.

These interfaces allow swapping storage implementations without changing
the rest of the application. Start with in-memory, upgrade to SQLite/Postgres later.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from context_graph.security.review_engine import ReviewResult


class ReviewStorage(ABC):
    """
    Abstract interface for review storage.
    
    Implementations:
    - InMemoryReviewStorage: Current behavior, for development/testing
    - SQLiteReviewStorage: Persistent local storage (future)
    - PostgresReviewStorage: Production storage (future)
    """
    
    @abstractmethod
    async def save_review(self, review_id: str, result: ReviewResult) -> None:
        """Save a review result."""
        pass
    
    @abstractmethod
    async def get_review(self, review_id: str) -> ReviewResult | None:
        """Get a review by ID. Returns None if not found."""
        pass
    
    @abstractmethod
    async def delete_review(self, review_id: str) -> bool:
        """Delete a review. Returns True if deleted, False if not found."""
        pass
    
    @abstractmethod
    async def list_reviews(self) -> list[dict[str, Any]]:
        """List all reviews with summary info."""
        pass
    
    @abstractmethod
    async def update_review_status(
        self, 
        review_id: str, 
        status: str, 
        progress: float, 
        message: str,
        dimensions: list[str] | None = None,
    ) -> None:
        """Update the status of a running review."""
        pass
    
    @abstractmethod
    async def get_review_status(self, review_id: str) -> dict[str, Any] | None:
        """Get the current status of a review."""
        pass


class CollaborationStorage(ABC):
    """
    Abstract interface for collaboration data storage.
    
    Handles:
    - Finding validations
    - Comments
    - Team assignments
    - Expert feedback
    
    This is separate from ReviewStorage to allow independent evolution
    and to keep collaboration concerns isolated.
    """
    
    # ==================== Finding Validation ====================
    
    @abstractmethod
    async def save_finding_validation(
        self,
        review_id: str,
        finding_id: str,
        status: str,
        validator_id: str,
        validator_team: str,
        notes: str,
    ) -> dict[str, Any]:
        """Save a validation decision for a finding."""
        pass
    
    @abstractmethod
    async def get_finding_validation(
        self,
        review_id: str,
        finding_id: str,
    ) -> dict[str, Any] | None:
        """Get the current validation status for a finding."""
        pass
    
    @abstractmethod
    async def get_validations_for_review(
        self,
        review_id: str,
    ) -> dict[str, dict[str, Any]]:
        """Get all validations for a review, keyed by finding_id."""
        pass
    
    # ==================== Comments ====================
    
    @abstractmethod
    async def add_comment(
        self,
        review_id: str,
        finding_id: str,
        author_id: str,
        author_name: str,
        author_team: str,
        content: str,
        parent_comment_id: str | None = None,
    ) -> dict[str, Any]:
        """Add a comment to a finding."""
        pass
    
    @abstractmethod
    async def get_comments(
        self,
        review_id: str,
        finding_id: str,
    ) -> list[dict[str, Any]]:
        """Get all comments for a finding."""
        pass
    
    @abstractmethod
    async def get_comment_counts(
        self,
        review_id: str,
    ) -> dict[str, int]:
        """Get comment counts for all findings in a review, keyed by finding_id."""
        pass
    
    @abstractmethod
    async def delete_comment(
        self,
        comment_id: str,
    ) -> bool:
        """Soft-delete a comment. Returns True if deleted."""
        pass
    
    # ==================== Team Assignment ====================
    
    @abstractmethod
    async def assign_finding(
        self,
        review_id: str,
        finding_id: str,
        team: str,
        user_id: str | None = None,
        assigned_by: str | None = None,
    ) -> dict[str, Any]:
        """Assign a finding to a team/user."""
        pass
    
    @abstractmethod
    async def get_assignments_for_review(
        self,
        review_id: str,
    ) -> dict[str, dict[str, Any]]:
        """Get all assignments for a review, keyed by finding_id."""
        pass
    
    @abstractmethod
    async def get_team_queue(
        self,
        team: str,
    ) -> list[dict[str, Any]]:
        """Get all findings assigned to a team across all reviews."""
        pass
    
    # ==================== Expert Feedback ====================
    
    @abstractmethod
    async def save_expert_feedback(
        self,
        review_id: str,
        finding_id: str,
        feedback_type: str,
        original_value: str,
        expert_value: str,
        expert_id: str,
        expert_team: str,
        reasoning: str,
    ) -> dict[str, Any]:
        """Save expert feedback on a finding."""
        pass
    
    @abstractmethod
    async def get_feedback_for_finding(
        self,
        review_id: str,
        finding_id: str,
    ) -> list[dict[str, Any]]:
        """Get all expert feedback for a finding."""
        pass
    
    @abstractmethod
    async def get_feedback_stats(self) -> dict[str, Any]:
        """Get aggregated feedback statistics for learning."""
        pass

    # ==================== Review Lifecycle (Phase 5) ====================
    
    @abstractmethod
    async def update_review_lifecycle(
        self,
        review_id: str,
        state: str,
        updated_by: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Update the lifecycle state of a review."""
        pass
    
    @abstractmethod
    async def get_review_lifecycle(
        self,
        review_id: str,
    ) -> dict[str, Any] | None:
        """Get the current lifecycle state of a review."""
        pass
    
    @abstractmethod
    async def get_lifecycle_history(
        self,
        review_id: str,
    ) -> list[dict[str, Any]]:
        """Get lifecycle state history for a review."""
        pass
    
    # ==================== Cross-Team Requests (Phase 5) ====================
    
    @abstractmethod
    async def create_review_request(
        self,
        review_id: str,
        finding_id: str,
        requesting_team: str,
        target_team: str,
        question: str,
        requested_by: str,
        deadline: str | None = None,
    ) -> dict[str, Any]:
        """Create a cross-team review request."""
        pass
    
    @abstractmethod
    async def get_review_requests(
        self,
        review_id: str | None = None,
        target_team: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get review requests filtered by review or target team."""
        pass
    
    @abstractmethod
    async def respond_to_request(
        self,
        request_id: str,
        response: str,
        responded_by: str,
    ) -> dict[str, Any]:
        """Respond to a cross-team review request."""
        pass
    
    # ==================== Consensus Mode (Phase 5) ====================
    
    @abstractmethod
    async def add_consensus_vote(
        self,
        review_id: str,
        finding_id: str,
        team: str,
        vote: str,
        voter_id: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Add a consensus vote for a finding."""
        pass
    
    @abstractmethod
    async def get_consensus_status(
        self,
        review_id: str,
        finding_id: str,
    ) -> dict[str, Any]:
        """Get consensus voting status for a finding."""
        pass
    
    # ==================== Pattern Learning (Phase 5) ====================
    
    @abstractmethod
    async def save_learned_pattern(
        self,
        pattern_type: str,
        pattern_signature: str,
        decision: str,
        conditions: list[str],
        reasoning: str,
        source_feedback_ids: list[str],
    ) -> dict[str, Any]:
        """Save a learned pattern from feedback aggregation."""
        pass
    
    @abstractmethod
    async def get_similar_patterns(
        self,
        pattern_type: str,
        pattern_signature: str,
    ) -> list[dict[str, Any]]:
        """Find similar patterns for a given finding."""
        pass
    
    @abstractmethod
    async def get_pattern_insights(self) -> dict[str, Any]:
        """Get aggregated pattern learning insights."""
        pass

