"""
PM-Focused Features Module.

This module implements the unified PM tool features:
- PRD change generation (diff-style suggestions)
- PRD quality scoring
- Effort estimation
- Expert assist
- Pattern learning
- Side-by-side diff generation
"""

from context_graph.pm.prd_change_generator import PRDChangeGenerator
from context_graph.pm.quality_scorer import PRDQualityScorer
from context_graph.pm.effort_estimator import EffortEstimator
from context_graph.pm.pattern_learner import PatternLearner
from context_graph.pm.diff_generator import SideBySideDiffGenerator, generate_side_by_side_diff

__all__ = [
    "PRDChangeGenerator",
    "PRDQualityScorer",
    "EffortEstimator",
    "PatternLearner",
    "SideBySideDiffGenerator",
    "generate_side_by_side_diff",
]
