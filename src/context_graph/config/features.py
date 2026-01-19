"""
Feature flags for incremental feature rollout.

All new collaboration features are disabled by default to maintain
backward compatibility. Enable features via environment variables
or programmatically.

Usage:
    # Check if a feature is enabled
    from context_graph.config import get_features
    
    if get_features().enable_finding_validation:
        # New validation logic
        pass

Environment Variables:
    FEATURE_FINDING_VALIDATION=true
    FEATURE_COMMENTS=true
    FEATURE_TEAM_ASSIGNMENT=true
    FEATURE_EXPERT_FEEDBACK=true
    FEATURE_REVIEW_LIFECYCLE=true
    
    # PM-Focused Features (Unified PM Tool)
    FEATURE_PRD_CHANGES=true
    FEATURE_PRD_QUALITY_SCORING=true
    FEATURE_EFFORT_ESTIMATION=true
    FEATURE_EXPERT_ASSIST=true
    FEATURE_PM_PATTERN_LEARNING=true
    FEATURE_PRD_SAVE_TO_FILE=true
    FEATURE_SIDE_BY_SIDE_DIFF=true
    
    # Bulk PRD Analysis Features
    FEATURE_BULK_PRD_ANALYSIS=true
    BULK_PRD_MAX_FILES=20
    BULK_PRD_MAX_PARALLEL_REVIEWS=10
    FEATURE_BULK_PRD_SMART_CODEBASE_DEFAULT=true
    BULK_PRD_CODEBASE_AUTO_DEFAULT_THRESHOLD=3
    
    # PRD Generator
    FEATURE_PRD_GENERATOR=true
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


def _env_bool(key: str, default: bool = False) -> bool:
    """Parse boolean from environment variable."""
    value = os.getenv(key, str(default)).lower()
    return value in ("true", "1", "yes", "on")


@dataclass
class FeatureFlags:
    """
    Feature flags for collaboration features.
    
    All flags default to False for backward compatibility.
    Enable features incrementally via environment variables or programmatically.
    """
    
    # ==================== Phase 1: Core Validation ====================
    
    # Enable finding validation workflow
    # Allows users to validate/reject AI findings
    enable_finding_validation: bool = False
    
    # Enable team assignment for findings
    # Routes findings to appropriate team queues
    enable_team_assignment: bool = False
    
    # Enable comments on findings
    # Allows threaded discussions
    enable_comments: bool = False
    
    # ==================== Phase 2: Expert Feedback ====================
    
    # Enable expert feedback collection
    # Captures corrections and reasoning for learning
    enable_expert_feedback: bool = False
    
    # Enable review lifecycle management
    # Adds approval gates and workflow states
    enable_review_lifecycle: bool = False
    
    # ==================== Phase 3: Advanced ====================
    
    # Enable cross-team review requests
    # Allows teams to request input from other teams
    enable_cross_team_requests: bool = False
    
    # Enable consensus mode for critical findings
    # Requires validation from multiple teams
    enable_consensus_mode: bool = False
    
    # Enable pattern learning from feedback
    # Aggregates feedback for AI improvement
    enable_pattern_learning: bool = False
    
    # ==================== PM-Focused Features (Unified PM Tool) ====================
    
    # Enable PRD change generation (diff-style suggestions)
    # Converts findings into actionable PRD changes
    enable_prd_changes: bool = False
    
    # Enable PRD quality scoring
    # Calculates readiness score and identifies gaps
    enable_prd_quality_scoring: bool = False
    
    # Enable effort estimation
    # Code-grounded time estimates for implementation
    enable_effort_estimation: bool = False
    
    # Enable expert assist (quick ask)
    # Lightweight expert validation, not ticketing
    enable_expert_assist: bool = False
    
    # Enable PM pattern learning
    # Learns from expert responses to improve predictions
    enable_pm_pattern_learning: bool = False
    
    # Enable PRD save-to-file
    # Allows saving PRD changes back to the original file on disk
    enable_prd_save_to_file: bool = False
    
    # Enable side-by-side diff comparison
    # Shows original vs suggested PRD changes in a side-by-side view
    enable_side_by_side_diff: bool = False
    
    # ==================== Bulk PRD Analysis Features ====================
    
    # Enable bulk PRD analysis
    # Allows analyzing up to 20 PRD files in parallel
    enable_bulk_prd_analysis: bool = False
    
    # Maximum number of PRD files for bulk analysis
    bulk_prd_max_files: int = 20
    
    # Maximum parallel review workers for bulk analysis
    bulk_prd_max_parallel_reviews: int = 10
    
    # Enable smart codebase defaulting based on usage frequency
    enable_bulk_prd_smart_codebase_default: bool = True
    
    # Threshold for auto-setting default codebase (selection count)
    bulk_prd_codebase_auto_default_threshold: int = 3
    
    # ==================== PRD Generator Features ====================
    
    # Enable PRD generator
    # Generates PRD documents from codebase analysis
    enable_prd_generator: bool = False
    
    # ==================== Utility Methods ====================
    
    @classmethod
    def from_env(cls) -> "FeatureFlags":
        """
        Create FeatureFlags from environment variables.
        
        Each flag can be enabled by setting its corresponding
        environment variable to "true", "1", "yes", or "on".
        """
        return cls(
            enable_finding_validation=_env_bool("FEATURE_FINDING_VALIDATION"),
            enable_team_assignment=_env_bool("FEATURE_TEAM_ASSIGNMENT"),
            enable_comments=_env_bool("FEATURE_COMMENTS"),
            enable_expert_feedback=_env_bool("FEATURE_EXPERT_FEEDBACK"),
            enable_review_lifecycle=_env_bool("FEATURE_REVIEW_LIFECYCLE"),
            enable_cross_team_requests=_env_bool("FEATURE_CROSS_TEAM_REQUESTS"),
            enable_consensus_mode=_env_bool("FEATURE_CONSENSUS_MODE"),
            enable_pattern_learning=_env_bool("FEATURE_PATTERN_LEARNING"),
            # PM-focused features
            enable_prd_changes=_env_bool("FEATURE_PRD_CHANGES"),
            enable_prd_quality_scoring=_env_bool("FEATURE_PRD_QUALITY_SCORING"),
            enable_effort_estimation=_env_bool("FEATURE_EFFORT_ESTIMATION"),
            enable_expert_assist=_env_bool("FEATURE_EXPERT_ASSIST"),
            enable_pm_pattern_learning=_env_bool("FEATURE_PM_PATTERN_LEARNING"),
            enable_prd_save_to_file=_env_bool("FEATURE_PRD_SAVE_TO_FILE"),
            enable_side_by_side_diff=_env_bool("FEATURE_SIDE_BY_SIDE_DIFF"),
            # Bulk PRD analysis features
            enable_bulk_prd_analysis=_env_bool("FEATURE_BULK_PRD_ANALYSIS"),
            bulk_prd_max_files=int(os.getenv("BULK_PRD_MAX_FILES", "20")),
            bulk_prd_max_parallel_reviews=int(os.getenv("BULK_PRD_MAX_PARALLEL_REVIEWS", "10")),
            enable_bulk_prd_smart_codebase_default=_env_bool("FEATURE_BULK_PRD_SMART_CODEBASE_DEFAULT", True),
            bulk_prd_codebase_auto_default_threshold=int(os.getenv("BULK_PRD_CODEBASE_AUTO_DEFAULT_THRESHOLD", "3")),
            # PRD generator
            enable_prd_generator=_env_bool("FEATURE_PRD_GENERATOR"),
        )
    
    @classmethod
    def all_enabled(cls) -> "FeatureFlags":
        """Create FeatureFlags with all features enabled. Useful for testing."""
        return cls(
            enable_finding_validation=True,
            enable_team_assignment=True,
            enable_comments=True,
            enable_expert_feedback=True,
            enable_review_lifecycle=True,
            enable_cross_team_requests=True,
            enable_consensus_mode=True,
            enable_pattern_learning=True,
            # PM-focused features
            enable_prd_changes=True,
            enable_prd_quality_scoring=True,
            enable_effort_estimation=True,
            enable_expert_assist=True,
            enable_pm_pattern_learning=True,
            enable_prd_save_to_file=True,
            enable_side_by_side_diff=True,
            # Bulk PRD analysis features
            enable_bulk_prd_analysis=True,
            bulk_prd_max_files=20,
            bulk_prd_max_parallel_reviews=10,
            enable_bulk_prd_smart_codebase_default=True,
            bulk_prd_codebase_auto_default_threshold=3,
            # PRD generator
            enable_prd_generator=True,
        )
    
    def to_dict(self) -> dict[str, bool]:
        """Convert to dictionary for API responses."""
        return {
            "validation": self.enable_finding_validation,
            "team_assignment": self.enable_team_assignment,
            "comments": self.enable_comments,
            "expert_feedback": self.enable_expert_feedback,
            "review_lifecycle": self.enable_review_lifecycle,
            "cross_team_requests": self.enable_cross_team_requests,
            "consensus_mode": self.enable_consensus_mode,
            "pattern_learning": self.enable_pattern_learning,
            # PM-focused features
            "prd_changes": self.enable_prd_changes,
            "prd_quality_scoring": self.enable_prd_quality_scoring,
            "effort_estimation": self.enable_effort_estimation,
            "expert_assist": self.enable_expert_assist,
            "pm_pattern_learning": self.enable_pm_pattern_learning,
            "prd_save_to_file": self.enable_prd_save_to_file,
            "side_by_side_diff": self.enable_side_by_side_diff,
            # Bulk PRD analysis features
            "bulk_prd_analysis": self.enable_bulk_prd_analysis,
            "bulk_prd_max_files": self.bulk_prd_max_files,
            "bulk_prd_max_parallel_reviews": self.bulk_prd_max_parallel_reviews,
            "bulk_prd_smart_codebase_default": self.enable_bulk_prd_smart_codebase_default,
            "bulk_prd_codebase_auto_default_threshold": self.bulk_prd_codebase_auto_default_threshold,
            # PRD generator
            "prd_generator": self.enable_prd_generator,
        }
    
    def get_enabled_features(self) -> list[str]:
        """Get list of enabled feature names."""
        enabled = []
        if self.enable_finding_validation:
            enabled.append("finding_validation")
        if self.enable_team_assignment:
            enabled.append("team_assignment")
        if self.enable_comments:
            enabled.append("comments")
        if self.enable_expert_feedback:
            enabled.append("expert_feedback")
        if self.enable_review_lifecycle:
            enabled.append("review_lifecycle")
        if self.enable_cross_team_requests:
            enabled.append("cross_team_requests")
        if self.enable_consensus_mode:
            enabled.append("consensus_mode")
        if self.enable_pattern_learning:
            enabled.append("pattern_learning")
        # PM-focused features
        if self.enable_prd_changes:
            enabled.append("prd_changes")
        if self.enable_prd_quality_scoring:
            enabled.append("prd_quality_scoring")
        if self.enable_effort_estimation:
            enabled.append("effort_estimation")
        if self.enable_expert_assist:
            enabled.append("expert_assist")
        if self.enable_pm_pattern_learning:
            enabled.append("pm_pattern_learning")
        if self.enable_prd_save_to_file:
            enabled.append("prd_save_to_file")
        if self.enable_side_by_side_diff:
            enabled.append("side_by_side_diff")
        # Bulk PRD analysis features
        if self.enable_bulk_prd_analysis:
            enabled.append("bulk_prd_analysis")
        if self.enable_bulk_prd_smart_codebase_default:
            enabled.append("bulk_prd_smart_codebase_default")
        # PRD generator
        if self.enable_prd_generator:
            enabled.append("prd_generator")
        return enabled


# ==================== Global Instance ====================

_features: FeatureFlags | None = None


def get_features() -> FeatureFlags:
    """
    Get the current feature flags instance.
    
    Loads from environment variables on first call.
    Thread-safe for reading (Python GIL).
    """
    global _features
    if _features is None:
        _features = FeatureFlags.from_env()
    return _features


def set_features(features: FeatureFlags) -> None:
    """
    Set the feature flags instance programmatically.
    
    Useful for testing or dynamic configuration.
    """
    global _features
    _features = features


def reset_features() -> None:
    """
    Reset feature flags to reload from environment.
    
    Useful after changing environment variables.
    """
    global _features
    _features = None


# ==================== Decorators for Feature-Gated Functions ====================


def requires_feature(feature_name: str):
    """
    Decorator that raises an error if a feature is not enabled.
    
    Usage:
        @requires_feature("finding_validation")
        async def validate_finding(...):
            ...
    """
    from functools import wraps
    from fastapi import HTTPException
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            features = get_features()
            flag_name = f"enable_{feature_name}"
            
            if not getattr(features, flag_name, False):
                raise HTTPException(
                    status_code=403,
                    detail=f"Feature '{feature_name}' is not enabled. "
                           f"Set FEATURE_{feature_name.upper()}=true to enable."
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

