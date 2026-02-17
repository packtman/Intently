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
    
    # Iterative Analysis Features (Multi-round LLM analysis)
    FEATURE_ITERATIVE_SECURITY_ANALYSIS=true
    FEATURE_ITERATIVE_PRIVACY_ANALYSIS=true
    FEATURE_ITERATIVE_COMPLIANCE_ANALYSIS=true
    FEATURE_ITERATIVE_ENGINEERING_ANALYSIS=true
    FEATURE_ITERATIVE_ARCHITECTURE_ANALYSIS=true
    FEATURE_ITERATIVE_THREAT_MODEL=true
    ITERATIVE_ANALYSIS_MAX_ROUNDS=5
    
    # False Positive Filtering
    FEATURE_FALSE_POSITIVE_FILTERING=true
    FALSE_POSITIVE_MAX_ITERATIONS=3
    FALSE_POSITIVE_MIN_FINDINGS=3
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
    
    # ==================== Iterative Analysis Features ====================
    # Multi-round LLM analysis for comprehensive coverage
    
    # Enable iterative security analysis
    # Runs multiple rounds to cover all security categories (STRIDE, OWASP)
    enable_iterative_security_analysis: bool = False
    
    # Enable iterative privacy analysis
    # Runs multiple rounds to cover all LINDDUN categories
    enable_iterative_privacy_analysis: bool = False
    
    # Enable iterative compliance analysis
    # Runs multiple rounds to cover all compliance frameworks
    enable_iterative_compliance_analysis: bool = False
    
    # Enable iterative engineering analysis
    # Runs multiple rounds to cover all engineering concern categories
    enable_iterative_engineering_analysis: bool = False
    
    # Enable iterative architecture analysis
    # Runs multiple rounds to cover all architecture concern categories
    enable_iterative_architecture_analysis: bool = False
    
    # Enable iterative threat modeling
    # Runs multiple rounds to cover all threat categories
    enable_iterative_threat_model: bool = False
    
    # Maximum rounds for iterative analysis (default: 5)
    iterative_analysis_max_rounds: int = 5
    
    # ==================== False Positive Filtering ====================
    # Multi-iteration LLM-based false positive removal
    
    # Enable false positive filtering on scan findings
    # Runs multiple validation passes to remove false positives
    enable_false_positive_filtering: bool = True
    
    # Maximum iterations for false positive filtering (1-5)
    # Each iteration applies a different validation strategy:
    #   1 = context validation (check existing mitigations)
    #   2 = specificity check (remove generic boilerplate)
    #   3 = evidence grounding (ensure concrete evidence)
    false_positive_max_iterations: int = 3
    
    # Minimum number of findings before filtering is applied
    # (skip filtering for very small result sets — not worth the cost)
    false_positive_min_findings: int = 3
    
    # Run FP filter strategies in parallel (fan-out + majority vote)
    # instead of sequentially (pipeline).  ~3x faster wall-clock time.
    false_positive_parallel: bool = True
    
    # In parallel mode, the minimum number of strategies that must vote
    # "remove" to actually remove a finding.
    # 1 = any strategy can remove (default — matches sequential behaviour)
    # 2 = majority must agree (recommended when using fast/cheap models)
    # 3 = unanimous (very conservative)
    false_positive_removal_threshold: int = 1
    
    # Use a faster/cheaper model for FP filtering (classification task).
    # Empty string = auto-detect the best fast model for the provider:
    #   OpenAI    → gpt-4.1-mini  (nano is too weak for FP evaluation)
    #   Anthropic → claude-haiku-4-5-20251001
    # Set explicitly to override (e.g. "gpt-4.1-nano" if cost is priority).
    # Set to "disabled" to use the same model as the main analysis.
    false_positive_model: str = "disabled"
    
    # ==================== P0: Core PM Experience ====================

    # Enable product-aware chat (conversational AI grounded in reviews)
    enable_product_chat: bool = False

    # Enable formal review requests (PR-like review workflow)
    enable_review_requests: bool = False

    # Enable impact graph visualization (D3.js entity graph)
    enable_impact_graph: bool = False

    # ==================== Scan Tracing ====================
    # Real-time trace log streaming for scan observability
    
    # Enable scan tracing (SSE trace log viewer in the frontend)
    # When enabled, scans emit granular trace events that are streamed
    # to the frontend via Server-Sent Events.
    enable_scan_tracing: bool = True
    
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
            # Iterative analysis features
            enable_iterative_security_analysis=_env_bool("FEATURE_ITERATIVE_SECURITY_ANALYSIS"),
            enable_iterative_privacy_analysis=_env_bool("FEATURE_ITERATIVE_PRIVACY_ANALYSIS"),
            enable_iterative_compliance_analysis=_env_bool("FEATURE_ITERATIVE_COMPLIANCE_ANALYSIS"),
            enable_iterative_engineering_analysis=_env_bool("FEATURE_ITERATIVE_ENGINEERING_ANALYSIS"),
            enable_iterative_architecture_analysis=_env_bool("FEATURE_ITERATIVE_ARCHITECTURE_ANALYSIS"),
            enable_iterative_threat_model=_env_bool("FEATURE_ITERATIVE_THREAT_MODEL"),
            iterative_analysis_max_rounds=int(os.getenv("ITERATIVE_ANALYSIS_MAX_ROUNDS", "5")),
            # False positive filtering
            enable_false_positive_filtering=_env_bool("FEATURE_FALSE_POSITIVE_FILTERING", True),
            false_positive_max_iterations=int(os.getenv("FALSE_POSITIVE_MAX_ITERATIONS", "3")),
            false_positive_min_findings=int(os.getenv("FALSE_POSITIVE_MIN_FINDINGS", "3")),
            false_positive_parallel=_env_bool("FALSE_POSITIVE_PARALLEL", True),
            false_positive_removal_threshold=int(os.getenv("FALSE_POSITIVE_REMOVAL_THRESHOLD", "1")),
            false_positive_model=os.getenv("FALSE_POSITIVE_MODEL", "disabled"),
            # P0: Core PM Experience
            enable_product_chat=_env_bool("FEATURE_PRODUCT_CHAT"),
            enable_review_requests=_env_bool("FEATURE_REVIEW_REQUESTS"),
            enable_impact_graph=_env_bool("FEATURE_IMPACT_GRAPH"),
            # Scan tracing
            enable_scan_tracing=_env_bool("FEATURE_SCAN_TRACING", True),
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
            # Iterative analysis features
            enable_iterative_security_analysis=True,
            enable_iterative_privacy_analysis=True,
            enable_iterative_compliance_analysis=True,
            enable_iterative_engineering_analysis=True,
            enable_iterative_architecture_analysis=True,
            enable_iterative_threat_model=True,
            iterative_analysis_max_rounds=5,
            # False positive filtering
            enable_false_positive_filtering=True,
            false_positive_max_iterations=3,
            false_positive_min_findings=3,
            false_positive_parallel=True,
            false_positive_removal_threshold=1,
            false_positive_model="disabled",
            # P0: Core PM Experience
            enable_product_chat=True,
            enable_review_requests=True,
            enable_impact_graph=True,
            # Scan tracing
            enable_scan_tracing=True,
        )
    
    def to_dict(self) -> dict[str, Any]:
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
            # Iterative analysis features
            "iterative_security_analysis": self.enable_iterative_security_analysis,
            "iterative_privacy_analysis": self.enable_iterative_privacy_analysis,
            "iterative_compliance_analysis": self.enable_iterative_compliance_analysis,
            "iterative_engineering_analysis": self.enable_iterative_engineering_analysis,
            "iterative_architecture_analysis": self.enable_iterative_architecture_analysis,
            "iterative_threat_model": self.enable_iterative_threat_model,
            "iterative_analysis_max_rounds": self.iterative_analysis_max_rounds,
            # False positive filtering
            "false_positive_filtering": self.enable_false_positive_filtering,
            "false_positive_max_iterations": self.false_positive_max_iterations,
            "false_positive_min_findings": self.false_positive_min_findings,
            "false_positive_parallel": self.false_positive_parallel,
            "false_positive_removal_threshold": self.false_positive_removal_threshold,
            "false_positive_model": self.false_positive_model,
            # P0: Core PM Experience
            "product_chat": self.enable_product_chat,
            "review_requests": self.enable_review_requests,
            "impact_graph": self.enable_impact_graph,
            # Scan tracing
            "scan_tracing": self.enable_scan_tracing,
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
        # Iterative analysis features
        if self.enable_iterative_security_analysis:
            enabled.append("iterative_security_analysis")
        if self.enable_iterative_privacy_analysis:
            enabled.append("iterative_privacy_analysis")
        if self.enable_iterative_compliance_analysis:
            enabled.append("iterative_compliance_analysis")
        if self.enable_iterative_engineering_analysis:
            enabled.append("iterative_engineering_analysis")
        if self.enable_iterative_architecture_analysis:
            enabled.append("iterative_architecture_analysis")
        if self.enable_iterative_threat_model:
            enabled.append("iterative_threat_model")
        # False positive filtering
        if self.enable_false_positive_filtering:
            enabled.append("false_positive_filtering")
        if self.false_positive_parallel:
            enabled.append("false_positive_parallel")
        # P0: Core PM Experience
        if self.enable_product_chat:
            enabled.append("product_chat")
        if self.enable_review_requests:
            enabled.append("review_requests")
        if self.enable_impact_graph:
            enabled.append("impact_graph")
        # Scan tracing
        if self.enable_scan_tracing:
            enabled.append("scan_tracing")
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

