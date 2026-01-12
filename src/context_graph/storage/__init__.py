"""
Storage abstractions for Context Graph.

Provides pluggable storage backends for reviews, comments, and collaboration data.
"""

from context_graph.storage.base import (
    ReviewStorage,
    CollaborationStorage,
)
from context_graph.storage.memory import (
    InMemoryReviewStorage,
    InMemoryCollaborationStorage,
)

__all__ = [
    "ReviewStorage",
    "CollaborationStorage",
    "InMemoryReviewStorage",
    "InMemoryCollaborationStorage",
]

