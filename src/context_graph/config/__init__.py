"""
Configuration module for Context Graph.

Provides feature flags and application configuration.
"""

from context_graph.config.features import (
    FeatureFlags,
    get_features,
    set_features,
    reset_features,
)

__all__ = [
    "FeatureFlags",
    "get_features",
    "set_features",
    "reset_features",
]

