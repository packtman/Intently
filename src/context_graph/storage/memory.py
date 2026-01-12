"""
In-memory storage implementations.

These wrap the current dict-based storage patterns, maintaining exact
backward compatibility while conforming to the storage interfaces.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from context_graph.storage.base import ReviewStorage, CollaborationStorage
from context_graph.security.review_engine import ReviewResult
from context_graph.core.models import ReviewDimension


class InMemoryReviewStorage(ReviewStorage):
    """
    In-memory review storage - maintains current behavior.
    
    This is the default storage used in development and testing.
    Data is lost on server restart.
    """
    
    def __init__(self) -> None:
        self._reviews: dict[str, ReviewResult] = {}
        self._status: dict[str, dict[str, Any]] = {}
    
    async def save_review(self, review_id: str, result: ReviewResult) -> None:
        """Save a review result."""
        self._reviews[review_id] = result
    
    async def get_review(self, review_id: str) -> ReviewResult | None:
        """Get a review by ID."""
        return self._reviews.get(review_id)
    
    async def delete_review(self, review_id: str) -> bool:
        """Delete a review."""
        if review_id in self._reviews:
            del self._reviews[review_id]
            if review_id in self._status:
                del self._status[review_id]
            return True
        return False
    
    async def list_reviews(self) -> list[dict[str, Any]]:
        """List all reviews with summary info."""
        return [
            {
                "review_id": review_id,
                "title": result.intent.title,
                "status": self._status.get(review_id, {}).get("status", "unknown"),
                "risk_rating": result.risk_rating,
                "findings_count": len(result.all_findings),
                "dimensions": [d.value for d in result.dimensions_analyzed],
                "security_findings": len(result.security_findings),
                "privacy_findings": len(result.privacy_findings),
                "compliance_findings": len(result.compliance_findings),
                "engineering_findings": len(result.engineering_findings),
                "architecture_findings": len(result.architecture_findings),
                "reviewed_at": result.reviewed_at.isoformat(),
            }
            for review_id, result in self._reviews.items()
        ]
    
    async def update_review_status(
        self,
        review_id: str,
        status: str,
        progress: float,
        message: str,
        dimensions: list[str] | None = None,
    ) -> None:
        """Update the status of a running review."""
        self._status[review_id] = {
            "status": status,
            "progress": progress,
            "message": message,
            "dimensions": dimensions or [],
        }
    
    async def get_review_status(self, review_id: str) -> dict[str, Any] | None:
        """Get the current status of a review."""
        return self._status.get(review_id)
    
    # Legacy compatibility methods for gradual migration
    
    def get_reviews_dict(self) -> dict[str, ReviewResult]:
        """Get raw reviews dict for backward compatibility during migration."""
        return self._reviews
    
    def get_status_dict(self) -> dict[str, dict[str, Any]]:
        """Get raw status dict for backward compatibility during migration."""
        return self._status


class InMemoryCollaborationStorage(CollaborationStorage):
    """
    In-memory collaboration data storage.
    
    Stores validations, comments, assignments, and feedback separately
    from review data to keep concerns isolated.
    """
    
    def __init__(self) -> None:
        # Phase 1-4: Core collaboration data
        # finding_id -> validation data
        self._validations: dict[str, dict[str, Any]] = {}
        # finding_id -> list of comments
        self._comments: dict[str, list[dict[str, Any]]] = {}
        # finding_id -> assignment data
        self._assignments: dict[str, dict[str, Any]] = {}
        # finding_id -> list of feedback
        self._feedback: dict[str, list[dict[str, Any]]] = {}
        
        # Phase 5: Advanced features
        # review_id -> lifecycle state
        self._lifecycle: dict[str, dict[str, Any]] = {}
        # review_id -> lifecycle history
        self._lifecycle_history: dict[str, list[dict[str, Any]]] = {}
        # cross-team review requests
        self._review_requests: dict[str, dict[str, Any]] = {}
        # consensus votes (review_id:finding_id -> votes by team)
        self._consensus_votes: dict[str, dict[str, dict[str, Any]]] = {}
        # learned patterns
        self._patterns: list[dict[str, Any]] = []
    
    # ==================== Finding Validation ====================
    
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
        validation = {
            "id": str(uuid4()),
            "review_id": review_id,
            "finding_id": finding_id,
            "status": status,
            "validator_id": validator_id,
            "validator_team": validator_team,
            "notes": notes,
            "validated_at": datetime.now().isoformat(),
        }
        
        # Store with composite key
        key = f"{review_id}:{finding_id}"
        self._validations[key] = validation
        
        return validation
    
    async def get_finding_validation(
        self,
        review_id: str,
        finding_id: str,
    ) -> dict[str, Any] | None:
        """Get the current validation status for a finding."""
        key = f"{review_id}:{finding_id}"
        return self._validations.get(key)
    
    async def get_validations_for_review(
        self,
        review_id: str,
    ) -> dict[str, dict[str, Any]]:
        """Get all validations for a review, keyed by finding_id."""
        result = {}
        prefix = f"{review_id}:"
        for key, validation in self._validations.items():
            if key.startswith(prefix):
                finding_id = key[len(prefix):]
                result[finding_id] = validation
        return result
    
    # ==================== Comments ====================
    
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
        comment = {
            "id": str(uuid4()),
            "review_id": review_id,
            "finding_id": finding_id,
            "author_id": author_id,
            "author_name": author_name,
            "author_team": author_team,
            "content": content,
            "parent_comment_id": parent_comment_id,
            "created_at": datetime.now().isoformat(),
            "is_deleted": False,
        }
        
        key = f"{review_id}:{finding_id}"
        if key not in self._comments:
            self._comments[key] = []
        self._comments[key].append(comment)
        
        return comment
    
    async def get_comments(
        self,
        review_id: str,
        finding_id: str,
    ) -> list[dict[str, Any]]:
        """Get all comments for a finding."""
        key = f"{review_id}:{finding_id}"
        comments = self._comments.get(key, [])
        return [c for c in comments if not c.get("is_deleted", False)]
    
    async def get_comment_counts(
        self,
        review_id: str,
    ) -> dict[str, int]:
        """Get comment counts for all findings in a review."""
        result = {}
        prefix = f"{review_id}:"
        for key, comments in self._comments.items():
            if key.startswith(prefix):
                finding_id = key[len(prefix):]
                active_comments = [c for c in comments if not c.get("is_deleted", False)]
                result[finding_id] = len(active_comments)
        return result
    
    async def delete_comment(
        self,
        comment_id: str,
    ) -> bool:
        """Soft-delete a comment."""
        for comments in self._comments.values():
            for comment in comments:
                if comment["id"] == comment_id:
                    comment["is_deleted"] = True
                    comment["deleted_at"] = datetime.now().isoformat()
                    return True
        return False
    
    # ==================== Team Assignment ====================
    
    async def assign_finding(
        self,
        review_id: str,
        finding_id: str,
        team: str,
        user_id: str | None = None,
        assigned_by: str | None = None,
    ) -> dict[str, Any]:
        """Assign a finding to a team/user."""
        assignment = {
            "id": str(uuid4()),
            "review_id": review_id,
            "finding_id": finding_id,
            "team": team,
            "user_id": user_id,
            "assigned_by": assigned_by,
            "assigned_at": datetime.now().isoformat(),
        }
        
        key = f"{review_id}:{finding_id}"
        self._assignments[key] = assignment
        
        return assignment
    
    async def get_assignments_for_review(
        self,
        review_id: str,
    ) -> dict[str, dict[str, Any]]:
        """Get all assignments for a review."""
        result = {}
        prefix = f"{review_id}:"
        for key, assignment in self._assignments.items():
            if key.startswith(prefix):
                finding_id = key[len(prefix):]
                result[finding_id] = assignment
        return result
    
    async def get_team_queue(
        self,
        team: str,
    ) -> list[dict[str, Any]]:
        """Get all findings assigned to a team."""
        return [
            assignment
            for assignment in self._assignments.values()
            if assignment.get("team") == team
        ]
    
    # ==================== Expert Feedback ====================
    
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
        feedback = {
            "id": str(uuid4()),
            "review_id": review_id,
            "finding_id": finding_id,
            "feedback_type": feedback_type,
            "original_value": original_value,
            "expert_value": expert_value,
            "expert_id": expert_id,
            "expert_team": expert_team,
            "reasoning": reasoning,
            "created_at": datetime.now().isoformat(),
        }
        
        key = f"{review_id}:{finding_id}"
        if key not in self._feedback:
            self._feedback[key] = []
        self._feedback[key].append(feedback)
        
        return feedback
    
    async def get_feedback_for_finding(
        self,
        review_id: str,
        finding_id: str,
    ) -> list[dict[str, Any]]:
        """Get all expert feedback for a finding."""
        key = f"{review_id}:{finding_id}"
        return self._feedback.get(key, [])
    
    async def get_feedback_stats(self) -> dict[str, Any]:
        """Get aggregated feedback statistics."""
        total_feedback = sum(len(fb_list) for fb_list in self._feedback.values())
        
        # Count by type
        by_type: dict[str, int] = {}
        # Count by team
        by_team: dict[str, int] = {}
        # Track rejection patterns
        rejection_reasons: dict[str, int] = {}
        
        for fb_list in self._feedback.values():
            for fb in fb_list:
                fb_type = fb.get("feedback_type", "unknown")
                by_type[fb_type] = by_type.get(fb_type, 0) + 1
                
                team = fb.get("expert_team", "unknown")
                by_team[team] = by_team.get(team, 0) + 1
                
                if fb_type == "accuracy" and fb.get("expert_value") == "rejected":
                    reason = fb.get("reasoning", "unspecified")[:50]
                    rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
        
        return {
            "total_feedback": total_feedback,
            "by_type": by_type,
            "by_team": by_team,
            "common_rejection_reasons": dict(
                sorted(rejection_reasons.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
        }
    
    # ==================== Review Lifecycle (Phase 5) ====================
    
    async def update_review_lifecycle(
        self,
        review_id: str,
        state: str,
        updated_by: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Update the lifecycle state of a review."""
        now = datetime.now().isoformat()
        
        lifecycle = {
            "review_id": review_id,
            "state": state,
            "updated_by": updated_by,
            "updated_at": now,
            "notes": notes,
        }
        
        self._lifecycle[review_id] = lifecycle
        
        # Add to history
        if review_id not in self._lifecycle_history:
            self._lifecycle_history[review_id] = []
        
        self._lifecycle_history[review_id].append({
            "id": str(uuid4()),
            "state": state,
            "updated_by": updated_by,
            "updated_at": now,
            "notes": notes,
        })
        
        return lifecycle
    
    async def get_review_lifecycle(
        self,
        review_id: str,
    ) -> dict[str, Any] | None:
        """Get the current lifecycle state of a review."""
        return self._lifecycle.get(review_id)
    
    async def get_lifecycle_history(
        self,
        review_id: str,
    ) -> list[dict[str, Any]]:
        """Get lifecycle state history for a review."""
        return self._lifecycle_history.get(review_id, [])
    
    # ==================== Cross-Team Requests (Phase 5) ====================
    
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
        request_id = str(uuid4())
        
        request = {
            "id": request_id,
            "review_id": review_id,
            "finding_id": finding_id,
            "requesting_team": requesting_team,
            "target_team": target_team,
            "question": question,
            "requested_by": requested_by,
            "deadline": deadline,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "response": None,
            "responded_by": None,
            "responded_at": None,
        }
        
        self._review_requests[request_id] = request
        return request
    
    async def get_review_requests(
        self,
        review_id: str | None = None,
        target_team: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get review requests filtered by review or target team."""
        requests = list(self._review_requests.values())
        
        if review_id:
            requests = [r for r in requests if r.get("review_id") == review_id]
        
        if target_team:
            requests = [r for r in requests if r.get("target_team") == target_team]
        
        return sorted(requests, key=lambda r: r.get("created_at", ""), reverse=True)
    
    async def respond_to_request(
        self,
        request_id: str,
        response: str,
        responded_by: str,
    ) -> dict[str, Any]:
        """Respond to a cross-team review request."""
        if request_id not in self._review_requests:
            raise ValueError(f"Request {request_id} not found")
        
        request = self._review_requests[request_id]
        request["status"] = "responded"
        request["response"] = response
        request["responded_by"] = responded_by
        request["responded_at"] = datetime.now().isoformat()
        
        return request
    
    # ==================== Consensus Mode (Phase 5) ====================
    
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
        key = f"{review_id}:{finding_id}"
        
        if key not in self._consensus_votes:
            self._consensus_votes[key] = {}
        
        vote_data = {
            "id": str(uuid4()),
            "review_id": review_id,
            "finding_id": finding_id,
            "team": team,
            "vote": vote,  # 'approve', 'reject', 'abstain'
            "voter_id": voter_id,
            "notes": notes,
            "voted_at": datetime.now().isoformat(),
        }
        
        self._consensus_votes[key][team] = vote_data
        return vote_data
    
    async def get_consensus_status(
        self,
        review_id: str,
        finding_id: str,
    ) -> dict[str, Any]:
        """Get consensus voting status for a finding."""
        key = f"{review_id}:{finding_id}"
        votes = self._consensus_votes.get(key, {})
        
        # Count votes
        vote_counts = {"approve": 0, "reject": 0, "abstain": 0}
        for vote_data in votes.values():
            vote_type = vote_data.get("vote", "abstain")
            if vote_type in vote_counts:
                vote_counts[vote_type] += 1
        
        total_votes = len(votes)
        
        return {
            "review_id": review_id,
            "finding_id": finding_id,
            "votes": votes,
            "vote_counts": vote_counts,
            "total_votes": total_votes,
            "has_consensus": (
                vote_counts["approve"] > vote_counts["reject"] and total_votes >= 2
            ),
        }
    
    # ==================== Pattern Learning (Phase 5) ====================
    
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
        pattern = {
            "id": str(uuid4()),
            "pattern_type": pattern_type,
            "pattern_signature": pattern_signature,
            "decision": decision,
            "conditions": conditions,
            "reasoning": reasoning,
            "source_feedback_ids": source_feedback_ids,
            "times_applied": 0,
            "created_at": datetime.now().isoformat(),
        }
        
        self._patterns.append(pattern)
        return pattern
    
    async def get_similar_patterns(
        self,
        pattern_type: str,
        pattern_signature: str,
    ) -> list[dict[str, Any]]:
        """Find similar patterns for a given finding."""
        # Simple substring matching - in production, use embeddings or fuzzy matching
        similar = []
        signature_lower = pattern_signature.lower()
        
        for pattern in self._patterns:
            if pattern["pattern_type"] == pattern_type:
                pattern_sig_lower = pattern["pattern_signature"].lower()
                # Check for keyword overlap
                sig_words = set(signature_lower.split())
                pattern_words = set(pattern_sig_lower.split())
                overlap = len(sig_words & pattern_words)
                
                if overlap >= 2 or signature_lower in pattern_sig_lower or pattern_sig_lower in signature_lower:
                    similar.append({
                        **pattern,
                        "similarity_score": overlap / max(len(sig_words), 1),
                    })
        
        return sorted(similar, key=lambda p: p.get("similarity_score", 0), reverse=True)[:5]
    
    async def get_pattern_insights(self) -> dict[str, Any]:
        """Get aggregated pattern learning insights."""
        total_patterns = len(self._patterns)
        
        # Group by pattern type
        by_type: dict[str, int] = {}
        # Group by decision
        by_decision: dict[str, int] = {}
        # Most applied patterns
        most_applied = sorted(
            self._patterns, 
            key=lambda p: p.get("times_applied", 0), 
            reverse=True
        )[:10]
        
        for pattern in self._patterns:
            pt = pattern.get("pattern_type", "unknown")
            by_type[pt] = by_type.get(pt, 0) + 1
            
            decision = pattern.get("decision", "unknown")
            by_decision[decision] = by_decision.get(decision, 0) + 1
        
        return {
            "total_patterns": total_patterns,
            "by_type": by_type,
            "by_decision": by_decision,
            "most_applied_patterns": [
                {
                    "pattern_signature": p["pattern_signature"],
                    "decision": p["decision"],
                    "times_applied": p["times_applied"],
                }
                for p in most_applied
            ],
        }

